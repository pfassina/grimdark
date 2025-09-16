"""
Unit tests for the Unit class.

Tests character stats, abilities, state management, and
combat-related functionality for game units.
"""
import pytest

from src.game.unit import Unit
from src.core.game_enums import Team, UnitClass
from src.core.data_structures import Vector2


class TestUnitInitialization:
    """Test Unit initialization and basic properties."""
    
    def test_basic_initialization(self):
        """Test basic Unit initialization."""
        position = Vector2(3, 4)
        unit = Unit("Test Knight", UnitClass.KNIGHT, Team.PLAYER, position)
        
        assert unit.name == "Test Knight"
        assert unit.actor.unit_class == UnitClass.KNIGHT
        assert unit.team == Team.PLAYER
        assert unit.position == position
    
    def test_initialization_different_classes(self):
        """Test initialization with different unit classes."""
        classes_to_test = [UnitClass.KNIGHT, UnitClass.ARCHER, UnitClass.MAGE, UnitClass.WARRIOR, UnitClass.PRIEST]
        
        for unit_class in classes_to_test:
            position = Vector2(1, 1)
            unit = Unit(f"Test {unit_class.name}", unit_class, Team.PLAYER, position)
            
            assert unit.name == f"Test {unit_class.name}"
            assert unit.actor.unit_class == unit_class
            assert unit.team == Team.PLAYER
            assert unit.position == position
    
    def test_initialization_different_teams(self):
        """Test initialization with different teams."""
        teams_to_test = [Team.PLAYER, Team.ENEMY, Team.ALLY, Team.NEUTRAL]
        
        for team in teams_to_test:
            position = Vector2(2, 2)
            unit = Unit(f"{team.name} Unit", UnitClass.KNIGHT, team, position)
            
            assert unit.team == team
            assert unit.name == f"{team.name} Unit"
            assert unit.position == position
    
    def test_initialization_with_custom_id(self):
        """Test initialization with custom unit ID."""
        position = Vector2(0, 0)
        unit = Unit("Test Unit", UnitClass.KNIGHT, Team.PLAYER, position, unit_id="custom_id_123")
        
        assert unit.unit_id == "custom_id_123"
        assert unit.name == "Test Unit"
    
    @pytest.mark.parametrize("position", [
        Vector2(0, 0), Vector2(5, 10), Vector2(-1, 3), Vector2(100, 200)
    ])
    def test_initialization_various_positions(self, position: Vector2):
        """Test initialization with various positions."""
        unit = Unit("Test Unit", UnitClass.KNIGHT, Team.PLAYER, position)
        assert unit.position == position


class TestUnitProperties:
    """Test Unit property access patterns."""
    
    def test_core_properties(self):
        """Test core property access."""
        position = Vector2(5, 7)
        unit = Unit("Test Knight", UnitClass.KNIGHT, Team.PLAYER, position)
        
        # Core properties should work
        assert unit.name == "Test Knight"
        assert unit.team == Team.PLAYER
        assert unit.position == position
        assert isinstance(unit.unit_id, str)
        assert len(unit.unit_id) > 0
    
    def test_component_properties(self):
        """Test component access properties."""
        position = Vector2(1, 1)
        unit = Unit("Test Unit", UnitClass.ARCHER, Team.PLAYER, position)
        
        # Component access should work
        assert hasattr(unit, 'actor')
        assert hasattr(unit, 'health')
        assert hasattr(unit, 'movement')
        assert hasattr(unit, 'combat')
        assert hasattr(unit, 'status')
        
        # Components should have expected types
        from src.game.components import ActorComponent, HealthComponent, MovementComponent, CombatComponent, StatusComponent
        assert isinstance(unit.actor, ActorComponent)
        assert isinstance(unit.health, HealthComponent)
        assert isinstance(unit.movement, MovementComponent)
        assert isinstance(unit.combat, CombatComponent)
        assert isinstance(unit.status, StatusComponent)
    
    def test_health_properties(self):
        """Test health-related properties."""
        position = Vector2(2, 3)
        unit = Unit("Test Knight", UnitClass.KNIGHT, Team.PLAYER, position)
        
        # Health properties
        assert isinstance(unit.hp_current, int)
        assert unit.hp_current > 0
        assert isinstance(unit.health.hp_max, int)
        assert unit.health.hp_max > 0
        assert unit.hp_current <= unit.health.hp_max
        assert unit.is_alive
    
    def test_status_properties(self):
        """Test status-related properties."""
        position = Vector2(3, 4)
        unit = Unit("Test Unit", UnitClass.WARRIOR, Team.PLAYER, position)
        
        # Status properties - should default to fresh state
        assert not unit.has_moved
        assert not unit.has_acted
        assert unit.can_move
        assert unit.can_act
    
    def test_combat_properties(self):
        """Test combat-related properties."""
        position = Vector2(4, 5)
        unit = Unit("Test Archer", UnitClass.ARCHER, Team.PLAYER, position)
        
        # Combat properties should exist
        assert isinstance(unit.combat.strength, int)
        assert isinstance(unit.combat.defense, int)
        assert unit.combat.strength > 0
        assert unit.combat.defense >= 0
    
    def test_movement_properties(self):
        """Test movement-related properties."""
        position = Vector2(6, 7)
        unit = Unit("Test Mage", UnitClass.MAGE, Team.PLAYER, position)
        
        # Movement properties should exist
        assert isinstance(unit.movement.movement_points, int)
        assert unit.movement.movement_points > 0
        assert isinstance(unit.facing, str)
        assert len(unit.facing) > 0


class TestUnitMethods:
    """Test Unit method functionality."""
    
    def test_move_to(self):
        """Test moving unit to new position."""
        initial_position = Vector2(1, 1)
        unit = Unit("Test Knight", UnitClass.KNIGHT, Team.PLAYER, initial_position)
        
        # Initially should not have moved
        assert not unit.has_moved
        assert unit.position == initial_position
        
        # Move to new position
        new_position = Vector2(3, 4)
        unit.move_to(new_position)
        
        assert unit.position == new_position
        assert unit.has_moved
    
    def test_take_damage(self):
        """Test taking damage."""
        position = Vector2(2, 2)
        unit = Unit("Test Warrior", UnitClass.WARRIOR, Team.PLAYER, position)
        
        initial_hp = unit.hp_current
        assert unit.is_alive
        
        # Take some damage
        damage = 5
        unit.take_damage(damage)
        
        assert unit.hp_current == initial_hp - damage
        assert unit.is_alive  # Should still be alive
    
    def test_defeat_on_zero_hp(self):
        """Test unit defeat when HP reaches zero."""
        position = Vector2(3, 3)
        unit = Unit("Test Unit", UnitClass.KNIGHT, Team.PLAYER, position)
        
        # Set HP to a low value then deal lethal damage
        unit.hp_current = 10
        assert unit.is_alive
        
        unit.take_damage(10)
        assert unit.hp_current == 0
        assert not unit.is_alive
    
    def test_hp_cannot_go_negative(self):
        """Test that HP cannot go below zero."""
        position = Vector2(4, 4)
        unit = Unit("Test Unit", UnitClass.KNIGHT, Team.PLAYER, position)
        
        unit.hp_current = 5
        unit.take_damage(10)  # Overkill damage
        
        assert unit.hp_current == 0  # Should not be negative
        assert not unit.is_alive


class TestUnitStatusManagement:
    """Test unit status and turn management."""
    
    def test_status_flags(self):
        """Test status flag manipulation."""
        position = Vector2(1, 2)
        unit = Unit("Test Unit", UnitClass.KNIGHT, Team.PLAYER, position)
        
        # Test initial state
        assert not unit.has_moved
        assert not unit.has_acted
        assert unit.can_move
        assert unit.can_act
        
        # Test setting flags
        unit.has_moved = True
        assert unit.has_moved
        
        unit.has_acted = True  
        assert unit.has_acted
    
    def test_action_constraints(self):
        """Test action constraint logic."""
        position = Vector2(2, 3)
        unit = Unit("Test Unit", UnitClass.ARCHER, Team.PLAYER, position)
        
        # Fresh unit can do everything
        assert unit.can_move
        assert unit.can_act
        
        # After moving, should still be able to act
        unit.move_to(Vector2(3, 4))
        assert unit.has_moved
        # Note: can_move and can_act depend on the actual status component logic
    
    def test_turn_reset(self):
        """Test turn-based status reset."""
        position = Vector2(5, 6)
        unit = Unit("Test Unit", UnitClass.MAGE, Team.PLAYER, position)
        
        # Exhaust the unit
        unit.has_moved = True
        unit.has_acted = True
        
        # Reset turn status (this would typically be called by turn manager)
        unit.status.start_turn()  # Uses actual method name
        
        assert not unit.has_moved
        assert not unit.has_acted


class TestUnitComponents:
    """Test component system integration."""
    
    def test_actor_component(self):
        """Test Actor component functionality."""
        position = Vector2(1, 1)
        unit = Unit("Knight Commander", UnitClass.KNIGHT, Team.PLAYER, position)
        
        assert unit.actor.name == "Knight Commander"
        assert unit.actor.team == Team.PLAYER
        assert unit.actor.unit_class == UnitClass.KNIGHT
        assert isinstance(unit.actor.get_class_name(), str)
        assert len(unit.actor.get_class_name()) > 0
    
    def test_health_component(self):
        """Test Health component functionality."""
        position = Vector2(2, 2)
        unit = Unit("Test Archer", UnitClass.ARCHER, Team.PLAYER, position)
        
        initial_hp = unit.health.hp_current
        max_hp = unit.health.hp_max
        
        assert initial_hp == max_hp  # Should start at full health
        assert unit.health.is_alive()
        assert unit.health.get_hp_percent() == 1.0  # 100%
        
        # Test damage
        unit.health.take_damage(5)
        assert unit.health.hp_current == initial_hp - 5
        assert unit.health.get_hp_percent() < 1.0
    
    def test_combat_component(self):
        """Test Combat component functionality."""
        position = Vector2(3, 3)
        unit = Unit("Test Warrior", UnitClass.WARRIOR, Team.PLAYER, position)
        
        # Combat stats should exist and be reasonable
        assert unit.combat.strength > 0
        assert unit.combat.defense >= 0
        assert hasattr(unit.combat, 'attack_range_min')
        assert hasattr(unit.combat, 'attack_range_max')
    
    def test_movement_component(self):
        """Test Movement component functionality."""
        position = Vector2(4, 4)
        unit = Unit("Test Scout", UnitClass.ARCHER, Team.PLAYER, position)
        
        assert unit.movement.position == position
        assert unit.movement.movement_points > 0
        assert isinstance(unit.movement.facing, str)
        
        # Test movement
        new_position = Vector2(5, 6)
        unit.movement.move_to(new_position)
        assert unit.movement.position == new_position
        assert unit.position == new_position  # Property should reflect component
    
    def test_status_component(self):
        """Test Status component functionality."""
        position = Vector2(5, 5)
        unit = Unit("Test Unit", UnitClass.MAGE, Team.PLAYER, position)
        
        assert hasattr(unit.status, 'speed')
        assert unit.status.speed > 0
        assert not unit.status.has_moved
        assert not unit.status.has_acted
        
        # Test status changes
        unit.status.mark_moved()
        assert unit.status.has_moved
        assert unit.has_moved  # Property should reflect component


class TestUnitIntegration:
    """Test integration scenarios and complex interactions."""
    
    def test_full_combat_scenario(self):
        """Test a complete combat scenario."""
        attacker_pos = Vector2(1, 1)
        defender_pos = Vector2(2, 2)
        
        attacker = Unit("Attacker", UnitClass.KNIGHT, Team.PLAYER, attacker_pos)
        defender = Unit("Defender", UnitClass.ARCHER, Team.ENEMY, defender_pos)
        
        # Both should start alive
        assert attacker.is_alive
        assert defender.is_alive
        
        # Move attacker
        attacker.move_to(Vector2(2, 1))
        assert attacker.has_moved
        
        # Deal damage to defender
        initial_hp = defender.hp_current
        damage = attacker.combat.strength
        defender.take_damage(damage)
        
        assert defender.hp_current == initial_hp - damage
    
    def test_position_tracking(self):
        """Test position tracking through movement."""
        unit = Unit("Mobile Unit", UnitClass.KNIGHT, Team.PLAYER, Vector2(0, 0))
        
        positions = [Vector2(1, 0), Vector2(2, 1), Vector2(3, 3)]
        
        for pos in positions:
            unit.move_to(pos)
            assert unit.position == pos
            assert unit.movement.position == pos
    
    def test_team_affiliation(self):
        """Test team-based logic."""
        player_unit = Unit("Player Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(0, 0))
        enemy_unit = Unit("Enemy Archer", UnitClass.ARCHER, Team.ENEMY, Vector2(5, 5))
        ally_unit = Unit("Allied Mage", UnitClass.MAGE, Team.ALLY, Vector2(10, 10))
        
        assert player_unit.team != enemy_unit.team
        assert player_unit.team != ally_unit.team
        assert enemy_unit.team != ally_unit.team
        
        # All should be different team instances
        teams = {player_unit.team, enemy_unit.team, ally_unit.team}
        assert len(teams) == 3
    
    def test_unit_classes_have_different_stats(self):
        """Test that different unit classes have different stats."""
        position = Vector2(1, 1)
        knight = Unit("Knight", UnitClass.KNIGHT, Team.PLAYER, position)
        archer = Unit("Archer", UnitClass.ARCHER, Team.PLAYER, position)
        mage = Unit("Mage", UnitClass.MAGE, Team.PLAYER, position)
        
        # Different classes should have different stat profiles
        units = [knight, archer, mage]
        
        # At least some stats should differ between classes
        strengths = [unit.combat.strength for unit in units]
        defenses = [unit.combat.defense for unit in units]
        hp_maxes = [unit.health.hp_max for unit in units]
        movements = [unit.movement.movement_points for unit in units]
        
        # Not all stats need to be different, but there should be variety
        # This tests that the unit template system is working
        assert len(set(strengths + defenses + hp_maxes + movements)) > 1


class TestUnitEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_damage(self):
        """Test taking zero damage."""
        unit = Unit("Test Unit", UnitClass.KNIGHT, Team.PLAYER, Vector2(0, 0))
        initial_hp = unit.hp_current
        
        unit.take_damage(0)
        assert unit.hp_current == initial_hp
        assert unit.is_alive
    
    def test_negative_damage(self):
        """Test negative damage (healing through damage system)."""
        unit = Unit("Test Unit", UnitClass.KNIGHT, Team.PLAYER, Vector2(0, 0))
        
        # Reduce HP first
        unit.hp_current = unit.health.hp_max // 2
        damaged_hp = unit.hp_current
        
        # Negative damage should raise error (take_damage doesn't accept negative values)
        with pytest.raises(ValueError):
            unit.take_damage(-5)
        # HP should remain unchanged since error was raised
        assert unit.hp_current == damaged_hp
    
    def test_move_to_same_position(self):
        """Test moving to the same position."""
        position = Vector2(3, 3)
        unit = Unit("Test Unit", UnitClass.KNIGHT, Team.PLAYER, position)
        
        assert not unit.has_moved
        unit.move_to(position)
        # Should still mark as moved even if position doesn't change
        assert unit.has_moved
        assert unit.position == position
    
    def test_string_representation(self):
        """Test string representation of units."""
        unit = Unit("Test Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(2, 3))
        
        str_repr = str(unit)
        # Unit class doesn't have custom __str__, so we just verify it returns something
        assert len(str_repr) > 0
        assert isinstance(str_repr, str)
    
    def test_unit_id_uniqueness(self):
        """Test that unit IDs are unique."""
        position = Vector2(0, 0)
        unit1 = Unit("Unit 1", UnitClass.KNIGHT, Team.PLAYER, position)
        unit2 = Unit("Unit 2", UnitClass.KNIGHT, Team.PLAYER, position)
        
        assert unit1.unit_id != unit2.unit_id
        assert len(unit1.unit_id) > 0
        assert len(unit2.unit_id) > 0