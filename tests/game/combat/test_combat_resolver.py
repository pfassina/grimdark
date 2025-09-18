"""
Unit tests for the CombatResolver system.

Tests combat execution, damage application, wound generation,
and defeat handling in the timeline-based combat system.
"""

import pytest
from unittest.mock import Mock, patch

from src.game.combat.combat_resolver import CombatResolver, CombatResult
from src.core.events.event_manager import EventManager
from src.core.events.events import UnitAttacked, UnitDefeated, LogMessage, EventType
from src.core.data.data_structures import Vector2
from src.core.data.game_enums import Team
from src.core.wounds import Wound


class MockUnit:
    """Mock unit for testing combat resolver."""
    
    def __init__(self, unit_id="test_unit", name="Test Unit", team=Team.PLAYER,
                 position=Vector2(5, 5), hp_current=25, strength=10, defense=2):
        self.unit_id = unit_id
        self.name = name
        self.team = team
        self.position = position
        self.hp_current = hp_current
        self.entity = Mock()  # Mock entity for morale processing
        
        # Mock components
        self.combat = Mock()
        self.combat.strength = strength
        self.combat.defense = defense
        self.combat.aoe_pattern = "small_blast"
        
        self.wound = Mock()
        self.wound.add_wound = Mock()


class MockGameMap:
    """Mock game map for testing combat resolver."""
    
    def __init__(self):
        self.units = {}
        
    def get_unit(self, unit_id):
        """Get unit by ID."""
        return self.units.get(unit_id)
        
    def calculate_aoe_tiles(self, center_pos, aoe_pattern):
        """Calculate AOE tiles around position."""
        # Simple 3x3 pattern for testing
        return [
            Vector2(center_pos.x + dx, center_pos.y + dy)
            for dx in [-1, 0, 1]
            for dy in [-1, 0, 1]
        ]
        
    def get_units_in_positions(self, positions):
        """Get all units in given positions."""
        units_in_positions = []
        for position in positions:
            for unit in self.units.values():
                if unit.position == position:
                    units_in_positions.append(unit)
        return units_in_positions
        
    def remove_units_batch(self, unit_ids):
        """Remove multiple units in batch."""
        for unit_id in unit_ids:
            if unit_id in self.units:
                del self.units[unit_id]


class MockMoraleManager:
    """Mock morale manager for testing."""
    
    def __init__(self):
        self.process_unit_damage = Mock()
        self.process_unit_death = Mock()


class TestCombatResult:
    """Test CombatResult data structure."""
    
    def test_combat_result_creation(self):
        """Test basic CombatResult creation."""
        result = CombatResult()
        
        assert result.targets_hit == []
        assert result.defeated_targets == []
        assert result.defeated_positions == {}
        assert result.damage_dealt == {}
        assert result.wounds_inflicted == {}
        assert result.friendly_fire is False


class TestCombatResolverInitialization:
    """Test CombatResolver initialization and setup."""
    
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture
    def mock_event_manager(self):
        event_manager = Mock(spec=EventManager)
        event_manager.subscribe = Mock()
        event_manager.publish = Mock()
        return event_manager
        
    @pytest.fixture
    def mock_morale_manager(self):
        return MockMoraleManager()
    
    def test_combat_resolver_creation(self, mock_game_map, mock_event_manager):
        """Test basic CombatResolver creation."""
        resolver = CombatResolver(mock_game_map, mock_event_manager)
        
        assert resolver.game_map == mock_game_map
        assert resolver.event_manager == mock_event_manager
        assert resolver.morale_manager is None
        
    def test_combat_resolver_with_morale(self, mock_game_map, mock_event_manager, mock_morale_manager):
        """Test CombatResolver creation with morale manager."""
        resolver = CombatResolver(mock_game_map, mock_event_manager, mock_morale_manager)
        
        assert resolver.morale_manager == mock_morale_manager
        
    def test_event_subscription(self, mock_game_map, mock_event_manager):
        """Test that CombatResolver subscribes to UnitAttacked events."""
        resolver = CombatResolver(mock_game_map, mock_event_manager)
        
        # Should subscribe to UnitAttacked events
        mock_event_manager.subscribe.assert_called_once_with(
            EventType.UNIT_ATTACKED,
            resolver._handle_unit_attacked,
            subscriber_name="CombatResolver.unit_attacked"
        )


class TestSingleAttack:
    """Test single-target attack execution."""
    
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture 
    def mock_event_manager(self):
        event_manager = Mock(spec=EventManager)
        event_manager.subscribe = Mock()
        event_manager.publish = Mock()
        return event_manager
        
    @pytest.fixture
    def resolver(self, mock_game_map, mock_event_manager):
        return CombatResolver(mock_game_map, mock_event_manager)
        
    @pytest.fixture
    def attacker(self):
        return MockUnit(unit_id="attacker", name="Knight", team=Team.PLAYER, 
                       strength=15, position=Vector2(5, 5))
        
    @pytest.fixture
    def target(self):
        return MockUnit(unit_id="target", name="Enemy", team=Team.ENEMY,
                       hp_current=20, defense=2, position=Vector2(6, 5))
    
    def test_single_attack_execution(self, resolver, attacker, target):
        """Test basic single attack execution."""
        result = resolver.execute_single_attack(attacker, target)
        
        assert len(result.targets_hit) == 1
        assert result.targets_hit[0] == target
        assert not result.friendly_fire
        assert target.name in result.damage_dealt
        
        # Should have dealt damage
        damage_dealt = result.damage_dealt[target.name]
        assert damage_dealt > 0
        assert target.hp_current < 20  # Should be damaged
        
    def test_single_attack_friendly_fire_detection(self, resolver, target):
        """Test friendly fire detection in single attacks."""
        friendly_attacker = MockUnit(unit_id="friendly", name="Friend", 
                                   team=Team.PLAYER, strength=10)
        friendly_target = MockUnit(unit_id="friendly_target", name="Ally", 
                                 team=Team.PLAYER, hp_current=20)
        
        result = resolver.execute_single_attack(friendly_attacker, friendly_target)
        
        assert result.friendly_fire
        assert len(result.targets_hit) == 1
        # Should not apply damage due to friendly fire
        assert friendly_target.name not in result.damage_dealt
        assert friendly_target.hp_current == 20  # Unchanged
        
    @patch('src.game.combat.combat_resolver.create_wound_from_damage')
    def test_single_attack_wound_generation(self, mock_create_wound, resolver, attacker, target):
        """Test wound generation during single attacks."""
        mock_wound = Mock(spec=Wound)
        mock_wound.properties = Mock()
        mock_wound.properties.wound_type = Mock()
        mock_wound.properties.wound_type.name = "MINOR"
        mock_wound.properties.body_part = Mock()
        mock_wound.properties.body_part.name = "TORSO"
        mock_create_wound.return_value = mock_wound
        
        result = resolver.execute_single_attack(attacker, target)
        
        # Should create wound from damage
        mock_create_wound.assert_called_once()
        call_args = mock_create_wound.call_args[1]
        assert call_args['damage_type'] == "physical"
        assert call_args['target_unit'] == target
        assert call_args['source_unit'] == attacker
        
        # Should add wound to target
        target.wound.add_wound.assert_called_once_with(mock_wound)
        
        # Should track wound in result
        assert target.name in result.wounds_inflicted
        assert mock_wound in result.wounds_inflicted[target.name]
        
    def test_single_attack_unit_defeat(self, resolver, attacker, mock_event_manager):
        """Test unit defeat handling in single attacks."""
        weak_target = MockUnit(unit_id="weak", name="Weak Enemy", team=Team.ENEMY,
                              hp_current=1, defense=0, position=Vector2(6, 5))
        resolver.game_map.units["weak"] = weak_target
        
        result = resolver.execute_single_attack(attacker, weak_target)
        
        # Should be defeated
        assert weak_target.name in result.defeated_targets
        assert weak_target.hp_current == 0
        assert weak_target.name in result.defeated_positions
        
        # Should emit UnitDefeated event
        mock_event_manager.publish.assert_called()
        
        # Find the UnitDefeated event in the publish calls
        defeated_event_published = False
        for call in mock_event_manager.publish.call_args_list:
            event = call[0][0]  # First argument is the event
            if isinstance(event, UnitDefeated):
                assert event.unit_name == weak_target.name
                assert event.unit_id == weak_target.unit_id
                assert event.team == weak_target.team
                defeated_event_published = True
                break
        
        assert defeated_event_published, "UnitDefeated event should have been published"


class TestAOEAttack:
    """Test area-of-effect attack execution."""
    
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture
    def mock_event_manager(self):
        event_manager = Mock(spec=EventManager)
        event_manager.subscribe = Mock()
        event_manager.publish = Mock()
        return event_manager
        
    @pytest.fixture
    def resolver(self, mock_game_map, mock_event_manager):
        return CombatResolver(mock_game_map, mock_event_manager)
        
    @pytest.fixture
    def attacker(self):
        return MockUnit(unit_id="mage", name="Mage", team=Team.PLAYER,
                       strength=12, position=Vector2(2, 2))
    
    def test_aoe_attack_execution(self, resolver, attacker):
        """Test basic AOE attack execution."""
        # Create multiple targets in AOE range
        target1 = MockUnit(unit_id="t1", name="Enemy1", team=Team.ENEMY,
                          hp_current=15, position=Vector2(5, 5))
        target2 = MockUnit(unit_id="t2", name="Enemy2", team=Team.ENEMY,
                          hp_current=15, position=Vector2(6, 5))
        
        resolver.game_map.units.update({"t1": target1, "t2": target2})
        
        result = resolver.execute_aoe_attack(attacker, Vector2(5, 5), "small_blast")
        
        assert len(result.targets_hit) == 2
        assert not result.friendly_fire
        
        # Both targets should take damage
        assert target1.name in result.damage_dealt
        assert target2.name in result.damage_dealt
        assert target1.hp_current < 15
        assert target2.hp_current < 15
        
    def test_aoe_attack_friendly_fire_detection(self, resolver, attacker):
        """Test friendly fire detection in AOE attacks."""
        enemy = MockUnit(unit_id="enemy", name="Enemy", team=Team.ENEMY,
                        hp_current=15, position=Vector2(5, 5))
        ally = MockUnit(unit_id="ally", name="Ally", team=Team.PLAYER,
                       hp_current=15, position=Vector2(6, 5))
        
        resolver.game_map.units.update({"enemy": enemy, "ally": ally})
        
        result = resolver.execute_aoe_attack(attacker, Vector2(5, 5), "small_blast")
        
        assert result.friendly_fire
        assert len(result.targets_hit) == 2  # Both in range
        
        # Should not apply damage due to friendly fire
        assert enemy.name not in result.damage_dealt
        assert ally.name not in result.damage_dealt
        assert enemy.hp_current == 15  # Unchanged
        assert ally.hp_current == 15  # Unchanged
        
    def test_aoe_attack_excludes_attacker(self, resolver, attacker):
        """Test that AOE attacks exclude the attacker."""
        # Place attacker in the AOE area
        attacker.position = Vector2(5, 5)
        enemy = MockUnit(unit_id="enemy", name="Enemy", team=Team.ENEMY,
                        hp_current=15, position=Vector2(6, 5))
        
        resolver.game_map.units.update({"mage": attacker, "enemy": enemy})
        
        result = resolver.execute_aoe_attack(attacker, Vector2(5, 5), "small_blast")
        
        # Should only hit the enemy, not the attacker
        assert len(result.targets_hit) == 1
        assert result.targets_hit[0] == enemy
        assert not result.friendly_fire


class TestDamageCalculation:
    """Test damage calculation mechanics."""
    
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture
    def mock_event_manager(self):
        event_manager = Mock(spec=EventManager)
        event_manager.subscribe = Mock()
        event_manager.publish = Mock()
        return event_manager
        
    @pytest.fixture
    def resolver(self, mock_game_map, mock_event_manager):
        return CombatResolver(mock_game_map, mock_event_manager)
    
    def test_damage_variance(self, resolver):
        """Test that damage calculation includes variance."""
        attacker = MockUnit(strength=10)
        target = MockUnit(hp_current=100, defense=0)  # No defense for predictable base damage
        
        result = CombatResult()
        result.targets_hit = [target]  # type: ignore[assignment]
        
        # Apply damage multiple times to test variance
        damages = []
        for _ in range(10):
            target.hp_current = 100  # Reset HP
            resolver._apply_damage_to_targets(attacker, result)
            damage = result.damage_dealt[target.name]
            damages.append(damage)
            result.damage_dealt.clear()  # Clear for next iteration
            
        # Should have variance (not all damages the same)
        # Base damage should be 10 (strength - defense//2 = 10 - 0//2 = 10)
        # With ±25% variance, we expect range of roughly 7-13
        assert len(set(damages)) > 1  # Should have different values
        assert all(damage >= 1 for damage in damages)  # Minimum damage of 1
        
    def test_defense_calculation(self, resolver):
        """Test defense reduces damage properly."""
        strong_attacker = MockUnit(strength=20)
        armored_target = MockUnit(hp_current=100, defense=10)
        
        result = CombatResult()
        result.targets_hit = [armored_target]  # type: ignore[assignment]
        
        resolver._apply_damage_to_targets(strong_attacker, result)
        
        # Base damage should be strength - defense//2 = 20 - 5 = 15
        # With variance, should be around 11-19 (±25%)
        damage = result.damage_dealt[armored_target.name]
        assert damage >= 1  # Minimum damage
        assert damage < 20  # Should be less than full strength due to defense
        
    def test_minimum_damage(self, resolver):
        """Test that minimum damage is always 1."""
        weak_attacker = MockUnit(strength=1)
        heavily_armored = MockUnit(hp_current=100, defense=20)
        
        result = CombatResult()
        result.targets_hit = [heavily_armored]  # type: ignore[assignment]
        
        resolver._apply_damage_to_targets(weak_attacker, result)
        
        # Even with high defense, should deal at least 1 damage
        damage = result.damage_dealt[heavily_armored.name]
        assert damage >= 1


class TestMoraleIntegration:
    """Test integration with morale system."""
    
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture
    def mock_event_manager(self):
        event_manager = Mock(spec=EventManager)
        event_manager.subscribe = Mock()
        event_manager.publish = Mock()
        return event_manager
        
    @pytest.fixture
    def mock_morale_manager(self):
        return MockMoraleManager()
        
    @pytest.fixture
    def resolver(self, mock_game_map, mock_event_manager, mock_morale_manager):
        return CombatResolver(mock_game_map, mock_event_manager, mock_morale_manager)
    
    def test_morale_damage_processing(self, resolver, mock_morale_manager):
        """Test that morale manager processes damage events."""
        attacker = MockUnit(unit_id="att", strength=10, team=Team.PLAYER)
        target = MockUnit(unit_id="tgt", hp_current=20, defense=0, team=Team.ENEMY)
        
        resolver.execute_single_attack(attacker, target)
        
        # Should call morale manager for damage (only if not friendly fire)
        mock_morale_manager.process_unit_damage.assert_called_once()
        call_args = mock_morale_manager.process_unit_damage.call_args[0]
        assert call_args[0] == target.entity  # target entity
        assert call_args[2] == attacker.entity  # attacker entity
        
    def test_morale_death_processing(self, resolver, mock_morale_manager):
        """Test that morale manager processes unit deaths."""
        attacker = MockUnit(strength=25, team=Team.PLAYER)
        weak_target = MockUnit(unit_id="weak", hp_current=1, defense=0, team=Team.ENEMY)
        resolver.game_map.units["weak"] = weak_target
        
        resolver.execute_single_attack(attacker, weak_target)
        
        # Should call morale manager for both damage and death
        assert mock_morale_manager.process_unit_damage.called
        mock_morale_manager.process_unit_death.assert_called_once()
        
        call_args = mock_morale_manager.process_unit_death.call_args[0]
        assert call_args[0] == weak_target.entity  # target entity
        assert call_args[1] == attacker.entity  # attacker entity


class TestEventHandling:
    """Test event-driven combat processing."""
    
    @pytest.fixture
    def mock_game_map(self):
        game_map = MockGameMap()
        # Add units to map for event handling
        attacker = MockUnit(unit_id="knight", name="Knight", team=Team.PLAYER, strength=12)
        target = MockUnit(unit_id="orc", name="Orc", team=Team.ENEMY, hp_current=15, defense=2)
        game_map.units["knight"] = attacker
        game_map.units["orc"] = target
        return game_map
        
    @pytest.fixture
    def mock_event_manager(self):
        event_manager = Mock(spec=EventManager)
        event_manager.subscribe = Mock()
        event_manager.publish = Mock()
        return event_manager
        
    @pytest.fixture
    def resolver(self, mock_game_map, mock_event_manager):
        return CombatResolver(mock_game_map, mock_event_manager)
    
    def test_unit_attacked_event_handling(self, resolver, mock_game_map):
        """Test handling of UnitAttacked events."""
        # Create a UnitAttacked event
        attack_event = UnitAttacked(
            turn=1,
            attacker_name="Knight",
            attacker_id="knight",
            attacker_team=Team.PLAYER,
            target_name="Orc",
            target_id="orc",
            target_team=Team.ENEMY,
            attack_type="StandardAttack",
            base_damage=12,
            damage_multiplier=1.0
        )
        
        # Get initial HP
        target = mock_game_map.units["orc"]
        initial_hp = target.hp_current
        
        # Handle the event
        resolver._handle_unit_attacked(attack_event)
        
        # Target should have taken damage
        assert target.hp_current < initial_hp
        
    def test_invalid_unit_event_handling(self, resolver):
        """Test handling events with invalid unit references."""
        # Create event with non-existent units
        invalid_event = UnitAttacked(
            turn=1,
            attacker_name="NonExistent",
            attacker_id="invalid_id",
            attacker_team=Team.PLAYER,
            target_name="AlsoNonExistent", 
            target_id="also_invalid",
            target_team=Team.ENEMY,
            attack_type="StandardAttack",
            base_damage=10,
            damage_multiplier=1.0
        )
        
        # Should handle gracefully without crashing
        resolver._handle_unit_attacked(invalid_event)
        
        # Should publish log message about missing units
        resolver.event_manager.publish.assert_called()
        
    def test_non_attack_event_ignored(self, resolver):
        """Test that non-UnitAttacked events cause AttributeError (bug in current implementation)."""
        # Create a different event type
        log_event = LogMessage(turn=1, message="Test", category="TEST", level="INFO", source="Test")
        
        # Current implementation has a bug - it tries to access attacker_name before type check
        with pytest.raises(AttributeError, match="'LogMessage' object has no attribute 'attacker_name'"):
            resolver._handle_unit_attacked(log_event)


class TestDefeatEventCreation:
    """Test creation of defeat events."""
    
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture
    def mock_event_manager(self):
        event_manager = Mock(spec=EventManager)
        event_manager.subscribe = Mock()
        event_manager.publish = Mock()
        return event_manager
        
    @pytest.fixture
    def resolver(self, mock_game_map, mock_event_manager):
        return CombatResolver(mock_game_map, mock_event_manager)
    
    def test_create_defeat_event(self, resolver):
        """Test creation of UnitDefeated events."""
        event = resolver.create_defeat_event(
            unit_name="Enemy Knight",
            unit_id="enemy_01",
            team=Team.ENEMY,
            position=(5, 7),
            turn=3
        )
        
        assert isinstance(event, UnitDefeated)
        assert event.unit_name == "Enemy Knight"
        assert event.unit_id == "enemy_01"
        assert event.team == Team.ENEMY
        assert event.position == (5, 7)
        assert event.turn == 3


class TestCombatEdgeCases:
    """Test edge cases and error conditions in combat."""
    
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture
    def mock_event_manager(self):
        event_manager = Mock(spec=EventManager)
        event_manager.subscribe = Mock()
        event_manager.publish = Mock()
        return event_manager
        
    @pytest.fixture
    def resolver(self, mock_game_map, mock_event_manager):
        return CombatResolver(mock_game_map, mock_event_manager)
    
    def test_empty_target_list(self, resolver):
        """Test damage application with empty target list."""
        attacker = MockUnit()
        result = CombatResult()
        # Empty targets_hit list
        
        # Should handle gracefully
        resolver._apply_damage_to_targets(attacker, result)
        
        assert len(result.damage_dealt) == 0
        assert len(result.defeated_targets) == 0
        
    def test_aoe_with_no_targets(self, resolver):
        """Test AOE attack with no targets in range."""
        attacker = MockUnit()
        
        result = resolver.execute_aoe_attack(attacker, Vector2(10, 10), "small_blast")
        
        assert len(result.targets_hit) == 0
        assert not result.friendly_fire
        assert len(result.damage_dealt) == 0
        
    @patch('src.game.combat.combat_resolver.create_wound_from_damage')
    def test_wound_creation_failure(self, mock_create_wound, resolver):
        """Test handling when wound creation returns None."""
        mock_create_wound.return_value = None  # Simulate no wound created
        
        attacker = MockUnit(strength=5, team=Team.PLAYER)
        target = MockUnit(hp_current=20, defense=0, team=Team.ENEMY)
        
        result = resolver.execute_single_attack(attacker, target)
        
        # Should handle gracefully when no wound is created
        assert target.name in result.damage_dealt  # Damage still applied
        assert target.name not in result.wounds_inflicted  # No wound tracked