"""
Unit tests for game event system.

Tests the event classes and event handling functionality used
by the objective system.
"""
import pytest
from unittest.mock import Mock

from src.core.events import (
    EventType, TurnStarted, TurnEnded, UnitSpawned, 
    UnitMoved, UnitDefeated, UnitEnteredRegion, UnitExitedRegion,
    ObjectiveContext
)
from src.core.game_enums import Team


class TestEventType:
    """Test the EventType enumeration."""
    
    def test_all_event_types_exist(self):
        """Test that all expected event types exist."""
        expected_types = [
            'TURN_STARTED', 'TURN_ENDED', 'UNIT_SPAWNED', 'UNIT_MOVED', 
            'UNIT_DEFEATED', 'UNIT_ENTERED_REGION', 'UNIT_EXITED_REGION'
        ]
        actual_types = [event_type.name for event_type in EventType]
        
        for expected in expected_types:
            assert expected in actual_types
    
    def test_event_type_values_unique(self):
        """Test that event type values are unique."""
        values = [event_type.value for event_type in EventType]
        assert len(values) == len(set(values))


class TestTurnStarted:
    """Test the TurnStarted event."""
    
    def test_initialization(self):
        """Test TurnStarted event initialization."""
        event = TurnStarted(turn=1, team=Team.PLAYER)
        
        assert event.turn == 1
        assert event.team == Team.PLAYER
        assert event.event_type == EventType.TURN_STARTED
    
    def test_frozen_dataclass(self):
        """Test that TurnStarted is frozen (immutable)."""
        event = TurnStarted(turn=1, team=Team.PLAYER)
        
        with pytest.raises((AttributeError, Exception)):  # Should be frozen/immutable
            event.turn = 2  # type: ignore[misc] # Testing frozen dataclass immutability
    
    @pytest.mark.parametrize("team", [Team.PLAYER, Team.ENEMY, Team.ALLY, Team.NEUTRAL])
    def test_various_teams(self, team: Team):
        """Test TurnStarted with various team values."""
        event = TurnStarted(turn=5, team=team)
        assert event.team == team
        assert event.turn == 5


class TestTurnEnded:
    """Test the TurnEnded event."""
    
    def test_initialization(self):
        """Test TurnEnded event initialization."""
        event = TurnEnded(turn=2, team=Team.ENEMY)
        
        assert event.turn == 2
        assert event.team == Team.ENEMY
        assert event.event_type == EventType.TURN_ENDED
    
    def test_frozen_dataclass(self):
        """Test that TurnEnded is frozen (immutable)."""
        event = TurnEnded(turn=2, team=Team.ENEMY)
        
        with pytest.raises((AttributeError, Exception)):  # Should be frozen/immutable
            event.team = Team.PLAYER  # type: ignore[misc] # Testing frozen dataclass immutability


class TestUnitSpawned:
    """Test the UnitSpawned event."""
    
    def test_initialization(self):
        """Test UnitSpawned event initialization."""
        event = UnitSpawned(
            turn=1,
            unit_name="Test Knight",
            team=Team.PLAYER,
            position=(2, 3)
        )
        
        assert event.turn == 1
        assert event.unit_name == "Test Knight"
        assert event.team == Team.PLAYER
        assert event.position == (2, 3)
        assert event.event_type == EventType.UNIT_SPAWNED
    
    def test_string_representation(self):
        """Test UnitSpawned string representation."""
        event = UnitSpawned(
            turn=1,
            unit_name="Knight",
            team=Team.PLAYER,
            position=(1, 1)
        )
        
        str_repr = str(event)
        assert "Knight" in str_repr or "UnitSpawned" in str_repr
    
    @pytest.mark.parametrize("position", [(0, 0), (5, 10), (20, 15)])
    def test_various_positions(self, position):
        """Test UnitSpawned with various position values."""
        event = UnitSpawned(
            turn=1,
            unit_name="Test Unit",
            team=Team.PLAYER,
            position=position
        )
        assert event.position == position


class TestUnitMoved:
    """Test the UnitMoved event."""
    
    def test_initialization(self):
        """Test UnitMoved event initialization."""
        event = UnitMoved(
            turn=3,
            unit_name="Moving Knight",
            team=Team.PLAYER,
            from_position=(1, 1),
            to_position=(2, 2)
        )
        
        assert event.turn == 3
        assert event.unit_name == "Moving Knight"
        assert event.team == Team.PLAYER
        assert event.from_position == (1, 1)
        assert event.to_position == (2, 2)
        assert event.event_type == EventType.UNIT_MOVED
    
    def test_movement_tracking(self):
        """Test tracking unit movement."""
        event = UnitMoved(
            turn=1,
            unit_name="Scout",
            team=Team.PLAYER,
            from_position=(0, 0),
            to_position=(3, 4)
        )
        
        # Calculate Manhattan distance moved
        from_y, from_x = event.from_position
        to_y, to_x = event.to_position
        distance = abs(to_y - from_y) + abs(to_x - from_x)
        
        assert distance == 7  # |3-0| + |4-0|


class TestUnitDefeated:
    """Test the UnitDefeated event."""
    
    def test_initialization(self):
        """Test UnitDefeated event initialization."""
        event = UnitDefeated(
            turn=5,
            unit_name="Fallen Warrior",
            team=Team.ENEMY,
            position=(3, 3)
        )
        
        assert event.turn == 5
        assert event.unit_name == "Fallen Warrior"
        assert event.team == Team.ENEMY
        assert event.position == (3, 3)
        assert event.event_type == EventType.UNIT_DEFEATED
    
    def test_defeat_tracking(self):
        """Test tracking unit defeats."""
        enemy_defeat = UnitDefeated(
            turn=10,
            unit_name="Enemy Archer",
            team=Team.ENEMY,
            position=(5, 5)
        )
        
        player_defeat = UnitDefeated(
            turn=15,
            unit_name="Player Knight",
            team=Team.PLAYER,
            position=(2, 2)
        )
        
        assert enemy_defeat.team == Team.ENEMY
        assert player_defeat.team == Team.PLAYER
        assert enemy_defeat.turn < player_defeat.turn


class TestUnitEnteredRegion:
    """Test the UnitEnteredRegion event."""
    
    def test_initialization(self):
        """Test UnitEnteredRegion event initialization."""
        event = UnitEnteredRegion(
            turn=1,
            unit_name="Scout",
            team=Team.PLAYER,
            region_name="CaptureZone",  # Correct parameter name
            position=(1, 1)
        )
        
        assert event.turn == 1
        assert event.unit_name == "Scout"
        assert event.team == Team.PLAYER
        assert event.region_name == "CaptureZone"
        assert event.position == (1, 1)
        assert event.event_type == EventType.UNIT_ENTERED_REGION
    
    def test_string_representation(self):
        """Test UnitEnteredRegion string representation."""
        event = UnitEnteredRegion(
            turn=1,
            unit_name="Knight",
            team=Team.PLAYER,
            region_name="DefenseArea",
            position=(2, 2)
        )
        
        str_repr = str(event)
        assert "Knight" in str_repr or "UnitEnteredRegion" in str_repr
    
    @pytest.mark.parametrize("region_name", [
        "CaptureZone", "DefenseArea", "SpawnPoint", "ExitZone", "TriggerArea"
    ])
    def test_various_regions(self, region_name: str):
        """Test UnitEnteredRegion with various region names."""
        event = UnitEnteredRegion(
            turn=1,
            unit_name="Scout",
            team=Team.PLAYER,
            region_name=region_name,  # Correct parameter name
            position=(1, 1)
        )
        assert event.region_name == region_name


class TestUnitExitedRegion:
    """Test the UnitExitedRegion event."""
    
    def test_initialization(self):
        """Test UnitExitedRegion event initialization."""
        event = UnitExitedRegion(
            turn=2,
            unit_name="Leaving Unit",
            team=Team.ALLY,
            region_name="SafeZone",
            position=(4, 4)
        )
        
        assert event.turn == 2
        assert event.unit_name == "Leaving Unit"
        assert event.team == Team.ALLY
        assert event.region_name == "SafeZone"
        assert event.position == (4, 4)
        assert event.event_type == EventType.UNIT_EXITED_REGION


class TestObjectiveContext:
    """Test the ObjectiveContext class."""
    
    def test_initialization(self):
        """Test ObjectiveContext initialization."""
        event = UnitSpawned(turn=1, unit_name="Test", team=Team.PLAYER, position=(0, 0))
        mock_view = Mock()
        
        context = ObjectiveContext(event=event, view=mock_view)
        
        assert context.event == event
        assert context.view == mock_view
        assert context.meta is None
    
    def test_initialization_with_meta(self):
        """Test ObjectiveContext initialization with metadata."""
        event = TurnStarted(turn=1, team=Team.PLAYER)
        mock_view = Mock()
        meta_data = {"scenario_id": "tutorial", "debug": True}
        
        context = ObjectiveContext(event=event, view=mock_view, meta=meta_data)
        
        assert context.event == event
        assert context.view == mock_view
        assert context.meta == meta_data
    
    def test_context_usage_pattern(self):
        """Test typical ObjectiveContext usage pattern."""
        # Create a move event
        event = UnitMoved(
            turn=5,
            unit_name="Player Knight",
            team=Team.PLAYER,
            from_position=(1, 1),
            to_position=(2, 2)
        )
        
        # Mock view with some query methods
        mock_view = Mock()
        mock_view.get_unit_at_position.return_value = Mock(name="Player Knight")
        mock_view.is_position_in_region.return_value = True
        
        context = ObjectiveContext(event=event, view=mock_view)
        
        # Simulate objective checking
        event_cast = context.event  # Type: ignore - we know it's UnitMoved
        assert event_cast.team == Team.PLAYER  # type: ignore
        assert event_cast.unit_name == "Player Knight"  # type: ignore
        
        # Simulate view queries (mock methods)
        context.view.get_unit_at_position(event.to_position)  # type: ignore
        context.view.is_position_in_region(event.to_position, "capture_zone")  # type: ignore
        
        # Verify mock calls
        mock_view.get_unit_at_position.assert_called_with((2, 2))
        mock_view.is_position_in_region.assert_called_with((2, 2), "capture_zone")


class TestEventIntegration:
    """Test event system integration scenarios."""
    
    def test_event_sequence_tracking(self):
        """Test tracking a sequence of related events."""
        events = [
            TurnStarted(turn=1, team=Team.PLAYER),
            UnitSpawned(turn=1, unit_name="Knight", team=Team.PLAYER, position=(0, 0)),
            UnitMoved(turn=1, unit_name="Knight", team=Team.PLAYER, from_position=(0, 0), to_position=(1, 1)),
            UnitEnteredRegion(turn=1, unit_name="Knight", team=Team.PLAYER, region_name="Objective", position=(1, 1)),
            TurnEnded(turn=1, team=Team.PLAYER)
        ]
        
        # Verify sequence properties
        assert all(event.turn == 1 for event in events)
        assert all(hasattr(event, 'event_type') for event in events)
        
        # Verify event types are different
        event_types = [event.event_type for event in events]
        assert len(set(event_types)) == len(events)  # All unique
    
    def test_combat_event_sequence(self):
        """Test a combat-related event sequence."""
        attacker_move = UnitMoved(
            turn=3,
            unit_name="Player Knight",
            team=Team.PLAYER,
            from_position=(0, 0),
            to_position=(1, 1)
        )
        
        defender_defeat = UnitDefeated(
            turn=3,
            unit_name="Enemy Archer",
            team=Team.ENEMY,
            position=(2, 2)
        )
        
        # Both events should be on same turn
        assert attacker_move.turn == defender_defeat.turn
        
        # Different teams involved
        assert attacker_move.team != defender_defeat.team
    
    def test_region_enter_exit_sequence(self):
        """Test unit entering and exiting regions."""
        enter_event = UnitEnteredRegion(
            turn=5,
            unit_name="Scout",
            team=Team.PLAYER,
            region_name="PatrolArea",
            position=(3, 3)
        )
        
        exit_event = UnitExitedRegion(
            turn=7,
            unit_name="Scout",
            team=Team.PLAYER,
            region_name="PatrolArea",
            position=(4, 4)
        )
        
        # Same unit and region, different positions and turns
        assert enter_event.unit_name == exit_event.unit_name
        assert enter_event.team == exit_event.team
        assert enter_event.region_name == exit_event.region_name
        assert enter_event.position != exit_event.position
        assert enter_event.turn < exit_event.turn


class TestEventValidation:
    """Test event validation and edge cases."""
    
    def test_event_immutability(self):
        """Test that all events are properly frozen."""
        events = [
            TurnStarted(turn=1, team=Team.PLAYER),
            UnitSpawned(turn=1, unit_name="Test", team=Team.PLAYER, position=(0, 0)),
            UnitMoved(turn=1, unit_name="Test", team=Team.PLAYER, from_position=(0, 0), to_position=(1, 1)),
            UnitDefeated(turn=1, unit_name="Test", team=Team.PLAYER, position=(1, 1)),
            UnitEnteredRegion(turn=1, unit_name="Test", team=Team.PLAYER, region_name="Area", position=(1, 1)),
            UnitExitedRegion(turn=1, unit_name="Test", team=Team.PLAYER, region_name="Area", position=(1, 1))
        ]
        
        for event in events:
            # All events should have turn attribute that can't be changed
            with pytest.raises((AttributeError, Exception)):  # Should be frozen/immutable
                event.turn = 999  # Testing frozen dataclass immutability
    
    def test_event_type_consistency(self):
        """Test that event_type is set correctly for all events."""
        test_cases = [
            (TurnStarted(turn=1, team=Team.PLAYER), EventType.TURN_STARTED),
            (TurnEnded(turn=1, team=Team.PLAYER), EventType.TURN_ENDED),
            (UnitSpawned(turn=1, unit_name="Test", team=Team.PLAYER, position=(0, 0)), EventType.UNIT_SPAWNED),
            (UnitMoved(turn=1, unit_name="Test", team=Team.PLAYER, from_position=(0, 0), to_position=(1, 1)), EventType.UNIT_MOVED),
            (UnitDefeated(turn=1, unit_name="Test", team=Team.PLAYER, position=(1, 1)), EventType.UNIT_DEFEATED),
            (UnitEnteredRegion(turn=1, unit_name="Test", team=Team.PLAYER, region_name="Area", position=(1, 1)), EventType.UNIT_ENTERED_REGION),
            (UnitExitedRegion(turn=1, unit_name="Test", team=Team.PLAYER, region_name="Area", position=(1, 1)), EventType.UNIT_EXITED_REGION)
        ]
        
        for event, expected_type in test_cases:
            assert event.event_type == expected_type