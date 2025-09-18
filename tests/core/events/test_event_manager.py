"""
Unit tests for the Event Manager system.

Tests the event-driven communication system that enables decoupled
manager interactions through the publisher-subscriber pattern.
"""

import time
from unittest.mock import Mock
from src.core.events.event_manager import EventPriority, QueuedEvent
from src.core.events.events import GameEvent, EventType, TurnStarted
from src.core.data.game_enums import Team


class MockEvent(GameEvent):
    """Mock event for testing."""
    event_type = EventType.TURN_STARTED
    
    def __init__(self, turn: int, data: str = "test"):
        super().__init__(turn=turn)
        self.data = data


class TestQueuedEvent:
    """Test QueuedEvent functionality."""

    def test_queued_event_creation(self):
        """Test basic queued event creation."""
        event = MockEvent(turn=1)
        queued = QueuedEvent(event=event, priority=EventPriority.HIGH, source="test")
        
        assert queued.event == event
        assert queued.priority == EventPriority.HIGH
        assert queued.source == "test"

    def test_queued_event_ordering_by_priority(self):
        """Test that events are ordered by priority."""
        high_event = QueuedEvent(MockEvent(1), EventPriority.HIGH)
        normal_event = QueuedEvent(MockEvent(1), EventPriority.NORMAL)
        critical_event = QueuedEvent(MockEvent(1), EventPriority.CRITICAL)
        low_event = QueuedEvent(MockEvent(1), EventPriority.LOW)
        
        # From enum: LOW=1, NORMAL=2, HIGH=3, CRITICAL=4
        # Lower enum value = higher priority (according to code comment)
        assert low_event < normal_event      # 1 < 2 = True (higher priority)
        assert normal_event < high_event     # 2 < 3 = True  
        assert high_event < critical_event   # 3 < 4 = True (lower priority)

    def test_queued_event_ordering_by_timestamp(self):
        """Test that events with same priority are ordered by timestamp."""
        
        event1 = QueuedEvent(MockEvent(1), EventPriority.NORMAL)
        time.sleep(0.001)  # Small delay to ensure different timestamps
        event2 = QueuedEvent(MockEvent(1), EventPriority.NORMAL)
        
        assert event1 < event2


class TestEventManager:
    """Test EventManager functionality."""

    def test_event_manager_creation(self, event_manager):
        """Test event manager initialization."""
        assert not event_manager.enable_debug_logging
        assert event_manager.get_statistics()['events_published'] == 0
        assert event_manager.get_statistics()['events_processed'] == 0

    def test_subscribe_to_event_type(self, event_manager):
        """Test subscribing to specific event types."""
        subscriber = Mock()
        
        event_manager.subscribe(EventType.TURN_STARTED, subscriber)
        
        # Check that subscriber was registered
        stats = event_manager.get_statistics()
        assert stats['subscribers_count'] == 1

    def test_subscribe_to_all_events(self, event_manager):
        """Test subscribing to all events (universal subscriber)."""
        subscriber = Mock()
        
        event_manager.subscribe_all(subscriber)
        
        # Check that universal subscriber was registered
        stats = event_manager.get_statistics()
        assert stats['universal_subscribers_count'] == 1

    def test_publish_event(self, event_manager):
        """Test publishing events to the queue."""
        event = MockEvent(turn=1)
        
        event_manager.publish(event, priority=EventPriority.HIGH, source="test")
        
        stats = event_manager.get_statistics()
        assert stats['events_published'] == 1
        assert stats['events_queued'] == 1
        assert event_manager.has_queued_events()

    def test_publish_immediate(self, event_manager):
        """Test immediate event publishing and processing."""
        subscriber = Mock()
        event_manager.subscribe(EventType.TURN_STARTED, subscriber)
        
        event = MockEvent(turn=1)
        event_manager.publish_immediate(event, source="test")
        
        # Event should be processed immediately
        subscriber.assert_called_once_with(event)

    def test_process_events(self, event_manager):
        """Test processing queued events."""
        subscriber = Mock()
        event_manager.subscribe(EventType.TURN_STARTED, subscriber)
        
        # Publish multiple events
        event1 = MockEvent(turn=1, data="first")
        event2 = MockEvent(turn=2, data="second")
        
        event_manager.publish(event1)
        event_manager.publish(event2)
        
        # Process all events
        processed_count = event_manager.process_events()
        
        assert processed_count == 2
        assert subscriber.call_count == 2
        assert not event_manager.has_queued_events()

    def test_process_events_with_limit(self, event_manager):
        """Test processing limited number of events."""
        subscriber = Mock()
        event_manager.subscribe(EventType.TURN_STARTED, subscriber)
        
        # Publish multiple events
        for i in range(5):
            event_manager.publish(MockEvent(turn=i))
        
        # Process only 2 events
        processed_count = event_manager.process_events(max_events=2)
        
        assert processed_count == 2
        assert subscriber.call_count == 2
        assert event_manager.has_queued_events()  # Should have remaining events

    def test_event_priority_processing(self, event_manager):
        """Test that events are processed in priority order."""
        results = []
        
        def capture_event(event):
            results.append(event.data)
        
        event_manager.subscribe(EventType.TURN_STARTED, capture_event)
        
        # Publish events in reverse priority order
        event_manager.publish(MockEvent(1, "low"), EventPriority.LOW)
        event_manager.publish(MockEvent(1, "critical"), EventPriority.CRITICAL)
        event_manager.publish(MockEvent(1, "normal"), EventPriority.NORMAL)
        event_manager.publish(MockEvent(1, "high"), EventPriority.HIGH)
        
        event_manager.process_events()
        
        # Lower enum value = higher priority: LOW=1, NORMAL=2, HIGH=3, CRITICAL=4
        # So processing order should be: low, normal, high, critical
        assert results == ["low", "normal", "high", "critical"]

    def test_universal_subscriber_receives_all_events(self, event_manager):
        """Test that universal subscribers receive all event types."""
        universal_subscriber = Mock()
        specific_subscriber = Mock()
        
        event_manager.subscribe_all(universal_subscriber)
        event_manager.subscribe(EventType.TURN_STARTED, specific_subscriber)
        
        # Publish different event types
        turn_event = TurnStarted(turn=1, team=Team.PLAYER)
        mock_event = MockEvent(turn=1)
        
        event_manager.publish_immediate(turn_event)
        event_manager.publish_immediate(mock_event)
        
        # Universal subscriber should receive both
        assert universal_subscriber.call_count == 2
        # Specific subscriber should only receive the matching event
        assert specific_subscriber.call_count == 2  # Both are TURN_STARTED events

    def test_unsubscribe(self, event_manager):
        """Test unsubscribing from events."""
        subscriber = Mock()
        
        event_manager.subscribe(EventType.TURN_STARTED, subscriber)
        success = event_manager.unsubscribe(EventType.TURN_STARTED, subscriber)
        
        assert success
        
        # Publishing event should not call subscriber
        event_manager.publish_immediate(MockEvent(turn=1))
        subscriber.assert_not_called()

    def test_unsubscribe_all(self, event_manager):
        """Test unsubscribing from all events."""
        subscriber = Mock()
        
        event_manager.subscribe_all(subscriber)
        success = event_manager.unsubscribe_all(subscriber)
        
        assert success
        
        # Publishing event should not call subscriber
        event_manager.publish_immediate(MockEvent(turn=1))
        subscriber.assert_not_called()

    def test_subscriber_exception_handling(self, event_manager):
        """Test that subscriber exceptions don't break event processing."""
        failing_subscriber = Mock(side_effect=Exception("Test error"))
        working_subscriber = Mock()
        
        event_manager.subscribe(EventType.TURN_STARTED, failing_subscriber)
        event_manager.subscribe(EventType.TURN_STARTED, working_subscriber)
        
        # Process event - should not raise exception
        event_manager.publish_immediate(MockEvent(turn=1))
        
        # Working subscriber should still be called
        working_subscriber.assert_called_once()

    def test_clear_queue(self, event_manager):
        """Test clearing the event queue."""
        event_manager.publish(MockEvent(turn=1))
        event_manager.publish(MockEvent(turn=2))
        
        cleared_count = event_manager.clear_queue()
        
        assert cleared_count == 2
        assert not event_manager.has_queued_events()

    def test_has_high_priority_events(self, event_manager):
        """Test checking for high priority events."""
        assert not event_manager.has_high_priority_events()
        
        event_manager.publish(MockEvent(turn=1), EventPriority.NORMAL)
        assert not event_manager.has_high_priority_events()
        
        event_manager.publish(MockEvent(turn=2), EventPriority.HIGH)
        assert event_manager.has_high_priority_events()

    def test_get_recent_events(self, event_manager):
        """Test getting recent event history."""
        # Process some events to build history
        for i in range(5):
            event_manager.publish_immediate(MockEvent(turn=i))
        
        recent = event_manager.get_recent_events(count=3)
        
        assert len(recent) == 3
        assert all('event_type' in event_info for event_info in recent)
        assert all('turn' in event_info for event_info in recent)

    def test_shutdown(self, event_manager):
        """Test event manager shutdown."""
        # Add some data
        subscriber = Mock()
        event_manager.subscribe(EventType.TURN_STARTED, subscriber)
        event_manager.publish(MockEvent(turn=1))
        
        event_manager.shutdown()
        
        # All data should be cleared
        stats = event_manager.get_statistics()
        assert stats['subscribers_count'] == 0
        assert stats['events_queued'] == 0