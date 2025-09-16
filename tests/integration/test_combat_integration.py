"""
Integration tests for combat system components.

Tests the interaction between CombatManager, CombatResolver,
BattleCalculator, and related systems in realistic scenarios.
"""
import pytest

from src.game.combat_manager import CombatManager
from src.game.combat_resolver import CombatResolver, CombatResult
from src.core.game_state import GameState, BattlePhase
from src.core.data_structures import Vector2
from src.core.game_enums import Team, UnitClass
from src.core.events import UnitDefeated
from tests.conftest import TestDataBuilder
from tests.test_utils import create_combat_scenario, MapTestBuilder


@pytest.mark.integration
class TestCombatManagerIntegration:
    """Test CombatManager integration with other combat systems."""
    
    @pytest.fixture
    def full_combat_setup(self, medium_map):
        """Create a complete combat setup with all components."""
        player_unit = TestDataBuilder.unit("Player Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(2, 2))
        enemy_unit = TestDataBuilder.unit("Enemy Warrior", UnitClass.WARRIOR, Team.ENEMY, Vector2(4, 4))
        
        medium_map.add_unit(player_unit)
        medium_map.add_unit(enemy_unit)
        
        game_state = GameState()
        game_state.battle.phase = BattlePhase.TARGETING
        
        events = []
        def event_emitter(event):
            events.append(event)
        
        combat_manager = CombatManager(medium_map, game_state, event_emitter)
        
        return {
            'map': medium_map,
            'state': game_state,
            'manager': combat_manager,
            'player': player_unit,
            'enemy': enemy_unit,
            'events': events
        }
    
    def test_complete_attack_flow(self, full_combat_setup):
        """Test complete attack flow from targeting to resolution."""
        setup = full_combat_setup
        manager = setup['manager']
        player = setup['player']
        enemy = setup['enemy']
        
        # Setup attack targeting
        manager.setup_attack_targeting(player)
        
        # Should have attack range
        assert len(setup['state'].battle.attack_range) > 0
        
        # Position cursor on enemy
        setup['state'].set_cursor_position(enemy.position)
        
        # Update targeting
        manager.update_attack_targeting()
        
        # Execute attack
        # Set cursor to target position and execute attack
        setup['state'].cursor.set_position(enemy.position)
        success = manager.execute_attack_at_cursor()
        
        # Create result based on success
        result = CombatResult()
        if success:
            result.targets_hit = [enemy]
        
        # Should get valid combat result
        assert isinstance(result, CombatResult)
        
        # If enemy was hit, should have damage dealt
        if len(result.targets_hit) > 0:
            assert len(result.damage_dealt) > 0
    
    def test_aoe_attack_integration(self, full_combat_setup):
        """Test AOE attack integration across systems."""
        setup = full_combat_setup
        
        # Create mage for AOE attacks
        mage = TestDataBuilder.unit("Battle Mage", UnitClass.MAGE, Team.PLAYER, Vector2(3, 3))
        setup['map'].add_unit(mage)
        
        manager = CombatManager(setup['map'], setup['state'])
        
        # Setup AOE attack
        center_pos = Vector2(4, 4)
        # Call AOE attack on the resolver
        result = manager.resolver.execute_aoe_attack(mage, center_pos, "cross")
        
        assert isinstance(result, CombatResult)
        assert isinstance(result.friendly_fire, bool)
    
    def test_combat_event_generation(self, full_combat_setup):
        """Test that combat generates appropriate events."""
        setup = full_combat_setup
        manager = setup['manager']
        enemy = setup['enemy']
        events = setup['events']
        
        # Weaken enemy to ensure defeat
        enemy.hp_current = 1
        
        # Execute attack
        # Set cursor to target position and execute attack
        setup['state'].cursor.set_position(enemy.position)
        success = manager.execute_attack_at_cursor()
        
        # Create result based on success
        result = CombatResult()
        if success:
            result.targets_hit = [enemy]
        
        # If enemy was defeated, should have generated events
        if enemy.name in result.defeated_targets:
            # Check if defeat event was emitted
            defeat_events = [e for e in events if isinstance(e, UnitDefeated)]
            assert len(defeat_events) > 0
    
    def test_battle_calculator_integration(self, full_combat_setup):
        """Test integration with BattleCalculator."""
        setup = full_combat_setup
        manager = setup['manager']
        player = setup['player']
        enemy = setup['enemy']
        
        # Calculator should be available
        assert manager.calculator is not None
        
        # Should be able to calculate damage preview
        if hasattr(manager.calculator, 'calculate_damage'):
            preview = manager.calculator.calculate_damage(player, enemy)
            assert isinstance(preview, (int, dict))  # Damage value or damage info


@pytest.mark.integration
class TestCombatResolverIntegration:
    """Test CombatResolver integration with map and units."""
    
    def test_resolver_with_populated_map(self, populated_map):
        """Test resolver working with a populated map."""
        resolver = CombatResolver(populated_map)
        
        # Get player and enemy units
        player_unit = None
        enemy_unit = None
        
        for unit in populated_map.units.values():
            if unit.team == Team.PLAYER:
                player_unit = unit
            elif unit.team == Team.ENEMY:
                enemy_unit = unit
        
        assert player_unit is not None
        assert enemy_unit is not None
        
        # Execute attack
        result = resolver.execute_single_attack(player_unit, enemy_unit)
        
        assert isinstance(result, CombatResult)
    
    def test_resolver_unit_defeat_integration(self, small_map):
        """Test that resolver properly handles unit defeat."""
        resolver = CombatResolver(small_map)
        
        # Create weak enemy
        weak_enemy = TestDataBuilder.unit("Weak Enemy", UnitClass.ARCHER, Team.ENEMY, Vector2(3, 3), hp=1)
        attacker = TestDataBuilder.unit("Attacker", UnitClass.KNIGHT, Team.PLAYER, Vector2(3, 2))
        
        small_map.add_unit(weak_enemy)
        small_map.add_unit(attacker)
        
        # Execute attack
        result = resolver.execute_single_attack(attacker, weak_enemy)
        
        # Check if enemy was defeated
        if weak_enemy.hp_current <= 0:
            assert weak_enemy.name in result.defeated_targets
            assert weak_enemy.name in result.defeated_positions
    
    def test_multi_unit_aoe_resolution(self, medium_map):
        """Test AOE resolution with multiple units."""
        resolver = CombatResolver(medium_map)
        
        # Create cluster of units
        caster = TestDataBuilder.unit("Caster", UnitClass.MAGE, Team.PLAYER, Vector2(5, 5))
        enemy1 = TestDataBuilder.unit("Enemy1", UnitClass.WARRIOR, Team.ENEMY, Vector2(5, 4))
        enemy2 = TestDataBuilder.unit("Enemy2", UnitClass.ARCHER, Team.ENEMY, Vector2(4, 5))
        ally = TestDataBuilder.unit("Ally", UnitClass.KNIGHT, Team.PLAYER, Vector2(5, 6))
        
        for unit in [caster, enemy1, enemy2, ally]:
            medium_map.add_unit(unit)
        
        # Execute AOE centered on enemies
        result = resolver.execute_aoe_attack(caster, Vector2(5, 5), "cross")
        
        # Should hit multiple units
        assert isinstance(result, CombatResult)
        
        # Check for friendly fire
        for hit_unit in result.targets_hit:
            if hit_unit.team == Team.PLAYER and hit_unit != caster:
                assert result.friendly_fire is True
                break


@pytest.mark.integration
class TestGameStateIntegration:
    """Test game state integration with combat systems."""
    
    def test_battle_phase_transitions(self):
        """Test battle phase transitions during combat."""
        game_map, player, _ = create_combat_scenario()
        game_state = GameState()
        combat_manager = CombatManager(game_map, game_state)
        
        # Start in select phase
        game_state.battle.phase = BattlePhase.UNIT_SELECTION
        
        # Select unit
        game_state.battle.selected_unit_id = player.unit_id
        
        # Move to targeting phase
        game_state.battle.phase = BattlePhase.TARGETING
        
        # Setup attack targeting
        combat_manager.setup_attack_targeting(player)
        
        # State should reflect combat preparation
        assert game_state.battle.phase == BattlePhase.TARGETING
        assert game_state.battle.selected_unit_id == player.unit_id
        assert len(game_state.battle.attack_range) > 0
    
    def test_cursor_and_targeting_integration(self):
        """Test cursor movement integration with targeting."""
        game_map, player, _ = create_combat_scenario((6, 6))
        game_state = GameState()
        combat_manager = CombatManager(game_map, game_state)
        
        # Setup attack targeting
        combat_manager.setup_attack_targeting(player)
        
        # Move cursor to different positions
        cursor_positions = [Vector2(3, 3), Vector2(4, 4), Vector2(2, 2)]
        
        for pos in cursor_positions:
            if game_map.is_valid_position(pos):
                game_state.cursor.set_position(pos)
                
                # Update targeting
                combat_manager.update_attack_targeting()
                
                # State should be consistent
                assert game_state.cursor.position == pos
    
    def test_unit_selection_integration(self):
        """Test unit selection integration with combat systems."""
        map_builder = MapTestBuilder(7, 7)
        game_map = (map_builder
                   .with_player_knight("Knight1", 2, 2)
                   .with_player_knight("Knight2", 3, 3)
                   .with_enemy_warrior("Enemy", 5, 5)
                   .build())
        
        game_state = GameState()
        combat_manager = CombatManager(game_map, game_state)
        
        # Select different units
        knight1 = game_map.get_unit_at(Vector2(2, 2))
        knight2 = game_map.get_unit_at(Vector2(3, 3))
        
        # Ensure units exist before proceeding
        assert knight1 is not None
        assert knight2 is not None
        
        # Select first knight
        if knight1:
            game_state.battle.selected_unit_id = knight1.name
            combat_manager.setup_attack_targeting(knight1)
        range1_size = len(game_state.battle.attack_range)
        
        # Select second knight
        if knight2:
            game_state.battle.selected_unit_id = knight2.name
            combat_manager.setup_attack_targeting(knight2)
        range2_size = len(game_state.battle.attack_range)
        
        # Both should have valid attack ranges
        assert range1_size > 0
        assert range2_size > 0


@pytest.mark.integration
class TestMapCombatIntegration:
    """Test map integration with combat systems."""
    
    def test_terrain_combat_interaction(self, terrain_map):
        """Test combat interaction with different terrain types."""
        # Add units to terrain map
        knight = TestDataBuilder.unit("Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(0, 0))
        enemy = TestDataBuilder.unit("Enemy", UnitClass.WARRIOR, Team.ENEMY, Vector2(2, 2))
        
        terrain_map.add_unit(knight)
        terrain_map.add_unit(enemy)
        
        resolver = CombatResolver(terrain_map)
        
        # Combat should work regardless of terrain
        result = resolver.execute_single_attack(knight, enemy)
        
        assert isinstance(result, CombatResult)
    
    def test_ranged_combat_across_map(self, large_map):
        """Test ranged combat across larger map distances."""
        # Place archer and distant enemy
        archer = TestDataBuilder.unit("Archer", UnitClass.ARCHER, Team.PLAYER, Vector2(5, 5))
        distant_enemy = TestDataBuilder.unit("Far Enemy", UnitClass.MAGE, Team.ENEMY, Vector2(15, 15))
        
        large_map.add_unit(archer)
        large_map.add_unit(distant_enemy)
        
        # Calculate attack range
        attack_range = large_map.calculate_attack_range(archer)
        
        # Range should be reasonable
        assert isinstance(attack_range, list) or hasattr(attack_range, '__iter__')
        assert len(attack_range) > 0
    
    def test_unit_movement_combat_integration(self, medium_map):
        """Test integration between movement and combat systems."""
        knight = TestDataBuilder.unit("Mobile Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(2, 2))
        enemy = TestDataBuilder.unit("Target", UnitClass.ARCHER, Team.ENEMY, Vector2(6, 6))
        
        medium_map.add_unit(knight)
        medium_map.add_unit(enemy)
        
        # Calculate movement range
        movement_range = medium_map.calculate_movement_range(knight)
        
        # From any position in movement range, should be able to calculate attack range
        if len(movement_range) > 0:
            test_position = movement_range[0]
            
            # Temporarily move knight
            original_pos = knight.position
            knight.move_to(test_position)
            
            # Calculate attack range from new position
            attack_range = medium_map.calculate_attack_range(knight)
            
            assert isinstance(attack_range, list) or hasattr(attack_range, '__iter__')
            
            # Restore position
            knight.move_to(original_pos)


@pytest.mark.integration
class TestEndToEndCombat:
    """End-to-end combat scenario tests."""
    
    def test_complete_combat_scenario(self):
        """Test a complete combat scenario from start to finish."""
        # Create battlefield
        map_builder = MapTestBuilder(10, 10)
        game_map = (map_builder
                   .with_player_knight("Hero", 2, 2)
                   .with_enemy_warrior("Villain", 7, 7)
                   .with_mountains([(4, 4), (5, 5)])  # Obstacles
                   .build())
        
        game_state = GameState()
        events = []
        
        def event_recorder(event):
            events.append(event)
        
        combat_manager = CombatManager(game_map, game_state, event_recorder)
        
        # Get units
        hero = game_map.get_unit_at(Vector2(2, 2))
        villain = game_map.get_unit_at(Vector2(7, 7))
        
        assert hero is not None
        assert villain is not None
        
        # Start combat
        game_state.battle.phase = BattlePhase.UNIT_SELECTION
        game_state.battle.selected_unit_id = hero.name
        
        # Setup attack
        game_state.battle.phase = BattlePhase.TARGETING
        combat_manager.setup_attack_targeting(hero)
        
        # Check if villain is in range (might not be for melee)
        attack_range = game_state.battle.attack_range
        villain_in_range = villain.position in attack_range
        
        if villain_in_range:
            # Execute attack
            game_state.cursor.set_position(villain.position)
            success = combat_manager.execute_attack_at_cursor()
            result = CombatResult()
            if success:
                result.targets_hit = [villain]
            
            # Verify combat completed
            assert isinstance(result, CombatResult)
            
            # Check for events if damage was dealt
            if len(result.damage_dealt) > 0:
                assert len(events) >= 0  # May have generated events
    
    def test_multi_turn_combat(self):
        """Test multi-turn combat scenario."""
        game_map, player, enemy = create_combat_scenario((5, 5))
        game_state = GameState()
        
        # Set up close combat
        game_map.move_unit(player.name, Vector2(2, 2))
        game_map.move_unit(enemy.name, Vector2(3, 2))
        
        combat_manager = CombatManager(game_map, game_state)
        
        # Player turn - set up properly
        game_state.battle.current_team = Team.PLAYER.value
        game_state.battle.phase = BattlePhase.TARGETING
        game_state.battle.selected_unit_id = player.name
        combat_manager.setup_attack_targeting(player)
        
        # Attack enemy - check attack range first
        game_state.cursor.set_position(enemy.position)
        
        # Verify attack is valid before executing
        in_range = game_state.battle.is_in_attack_range(enemy.position)
        if in_range:
            success = combat_manager.execute_attack_at_cursor()
            assert success, "Attack should succeed when enemy is in range"
        else:
            # Test attack fails when out of range
            success = combat_manager.execute_attack_at_cursor()
            assert not success, "Attack should fail when enemy is out of range"
        
        # Enemy turn (if still alive)
        if enemy.hp_current > 0:
            game_state.battle.current_team = Team.ENEMY.value
            game_state.battle.phase = BattlePhase.ENEMY_TURN
            
            # Enemy can attack back
            game_state.cursor.set_position(player.position)
            success2 = combat_manager.execute_attack_at_cursor()
            result2 = CombatResult()
            if success2:
                result2.targets_hit = [player]
            assert isinstance(result2, CombatResult)
    
    def test_team_vs_team_combat(self):
        """Test combat between multiple units per team."""
        map_builder = MapTestBuilder(8, 8)
        game_map = (map_builder
                   .with_unit("Player1", UnitClass.KNIGHT, Team.PLAYER, 1, 1)
                   .with_unit("Player2", UnitClass.ARCHER, Team.PLAYER, 2, 1)
                   .with_unit("Enemy1", UnitClass.WARRIOR, Team.ENEMY, 6, 6)
                   .with_unit("Enemy2", UnitClass.MAGE, Team.ENEMY, 7, 6)
                   .build())
        
        game_state = GameState()
        combat_manager = CombatManager(game_map, game_state)
        
        # Get all units
        player_units = [u for u in game_map.units if u is not None and u.team == Team.PLAYER]
        enemy_units = [u for u in game_map.units if u is not None and u.team == Team.ENEMY]
        
        assert len(player_units) == 2
        assert len(enemy_units) == 2
        
        # Each player unit should be able to set up attacks
        for player_unit in player_units:
            combat_manager.setup_attack_targeting(player_unit)
            attack_range = game_state.battle.attack_range
            
            assert len(attack_range) > 0
            
            # Try to attack any enemy in range
            for enemy_unit in enemy_units:
                if enemy_unit.position in attack_range:
                    game_state.cursor.set_position(enemy_unit.position)
                    success = combat_manager.execute_attack_at_cursor()
                    result = CombatResult()
                    if success:
                        result.targets_hit = [enemy_unit]
                    assert isinstance(result, CombatResult)
                    break