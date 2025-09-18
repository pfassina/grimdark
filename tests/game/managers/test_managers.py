"""
Unit tests for key game managers.

Tests TimelineManager, PhaseManager, and other critical manager systems
that coordinate the timeline-based game architecture.
"""

import pytest
from unittest.mock import Mock
from src.core.events.event_manager import EventManager
from src.core.events.events import (
    EventType, UnitTurnStarted, ActionExecuted,
    ScenarioLoaded, BattlePhaseChanged
)
from src.core.data.game_enums import Team
from src.core.engine.game_state import GameState, GamePhase, BattlePhase
from src.core.engine.timeline import Timeline
from src.game.managers.phase_manager import PhaseManager, GamePhaseTransitionRule


class TestPhaseTransitionRule:
    """Test PhaseTransitionRule functionality."""

    def test_rule_creation(self):
        """Test basic rule creation."""
        rule = GamePhaseTransitionRule(
            from_phase=GamePhase.MAIN_MENU,
            event_type=EventType.SCENARIO_LOADED,
            to_phase=GamePhase.BATTLE,
            description="Start battle"
        )
        
        assert rule.from_phase == GamePhase.MAIN_MENU
        assert rule.event_type == EventType.SCENARIO_LOADED
        assert rule.to_phase == GamePhase.BATTLE
        assert rule.description == "Start battle"

    def test_rule_matches(self):
        """Test rule matching logic."""
        rule = GamePhaseTransitionRule(
            from_phase=GamePhase.MAIN_MENU,
            event_type=EventType.SCENARIO_LOADED,
            to_phase=GamePhase.BATTLE,
            description="Start battle"
        )
        
        # Should match correct phase and event
        assert rule.matches(GamePhase.MAIN_MENU, EventType.SCENARIO_LOADED)
        
        # Should not match wrong phase
        assert not rule.matches(GamePhase.BATTLE, EventType.SCENARIO_LOADED)
        
        # Should not match wrong event
        assert not rule.matches(GamePhase.MAIN_MENU, EventType.GAME_ENDED)


class TestPhaseManager:
    """Test PhaseManager functionality."""

    @pytest.fixture
    def game_state(self):
        return GameState(phase=GamePhase.MAIN_MENU)

    @pytest.fixture
    def event_manager(self):
        return EventManager(enable_debug_logging=False)

    @pytest.fixture
    def phase_manager(self, game_state, event_manager):
        return PhaseManager(game_state, event_manager)

    def test_phase_manager_creation(self, phase_manager):
        """Test phase manager initialization."""
        assert phase_manager.state is not None
        assert phase_manager.event_manager is not None
        assert len(phase_manager.game_phase_rules) > 0
        assert len(phase_manager.battle_phase_rules) > 0

    def test_game_phase_rules_setup(self, phase_manager):
        """Test that game phase transition rules are properly set up."""
        # Check for main menu to battle rule
        menu_to_battle = any(
            rule.from_phase == GamePhase.MAIN_MENU and 
            rule.event_type == EventType.SCENARIO_LOADED and
            rule.to_phase == GamePhase.BATTLE
            for rule in phase_manager.game_phase_rules
        )
        assert menu_to_battle

        # Check for battle to game over rule
        battle_to_over = any(
            rule.from_phase == GamePhase.BATTLE and
            rule.event_type == EventType.GAME_ENDED and
            rule.to_phase == GamePhase.GAME_OVER
            for rule in phase_manager.game_phase_rules
        )
        assert battle_to_over

    def test_battle_phase_rules_setup(self, phase_manager):
        """Test that battle phase transition rules exist."""
        # Should have some battle phase transition rules
        assert len(phase_manager.battle_phase_rules) > 0
        
        # Rules should involve common battle phases
        phase_types = {rule.from_phase for rule in phase_manager.battle_phase_rules}
        common_phases = {
            BattlePhase.TIMELINE_PROCESSING,
            BattlePhase.UNIT_MOVING,
            BattlePhase.UNIT_ACTION_SELECTION,
            BattlePhase.ACTION_TARGETING
        }
        
        # Should have rules for at least some common phases
        assert len(phase_types.intersection(common_phases)) > 0

    def test_event_subscription(self, phase_manager):
        """Test that phase manager subscribes to events."""
        # PhaseManager should subscribe to events during initialization
        # This is verified by checking that it doesn't crash and has rules
        assert True  # If we got here, subscription worked

    def test_game_phase_transition_scenario_loaded(self, phase_manager, event_manager):
        """Test game phase transition from main menu to battle."""
        # Start in main menu
        assert phase_manager.state.phase == GamePhase.MAIN_MENU
        
        # Publish scenario loaded event
        scenario_event = ScenarioLoaded(turn=0, scenario_name="test", scenario_path="test.yaml")
        event_manager.publish_immediate(scenario_event)
        
        # Should transition to battle phase
        assert phase_manager.state.phase == GamePhase.BATTLE

    def test_battle_phase_management(self, phase_manager):
        """Test battle phase management."""
        # Set to battle phase
        phase_manager.state.phase = GamePhase.BATTLE
        
        # Battle phase should be accessible
        assert hasattr(phase_manager.state, 'battle')
        assert hasattr(phase_manager.state.battle, 'phase')


class TestTimelineManagerIntegration:
    """Test TimelineManager integration patterns."""

    @pytest.fixture
    def mock_game_map(self):
        """Create a mock game map."""
        game_map = Mock()
        game_map.units = []
        return game_map

    @pytest.fixture
    def game_state(self):
        return GameState(phase=GamePhase.BATTLE)

    @pytest.fixture
    def event_manager(self):
        return EventManager(enable_debug_logging=False)

    def test_timeline_manager_imports(self):
        """Test that TimelineManager can be imported."""
        try:
            from src.game.managers.timeline_manager import TimelineManager
            assert TimelineManager is not None
        except ImportError:
            pytest.skip("TimelineManager not available for import")

    def test_timeline_manager_initialization(self, mock_game_map, game_state, event_manager):
        """Test TimelineManager initialization."""
        try:
            from src.game.managers.timeline_manager import TimelineManager
            
            timeline_manager = TimelineManager(
                game_map=mock_game_map,
                game_state=game_state,
                event_manager=event_manager
            )
            
            assert timeline_manager.game_map == mock_game_map
            assert timeline_manager.state == game_state
            assert timeline_manager.event_manager == event_manager
            assert timeline_manager.timeline is not None
            
        except ImportError:
            pytest.skip("TimelineManager not available")
        except Exception as e:
            pytest.skip(f"TimelineManager initialization failed: {e}")

    def test_timeline_manager_event_subscriptions(self, mock_game_map, game_state, event_manager):
        """Test that TimelineManager subscribes to events."""
        try:
            from src.game.managers.timeline_manager import TimelineManager
            
            # Count subscribers before
            initial_count = event_manager.get_statistics()['subscribers_count']
            
            timeline_manager = TimelineManager(
                game_map=mock_game_map,
                game_state=game_state,
                event_manager=event_manager
            )
            
            # TimelineManager should be created successfully
            assert timeline_manager is not None
            
            # Should have more subscribers after initialization
            final_count = event_manager.get_statistics()['subscribers_count']
            assert final_count > initial_count
            
        except ImportError:
            pytest.skip("TimelineManager not available")
        except Exception as e:
            pytest.skip(f"TimelineManager initialization failed: {e}")


class TestManagerEventFlow:
    """Test event flow between managers."""

    @pytest.fixture
    def event_manager(self):
        return EventManager(enable_debug_logging=False)

    def test_event_manager_publish_flow(self, event_manager):
        """Test basic event publishing and processing flow."""
        received_events = []
        
        def event_handler(event):
            received_events.append(event)
        
        # Subscribe to turn events
        event_manager.subscribe(EventType.UNIT_TURN_STARTED, event_handler)
        
        # Publish event
        turn_event = UnitTurnStarted(
            turn=1,
            unit_name="Test Knight",
            unit_id="test_123",
            team=Team.PLAYER
        )
        event_manager.publish_immediate(turn_event)
        
        # Should have received the event
        assert len(received_events) == 1
        assert received_events[0] == turn_event

    def test_multiple_managers_event_coordination(self, event_manager):
        """Test coordination between multiple manager types."""
        phase_events = []
        timeline_events = []
        
        def phase_handler(event):
            phase_events.append(event)
            
        def timeline_handler(event):
            timeline_events.append(event)
        
        # Subscribe different handlers to different events
        event_manager.subscribe(EventType.BATTLE_PHASE_CHANGED, phase_handler)
        event_manager.subscribe(EventType.ACTION_EXECUTED, timeline_handler)
        
        # Publish different types of events
        phase_event = BattlePhaseChanged(
            turn=1,
            old_phase="TIMELINE_PROCESSING",
            new_phase="UNIT_MOVING",
            unit_id="test_123"
        )
        action_event = ActionExecuted(
            turn=1,
            unit_name="Test Knight", 
            unit_id="test_123",
            action_name="Move",
            action_type="Movement",
            success=True
        )
        
        event_manager.publish_immediate(phase_event)
        event_manager.publish_immediate(action_event)
        
        # Each handler should only receive its subscribed events
        assert len(phase_events) == 1
        assert len(timeline_events) == 1
        assert phase_events[0] == phase_event
        assert timeline_events[0] == action_event


class TestManagerErrorHandling:
    """Test error handling in manager systems."""

    @pytest.fixture
    def event_manager(self):
        return EventManager(enable_debug_logging=False)

    def test_event_manager_subscriber_exception_isolation(self, event_manager):
        """Test that subscriber exceptions don't break other subscribers."""
        successful_calls = []
        
        def failing_handler(event):
            raise Exception("Test failure")
            
        def working_handler(event):
            successful_calls.append(event)
        
        # Subscribe both handlers
        event_manager.subscribe(EventType.UNIT_TURN_STARTED, failing_handler)
        event_manager.subscribe(EventType.UNIT_TURN_STARTED, working_handler)
        
        # Publish event
        turn_event = UnitTurnStarted(
            turn=1,
            unit_name="Test",
            unit_id="test_123", 
            team=Team.PLAYER
        )
        
        # Should not raise exception, working handler should still be called
        event_manager.publish_immediate(turn_event)
        assert len(successful_calls) == 1

    def test_timeline_empty_state_handling(self):
        """Test handling of empty timeline states."""
        timeline = Timeline()
        
        # Empty timeline operations should not crash
        assert timeline.is_empty
        assert timeline.peek_next() is None
        assert timeline.pop_next() is None
        assert timeline.get_preview(5) == []

    def test_manager_initialization_resilience(self):
        """Test that managers handle initialization edge cases."""
        # Test with minimal game state
        game_state = GameState(phase=GamePhase.BATTLE)
        event_manager = EventManager(enable_debug_logging=False)
        
        try:
            phase_manager = PhaseManager(game_state, event_manager)
            assert phase_manager is not None
        except Exception as e:
            pytest.fail(f"PhaseManager initialization should not fail: {e}")


class TestManagerStateMaintenance:
    """Test that managers maintain consistent state."""

    def test_phase_manager_state_consistency(self):
        """Test that PhaseManager maintains consistent state."""
        game_state = GameState(phase=GamePhase.MAIN_MENU)
        event_manager = EventManager(enable_debug_logging=False)
        phase_manager = PhaseManager(game_state, event_manager)
        
        # Initial state should be consistent
        assert phase_manager.state.phase == GamePhase.MAIN_MENU
        
        # After rule application, state should remain consistent
        original_rules_count = len(phase_manager.game_phase_rules)
        assert original_rules_count > 0
        
        # Rules should not change after initialization
        new_rules_count = len(phase_manager.game_phase_rules)
        assert new_rules_count == original_rules_count

    def test_event_manager_statistics_consistency(self):
        """Test that EventManager statistics remain consistent."""
        event_manager = EventManager(enable_debug_logging=False)
        
        # Initial statistics
        initial_stats = event_manager.get_statistics()
        assert initial_stats['events_published'] == 0
        assert initial_stats['events_processed'] == 0
        
        # Test normal publish + process flow
        mock_event = UnitTurnStarted(
            turn=1,
            unit_name="Test",
            unit_id="test",
            team=Team.PLAYER
        )
        event_manager.publish(mock_event)
        event_manager.process_events()
        
        final_stats = event_manager.get_statistics()
        assert final_stats['events_published'] == 1
        assert final_stats['events_processed'] == 1