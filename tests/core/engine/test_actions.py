"""
Unit tests for the Actions system.

Tests the action class hierarchy, validation logic, execution flows,
and timeline integration for the timeline-based combat system.
"""

import pytest
from unittest.mock import Mock

from src.core.engine import (
    Action, ActionCategory, ActionResult, ActionValidation,
    QuickStrike, QuickMove, StandardAttack, StandardMove, Wait,
    PowerAttack, ChargeAttack, OverwatchAction, ShieldWall,
    get_available_actions, create_action_by_name
)
from src.core.data import Vector2, Team, AOEPattern, VectorArray


class MockUnit:
    """Mock unit for testing actions."""
    
    def __init__(self, unit_id="test_unit", name="Test Unit", team=Team.PLAYER, 
                 position=Vector2(5, 5), is_alive=True, strength=10):
        self.unit_id = unit_id
        self.name = name
        self.team = team
        self.position = position
        self.is_alive = is_alive
        self.unit_class = Mock()
        self.unit_class.name = 'KNIGHT'
        
        # Mock components
        self.combat = Mock()
        self.combat.strength = strength
        self.combat.aoe_pattern = AOEPattern.SINGLE  # Required for new AttackAction
        
        self.movement = Mock()
        self.movement.movement_points = 3
        
        self.health = Mock()
        self.health.is_alive = Mock(return_value=is_alive)


class MockGameMap:
    """Mock game map for testing actions."""
    
    def __init__(self):
        self.units = {}
        self._mock_units_in_positions = []  # Units to return for AOE attacks
        
    def is_valid_position(self, position):
        """Check if position is valid."""
        return (0 <= position.x <= 20 and 0 <= position.y <= 20)
        
    def is_position_blocked(self, position, team):
        """Check if position is blocked."""
        return False  # Default: no blocking
        
    def move_unit(self, unit_id, position):
        """Move unit to position."""
        return True  # Default: movement succeeds
        
    def calculate_aoe_tiles(self, center, pattern):
        """Calculate AOE tiles for attacks."""
        # Simple mock: return center position for SINGLE, center + adjacent for others
        if pattern == AOEPattern.SINGLE:
            return VectorArray([center])
        else:
            # Return center + one adjacent tile for testing
            return VectorArray([center, Vector2(center.x + 1, center.y)])
            
    def get_units_in_positions(self, positions):
        """Get units in the given positions."""
        return self._mock_units_in_positions
        
    def set_mock_units_in_aoe(self, units):
        """Set which units should be returned by get_units_in_positions."""
        self._mock_units_in_positions = units


class TestActionEnums:
    """Test action-related enums and data classes."""
    
    def test_action_category_values(self):
        """Test ActionCategory enum values."""
        assert ActionCategory.QUICK
        assert ActionCategory.NORMAL
        assert ActionCategory.HEAVY
        assert ActionCategory.PREPARED
        
    def test_action_result_values(self):
        """Test ActionResult enum values."""
        assert ActionResult.SUCCESS
        assert ActionResult.FAILED
        assert ActionResult.CANCELLED
        assert ActionResult.INTERRUPTED
        assert ActionResult.REQUIRES_TARGET
        assert ActionResult.REQUIRES_INPUT


class TestActionValidation:
    """Test ActionValidation data class."""
    
    def test_validation_creation(self):
        """Test basic validation creation."""
        valid = ActionValidation(is_valid=True)
        assert valid.is_valid
        assert valid.reason == ""
        
        invalid = ActionValidation(is_valid=False, reason="Test reason")
        assert not invalid.is_valid
        assert invalid.reason == "Test reason"
        
    def test_validation_valid_factory(self):
        """Test valid() factory method."""
        validation = ActionValidation.valid()
        assert validation.is_valid
        assert validation.reason == ""
        
    def test_validation_invalid_factory(self):
        """Test invalid() factory method."""
        validation = ActionValidation.invalid("Test error")
        assert not validation.is_valid
        assert validation.reason == "Test error"


class TestActionBaseClass:
    """Test Action base class functionality."""
    
    class ConcreteTestAction(Action):
        """Concrete test action for testing base class."""
        
        def validate(self, actor, game_map, target=None):
            return ActionValidation.valid()
            
        def execute(self, actor, game_map, target=None, event_emitter=None):
            return ActionResult.SUCCESS
    
    @pytest.fixture
    def test_action(self):
        return self.ConcreteTestAction("Test Action", 100, ActionCategory.NORMAL)
        
    @pytest.fixture
    def mock_unit(self):
        return MockUnit()
    
    def test_action_creation(self, test_action):
        """Test basic action creation."""
        assert test_action.name == "Test Action"
        assert test_action.weight == 100
        assert test_action.category == ActionCategory.NORMAL
        assert test_action.is_interruptible
        assert not test_action.requires_line_of_sight
        assert test_action.max_range == 1
        
    def test_get_weight_modifier_default(self, test_action, mock_unit):
        """Test default weight modifier."""
        modifier = test_action.get_weight_modifier(mock_unit)
        assert modifier == 0
        
    def test_get_effective_weight(self, test_action, mock_unit):
        """Test effective weight calculation."""
        weight = test_action.get_effective_weight(mock_unit)
        assert weight == 100  # base weight + 0 modifier
        
    def test_can_interrupt_default(self, test_action):
        """Test default interrupt behavior."""
        assert not test_action.can_interrupt("any_condition")
        
    def test_get_description(self, test_action):
        """Test action description."""
        assert test_action.get_description() == "Test Action"
        
    def test_get_intent_description(self, test_action):
        """Test intent description for timeline display."""
        assert test_action.get_intent_description() == "Test Action"
        assert test_action.get_intent_description(hidden=True) == "???"


class TestQuickStrike:
    """Test QuickStrike action."""
    
    @pytest.fixture
    def action(self):
        return QuickStrike()
        
    @pytest.fixture
    def actor(self):
        return MockUnit(position=Vector2(5, 5))
        
    @pytest.fixture
    def target(self):
        return Vector2(5, 6)  # Adjacent position for attack
        
    @pytest.fixture
    def game_map(self):
        return MockGameMap()
    
    def test_quick_strike_creation(self, action):
        """Test QuickStrike initialization."""
        assert action.name == "Quick Strike"
        assert action.weight == 70
        assert action.category == ActionCategory.QUICK
        assert action.requires_line_of_sight
        assert action.max_range == 1
        
    def test_validate_success(self, action, actor, target, game_map):
        """Test successful validation."""
        # Set up an enemy target unit at the target position
        target_unit = MockUnit(unit_id="target", position=target, team=Team.ENEMY)
        game_map.set_mock_units_in_aoe([target_unit])
        
        validation = action.validate(actor, game_map, target)
        assert validation.is_valid
        
    def test_validate_no_target(self, action, actor, game_map):
        """Test validation with no target."""
        validation = action.validate(actor, game_map, None)
        assert not validation.is_valid
        assert "No target selected" in validation.reason
        
    def test_validate_invalid_target(self, action, actor, game_map):
        """Test validation with invalid target."""
        invalid_target = "not a position"
        validation = action.validate(actor, game_map, invalid_target)
        assert not validation.is_valid
        assert "Target must be" in validation.reason
        
    def test_validate_no_targets_in_area(self, action, actor, game_map):
        """Test validation with no valid targets in AOE area."""
        target_position = Vector2(5, 6)  # Adjacent position
        game_map.set_mock_units_in_aoe([])  # No units in AOE
        validation = action.validate(actor, game_map, target_position)
        assert not validation.is_valid
        assert "No valid targets in area" in validation.reason
        
    def test_validate_out_of_range(self, action, actor, game_map):
        """Test validation with out-of-range target."""
        far_position = Vector2(10, 10)  # Too far
        validation = action.validate(actor, game_map, far_position)
        assert not validation.is_valid
        assert "out of range" in validation.reason
        
    def test_execute_success_with_events(self, action, actor, target, game_map):
        """Test successful execution with event system."""
        # Set up an enemy target unit for successful execution
        target_unit = MockUnit(unit_id="target", position=target, team=Team.ENEMY)
        game_map.set_mock_units_in_aoe([target_unit])
        
        event_emitter = Mock()
        
        result = action.execute(actor, game_map, target, event_emitter)
        
        assert result == ActionResult.SUCCESS
        event_emitter.assert_called_once()
        
        # Verify event details
        call_args = event_emitter.call_args[0]
        attack_event = call_args[0]
        assert attack_event.attacker == actor
        assert attack_event.target == target_unit  # Event target is the unit, not position
        assert attack_event.damage_multiplier == 0.7
        
    def test_execute_requires_event_system(self, action, actor, target, game_map):
        """Test that execution requires event system."""
        # Set up an enemy target unit so validation passes
        target_unit = MockUnit(unit_id="target", position=target, team=Team.ENEMY)
        game_map.set_mock_units_in_aoe([target_unit])
        
        with pytest.raises(RuntimeError, match="Quick Strike requires event system"):
            action.execute(actor, game_map, target, None)
            
    def test_execute_failed_validation(self, action, actor, game_map):
        """Test execution with failed validation."""
        result = action.execute(actor, game_map, None)  # No target
        assert result == ActionResult.FAILED


class TestQuickMove:
    """Test QuickMove action."""
    
    @pytest.fixture
    def action(self):
        return QuickMove()
        
    @pytest.fixture
    def actor(self):
        return MockUnit(position=Vector2(5, 5))
        
    @pytest.fixture
    def game_map(self):
        return MockGameMap()
    
    def test_quick_move_creation(self, action):
        """Test QuickMove initialization."""
        assert action.name == "Quick Move"
        assert action.weight == 60
        assert action.category == ActionCategory.QUICK
        assert action.max_range == 2
        
    def test_validate_success(self, action, actor, game_map):
        """Test successful validation."""
        destination = Vector2(6, 5)  # 1 tile away
        validation = action.validate(actor, game_map, destination)
        assert validation.is_valid
        
    def test_validate_no_destination(self, action, actor, game_map):
        """Test validation with no destination."""
        validation = action.validate(actor, game_map, None)
        assert not validation.is_valid
        assert "No destination selected" in validation.reason
        
    def test_validate_invalid_destination(self, action, actor, game_map):
        """Test validation with invalid destination."""
        validation = action.validate(actor, game_map, "not a position")
        assert not validation.is_valid
        assert "Invalid destination" in validation.reason
        
    def test_validate_too_far(self, action, actor, game_map):
        """Test validation with destination too far."""
        far_destination = Vector2(10, 10)  # Too far
        validation = action.validate(actor, game_map, far_destination)
        assert not validation.is_valid
        assert "Too far" in validation.reason
        
    def test_validate_invalid_position(self, action, actor, game_map):
        """Test validation with invalid map position."""
        invalid_position = Vector2(6, 6)  # Within range but invalid position
        game_map.is_valid_position = Mock(return_value=False)
        
        validation = action.validate(actor, game_map, invalid_position)
        assert not validation.is_valid
        assert "Invalid position" in validation.reason
        
    def test_validate_blocked_position(self, action, actor, game_map):
        """Test validation with blocked position."""
        game_map.is_position_blocked = Mock(return_value=True)
        destination = Vector2(6, 5)
        
        validation = action.validate(actor, game_map, destination)
        assert not validation.is_valid
        assert "Position blocked" in validation.reason
        
    def test_execute_success(self, action, actor, game_map):
        """Test successful execution."""
        destination = Vector2(6, 5)
        game_map.move_unit = Mock(return_value=True)
        
        result = action.execute(actor, game_map, destination)
        
        assert result == ActionResult.SUCCESS
        game_map.move_unit.assert_called_once_with(actor.unit_id, destination)
        
    def test_execute_move_failed(self, action, actor, game_map):
        """Test execution when map movement fails."""
        destination = Vector2(6, 5)
        game_map.move_unit = Mock(return_value=False)
        
        result = action.execute(actor, game_map, destination)
        assert result == ActionResult.FAILED


class TestStandardAttack:
    """Test StandardAttack action."""
    
    @pytest.fixture
    def action(self):
        return StandardAttack()
        
    @pytest.fixture
    def actor(self):
        return MockUnit(position=Vector2(5, 5))
        
    @pytest.fixture
    def target(self):
        return Vector2(5, 6)
        
    @pytest.fixture
    def game_map(self):
        return MockGameMap()
    
    def test_standard_attack_creation(self, action):
        """Test StandardAttack initialization."""
        assert action.name == "Attack"
        assert action.weight == 100
        assert action.category == ActionCategory.NORMAL
        assert action.requires_line_of_sight
        assert action.max_range == 1
        
    def test_execute_success_with_events(self, action, actor, target, game_map):
        """Test successful execution with event system."""
        # Set up an enemy target unit for successful execution
        target_unit = MockUnit(unit_id="target", position=target, team=Team.ENEMY)
        game_map.set_mock_units_in_aoe([target_unit])
        
        event_emitter = Mock()
        
        result = action.execute(actor, game_map, target, event_emitter)
        
        assert result == ActionResult.SUCCESS
        event_emitter.assert_called_once()
        
        # Verify event details
        call_args = event_emitter.call_args[0]
        attack_event = call_args[0]
        assert attack_event.attacker == actor
        assert attack_event.target == target_unit  # Event target is the unit, not position
        assert attack_event.damage_multiplier == 1.0  # Full damage


class TestWait:
    """Test Wait action."""
    
    @pytest.fixture
    def action(self):
        return Wait()
        
    @pytest.fixture
    def actor(self):
        return MockUnit()
        
    @pytest.fixture
    def game_map(self):
        return MockGameMap()
    
    def test_wait_creation(self, action):
        """Test Wait initialization."""
        assert action.name == "Wait"
        assert action.weight == 100
        assert action.category == ActionCategory.NORMAL
        
    def test_validate_alive_unit(self, action, actor, game_map):
        """Test validation with alive unit."""
        validation = action.validate(actor, game_map)
        assert validation.is_valid
        
    def test_validate_dead_unit(self, action, game_map):
        """Test validation with dead unit."""
        dead_actor = MockUnit(is_alive=False)
        validation = action.validate(dead_actor, game_map)
        assert not validation.is_valid
        assert "Unit is not alive" in validation.reason
        
    def test_execute_success(self, action, actor, game_map):
        """Test successful execution."""
        result = action.execute(actor, game_map)
        assert result == ActionResult.SUCCESS


class TestPowerAttack:
    """Test PowerAttack action."""
    
    @pytest.fixture
    def action(self):
        return PowerAttack()
        
    @pytest.fixture
    def actor(self):
        return MockUnit(position=Vector2(5, 5))
        
    @pytest.fixture
    def target(self):
        return Vector2(5, 6)
        
    @pytest.fixture
    def game_map(self):
        return MockGameMap()
    
    def test_power_attack_creation(self, action):
        """Test PowerAttack initialization."""
        assert action.name == "Power Attack"
        assert action.weight == 180
        assert action.category == ActionCategory.HEAVY
        
    def test_execute_success_with_events(self, action, actor, target, game_map):
        """Test successful execution with event system."""
        event_emitter = Mock()
        
        result = action.execute(actor, game_map, target, event_emitter)
        
        assert result == ActionResult.SUCCESS
        event_emitter.assert_called_once()
        
        # Verify event details
        call_args = event_emitter.call_args[0]
        attack_event = call_args[0]
        assert attack_event.damage_multiplier == 1.5  # 150% damage


class TestChargeAttack:
    """Test ChargeAttack action."""
    
    @pytest.fixture
    def action(self):
        return ChargeAttack()
        
    @pytest.fixture
    def actor(self):
        return MockUnit(position=Vector2(5, 5))
        
    @pytest.fixture
    def game_map(self):
        return MockGameMap()
    
    def test_charge_attack_creation(self, action):
        """Test ChargeAttack initialization."""
        assert action.name == "Charge"
        assert action.weight == 170
        assert action.category == ActionCategory.HEAVY
        assert action.max_range == 4
        
    def test_validate_good_range(self, action, actor, game_map):
        """Test validation with good charge range."""
        target = MockUnit(position=Vector2(5, 8))  # 3 tiles away
        validation = action.validate(actor, game_map, target)
        assert validation.is_valid
        
    def test_validate_too_close(self, action, actor, game_map):
        """Test validation with target too close."""
        target = MockUnit(position=Vector2(5, 6))  # 1 tile away
        validation = action.validate(actor, game_map, target)
        assert not validation.is_valid
        assert "Invalid charge range" in validation.reason
        
    def test_validate_too_far(self, action, actor, game_map):
        """Test validation with target too far."""
        target = MockUnit(position=Vector2(5, 10))  # 5 tiles away
        validation = action.validate(actor, game_map, target)
        assert not validation.is_valid
        assert "Invalid charge range" in validation.reason


class TestOverwatchAction:
    """Test OverwatchAction."""
    
    @pytest.fixture
    def action(self):
        return OverwatchAction()
        
    @pytest.fixture
    def actor(self):
        return MockUnit()
        
    @pytest.fixture
    def game_map(self):
        return MockGameMap()
    
    def test_overwatch_creation(self, action):
        """Test OverwatchAction initialization."""
        assert action.name == "Overwatch"
        assert action.weight == 130
        assert action.category == ActionCategory.PREPARED
        assert action.max_range == 3
        
    def test_validate_always_valid(self, action, actor, game_map):
        """Test that overwatch is always valid."""
        validation = action.validate(actor, game_map)
        assert validation.is_valid
        
    def test_execute_success(self, action, actor, game_map):
        """Test successful execution."""
        result = action.execute(actor, game_map)
        assert result == ActionResult.SUCCESS
        
    def test_can_interrupt_movement(self, action):
        """Test interrupt capability for movement."""
        assert action.can_interrupt("enemy_movement_in_range")
        assert not action.can_interrupt("other_condition")


class TestShieldWall:
    """Test ShieldWall action."""
    
    @pytest.fixture
    def action(self):
        return ShieldWall()
        
    @pytest.fixture
    def actor(self):
        return MockUnit()
        
    @pytest.fixture
    def game_map(self):
        return MockGameMap()
    
    def test_shield_wall_creation(self, action):
        """Test ShieldWall initialization."""
        assert action.name == "Shield Wall"
        assert action.weight == 125
        assert action.category == ActionCategory.PREPARED
        
    def test_can_interrupt_attack(self, action):
        """Test interrupt capability for attacks."""
        assert action.can_interrupt("incoming_attack")
        assert not action.can_interrupt("other_condition")


class TestActionFactories:
    """Test action factory functions."""
    
    def test_get_available_actions_knight(self):
        """Test available actions for knight unit."""
        knight_unit = MockUnit()
        knight_unit.unit_class.name = 'KNIGHT'
        
        actions = get_available_actions(knight_unit)  # type: ignore[arg-type]
        action_names = [action.name for action in actions]
        
        # Should have basic actions
        assert "Quick Strike" in action_names
        assert "Quick Move" in action_names
        assert "Attack" in action_names
        assert "Move" in action_names
        
        # Should have warrior-specific actions
        assert "Power Attack" in action_names
        assert "Charge" in action_names
        assert "Shield Wall" in action_names
        
    def test_get_available_actions_archer(self):
        """Test available actions for archer unit."""
        archer_unit = MockUnit()
        archer_unit.unit_class.name = 'ARCHER'
        
        actions = get_available_actions(archer_unit)  # type: ignore[arg-type]
        action_names = [action.name for action in actions]
        
        # Should have basic actions
        assert "Quick Strike" in action_names
        assert "Move" in action_names
        
        # Should have ranged-specific actions
        assert "Overwatch" in action_names
        
        # Should not have warrior-specific actions
        assert "Power Attack" not in action_names
        assert "Charge" not in action_names
        
    def test_create_action_by_name_success(self):
        """Test creating action by name successfully."""
        action = create_action_by_name("Quick Strike")
        assert action is not None
        assert isinstance(action, QuickStrike)
        assert action.name == "Quick Strike"
        
    def test_create_action_by_name_failure(self):
        """Test creating action by unknown name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown action name: Unknown Action"):
            create_action_by_name("Unknown Action")
        
    def test_create_action_by_name_all_actions(self):
        """Test creating all available actions by name."""
        action_names = [
            "Quick Strike", "Quick Move", "Attack", "Move", "Wait",
            "Power Attack", "Charge", "Overwatch", "Shield Wall"
        ]
        
        for name in action_names:
            action = create_action_by_name(name)
            assert action is not None
            assert action.name == name


class TestActionIntegration:
    """Test action integration and edge cases."""
    
    def test_action_weight_categories(self):
        """Test that actions have appropriate weights for their categories."""
        quick_actions = [QuickStrike(), QuickMove()]
        normal_actions = [StandardAttack(), StandardMove(), Wait()]
        heavy_actions = [PowerAttack(), ChargeAttack()]
        prepared_actions = [OverwatchAction(), ShieldWall()]
        
        # Quick actions should be 50-80 weight
        for action in quick_actions:
            assert 50 <= action.weight <= 80
            assert action.category == ActionCategory.QUICK
            
        # Normal actions should be around 100 weight
        for action in normal_actions:
            assert action.weight == 100
            assert action.category == ActionCategory.NORMAL
            
        # Heavy actions should be 150+ weight
        for action in heavy_actions:
            assert action.weight >= 150
            assert action.category == ActionCategory.HEAVY
            
        # Prepared actions should be 120-140 weight
        for action in prepared_actions:
            assert 120 <= action.weight <= 140
            assert action.category == ActionCategory.PREPARED
            
    def test_action_range_consistency(self):
        """Test that action ranges are consistent with their types."""
        # Melee actions should have range 1
        melee_actions = [QuickStrike(), StandardAttack(), PowerAttack()]
        for action in melee_actions:
            assert action.max_range == 1
            
        # Movement actions should have higher range
        movement_actions = [QuickMove(), StandardMove()]
        for action in movement_actions:
            assert action.max_range >= 2
            
    def test_attack_actions_require_line_of_sight(self):
        """Test that attack actions require line of sight."""
        attack_actions = [QuickStrike(), StandardAttack(), PowerAttack(), ChargeAttack()]
        for action in attack_actions:
            assert action.requires_line_of_sight
            
    def test_movement_actions_no_line_of_sight(self):
        """Test that movement actions don't require line of sight."""
        movement_actions = [QuickMove(), StandardMove()]
        for action in movement_actions:
            assert not action.requires_line_of_sight