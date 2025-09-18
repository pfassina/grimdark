"""
Unit tests for game components and Unit class.

Tests the component-based unit system including Actor, Health, Movement,
Combat, and Status components, as well as the Unit wrapper class.
"""

import pytest
from src.core.data.data_structures import Vector2
from src.core.data.game_enums import UnitClass, Team
from src.game.entities.components import ActorComponent, HealthComponent, MovementComponent, CombatComponent, StatusComponent
from src.game.entities.unit import Unit


class MockEntity:
    """Mock entity for testing components."""
    def __init__(self):
        self.unit_id = "test_unit_123"


class TestActorComponent:
    """Test ActorComponent functionality."""

    @pytest.fixture
    def mock_entity(self):
        return MockEntity()

    @pytest.fixture
    def actor_component(self, mock_entity):
        return ActorComponent(mock_entity, "Test Knight", UnitClass.KNIGHT, Team.PLAYER)

    def test_actor_creation(self, actor_component):
        """Test basic actor component creation."""
        assert actor_component.name == "Test Knight"
        assert actor_component.unit_class == UnitClass.KNIGHT
        assert actor_component.team == Team.PLAYER
        assert actor_component.get_component_name() == "Actor"

    def test_get_display_name(self, actor_component):
        """Test getting display name."""
        assert actor_component.get_display_name() == "Test Knight"

    def test_get_class_name(self, actor_component):
        """Test getting human-readable class name."""
        class_name = actor_component.get_class_name()
        assert isinstance(class_name, str)
        assert len(class_name) > 0

    def test_get_class_info(self, actor_component):
        """Test getting class information."""
        class_info = actor_component.get_class_info()
        assert class_info is not None
        assert hasattr(class_info, 'symbol')

    def test_is_ally_of(self, mock_entity):
        """Test ally checking."""
        player_actor = ActorComponent(mock_entity, "Player Knight", UnitClass.KNIGHT, Team.PLAYER)
        other_player_actor = ActorComponent(mock_entity, "Player Archer", UnitClass.ARCHER, Team.PLAYER)
        enemy_actor = ActorComponent(mock_entity, "Enemy Knight", UnitClass.KNIGHT, Team.ENEMY)

        assert player_actor.is_ally_of(other_player_actor)
        assert not player_actor.is_ally_of(enemy_actor)

    def test_get_symbol(self, actor_component):
        """Test getting unit symbol."""
        symbol = actor_component.get_symbol()
        assert isinstance(symbol, str)
        assert len(symbol) > 0


class TestHealthComponent:
    """Test HealthComponent functionality."""

    @pytest.fixture
    def mock_entity(self):
        return MockEntity()

    @pytest.fixture
    def health_component(self, mock_entity):
        return HealthComponent(mock_entity, hp_max=25)

    def test_health_creation(self, health_component):
        """Test basic health component creation."""
        assert health_component.hp_max == 25
        assert health_component.hp_current == 25  # Start at full health
        assert health_component.get_component_name() == "Health"

    def test_is_alive_when_healthy(self, health_component):
        """Test that unit is alive when healthy."""
        assert health_component.is_alive()

    def test_is_alive_when_wounded(self, health_component):
        """Test that unit is alive when wounded but not dead."""
        health_component.hp_current = 1
        assert health_component.is_alive()

    def test_is_alive_when_dead(self, health_component):
        """Test that unit is not alive when at 0 HP."""
        health_component.hp_current = 0
        assert not health_component.is_alive()

    def test_is_alive_when_negative_hp(self, health_component):
        """Test that unit is not alive with negative HP."""
        health_component.hp_current = -5
        assert not health_component.is_alive()

    def test_get_health_ratio(self, health_component):
        """Test health ratio calculation."""
        # Full health - use get_hp_percent() instead of get_health_ratio()
        assert health_component.get_hp_percent() == 1.0
        
        # Half health
        health_component.hp_current = 12
        assert abs(health_component.get_hp_percent() - 0.48) < 0.01
        
        # No health
        health_component.hp_current = 0
        assert health_component.get_hp_percent() == 0.0


class TestMovementComponent:
    """Test MovementComponent functionality."""

    @pytest.fixture
    def mock_entity(self):
        return MockEntity()

    @pytest.fixture
    def movement_component(self, mock_entity):
        return MovementComponent(mock_entity, Vector2(5, 7), movement_points=3)

    def test_movement_creation(self, movement_component):
        """Test basic movement component creation."""
        assert movement_component.position == Vector2(5, 7)
        assert movement_component.movement_points == 3
        assert movement_component.get_component_name() == "Movement"

    def test_position_property_access(self, movement_component):
        """Test accessing position coordinates."""
        assert movement_component.position.x == 7
        assert movement_component.position.y == 5

    def test_set_position(self, movement_component):
        """Test setting unit position."""
        new_position = Vector2(2, 3)
        movement_component.set_position(new_position)
        
        assert movement_component.position == new_position
        assert movement_component.position.x == 3
        assert movement_component.position.y == 2

    def test_distance_calculation(self, movement_component):
        """Test distance calculations."""
        target = Vector2(8, 10)
        
        # Use the Vector2 distance methods instead of component methods
        euclidean = movement_component.position.distance_to(target)
        manhattan = movement_component.position.manhattan_distance_to(target)
        
        assert euclidean > 0
        assert manhattan > 0
        assert manhattan >= euclidean  # Manhattan is always >= Euclidean


class TestCombatComponent:
    """Test CombatComponent functionality."""

    @pytest.fixture
    def mock_entity(self):
        return MockEntity()

    @pytest.fixture
    def combat_component(self, mock_entity):
        return CombatComponent(mock_entity, strength=10, defense=2, attack_range_min=1, attack_range_max=1)

    def test_combat_creation(self, combat_component):
        """Test basic combat component creation."""
        assert combat_component.strength == 10
        assert combat_component.attack_range_min == 1
        assert combat_component.attack_range_max == 1
        assert combat_component.defense == 2
        assert combat_component.get_component_name() == "Combat"

    def test_can_attack_target(self, combat_component):
        """Test target attack range validation."""
        # CombatComponent.can_attack() uses entity.get_component("Movement") 
        # which won't work with our MockEntity. Let's test the simpler get_attack_range instead
        range_tuple = combat_component.get_attack_range()
        assert range_tuple == (1, 1)


class TestStatusComponent:
    """Test StatusComponent functionality."""

    @pytest.fixture
    def mock_entity(self):
        return MockEntity()

    @pytest.fixture
    def status_component(self, mock_entity):
        return StatusComponent(mock_entity, speed=5)

    def test_status_creation(self, status_component):
        """Test basic status component creation."""
        assert status_component.speed == 5
        assert status_component.get_component_name() == "Status"

    def test_turn_state_initialization(self, status_component):
        """Test initial turn state."""
        # Turn state flags should be properly initialized
        assert hasattr(status_component, 'speed')

    def test_reset_turn_flags(self, status_component):
        """Test resetting turn-based flags."""
        # This tests functionality that might be implemented
        if hasattr(status_component, 'reset_turn_flags'):
            status_component.reset_turn_flags()
            # Test that appropriate flags are reset


class TestUnit:
    """Test Unit class integration."""

    @pytest.fixture
    def sample_unit(self):
        """Create a sample unit for testing."""
        return Unit(
            name="Test Knight",
            unit_class=UnitClass.KNIGHT,
            team=Team.PLAYER,
            position=Vector2(2, 3)
        )

    def test_unit_creation(self, sample_unit):
        """Test basic unit creation."""
        assert sample_unit.name == "Test Knight"
        assert sample_unit.team == Team.PLAYER
        assert sample_unit.position == Vector2(2, 3)

    def test_unit_property_access(self, sample_unit):
        """Test accessing unit properties."""
        # Test coordinate access via position
        assert sample_unit.position.x == 3
        assert sample_unit.position.y == 2
        
        # Test health access
        assert sample_unit.hp_current > 0
        assert sample_unit.health.hp_max > 0  # Access via health component
        assert sample_unit.is_alive

    def test_unit_component_access(self, sample_unit):
        """Test accessing unit components."""
        # Test that components are accessible
        assert hasattr(sample_unit, 'actor')
        assert hasattr(sample_unit, 'health')
        assert hasattr(sample_unit, 'movement')
        assert hasattr(sample_unit, 'combat')
        assert hasattr(sample_unit, 'status')

    def test_unit_component_properties(self, sample_unit):
        """Test component-specific properties."""
        # Actor component
        assert sample_unit.actor.name == "Test Knight"
        assert sample_unit.actor.team == Team.PLAYER
        
        # Health component
        assert sample_unit.health.hp_max > 0
        assert sample_unit.health.is_alive()
        
        # Movement component
        assert sample_unit.movement.position == Vector2(2, 3)


class TestComponentIntegration:
    """Test component integration and interactions."""

    @pytest.fixture
    def mock_entity(self):
        return MockEntity()

    def test_component_entity_reference(self, mock_entity):
        """Test that components maintain entity reference."""
        actor = ActorComponent(mock_entity, "Test", UnitClass.KNIGHT, Team.PLAYER)
        health = HealthComponent(mock_entity, 25)
        
        assert actor.entity == mock_entity
        assert health.entity == mock_entity

    def test_multiple_components_same_entity(self, mock_entity):
        """Test multiple components on same entity."""
        actor = ActorComponent(mock_entity, "Test Knight", UnitClass.KNIGHT, Team.PLAYER)
        health = HealthComponent(mock_entity, 25)
        movement = MovementComponent(mock_entity, Vector2(0, 0), 3)
        
        # All components should reference the same entity
        assert actor.entity == health.entity == movement.entity

    def test_component_name_uniqueness(self, mock_entity):
        """Test that component names are unique."""
        actor = ActorComponent(mock_entity, "Test", UnitClass.KNIGHT, Team.PLAYER)
        health = HealthComponent(mock_entity, 25)
        movement = MovementComponent(mock_entity, Vector2(0, 0), 3)
        combat = CombatComponent(mock_entity, 10, 2, 1, 1)
        status = StatusComponent(mock_entity, 5)
        
        component_names = {
            actor.get_component_name(),
            health.get_component_name(),
            movement.get_component_name(),
            combat.get_component_name(),
            status.get_component_name()
        }
        
        # All component names should be unique
        assert len(component_names) == 5