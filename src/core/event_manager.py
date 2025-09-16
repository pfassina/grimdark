"""
Event management system for decoupled manager communication.

This module provides a central event bus that allows managers to communicate
through events instead of direct dependencies, following the publisher-subscriber
pattern for clean separation of concerns.
"""

import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .events import GameEvent, EventType


class EventPriority(Enum):
    """Event processing priorities."""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class QueuedEvent:
    """An event in the processing queue with metadata."""
    event: "GameEvent"
    priority: EventPriority = EventPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None  # For debugging
    
    def __lt__(self, other: "QueuedEvent") -> bool:
        """Compare events for priority queue ordering."""
        # Higher priority events come first (lower enum value = higher priority)
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # If same priority, older events come first
        return self.timestamp < other.timestamp


EventSubscriber = Callable[["GameEvent"], None]


class EventManager:
    """Central event bus for managing game system communication."""
    
    def __init__(self, enable_debug_logging: bool = False):
        """Initialize the event manager.
        
        Args:
            enable_debug_logging: Whether to enable detailed event logging
        """
        self.enable_debug_logging = enable_debug_logging
        
        # Event subscribers by event type
        self._subscribers: dict["EventType", list[EventSubscriber]] = defaultdict(list)
        
        # Universal subscribers (receive all events)
        self._universal_subscribers: list[EventSubscriber] = []
        
        # Event processing queue
        self._event_queue: deque[QueuedEvent] = deque()
        
        # Statistics and debugging
        self._events_published = 0
        self._events_processed = 0
        self._event_history: deque[QueuedEvent] = deque(maxlen=1000)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Debug callback for logging
        self._debug_callback: Optional[Callable[[str], None]] = None
    
    def set_debug_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """Set a callback function for debug logging."""
        self._debug_callback = callback
    
    def _debug_log(self, message: str) -> None:
        """Log a debug message if debug logging is enabled."""
        if self.enable_debug_logging and self._debug_callback:
            self._debug_callback(f"[EVENT] {message}")
    
    def subscribe(
        self, 
        event_type: "EventType", 
        subscriber: EventSubscriber,
        subscriber_name: Optional[str] = None
    ) -> None:
        """Subscribe to events of a specific type.
        
        Args:
            event_type: The type of events to subscribe to
            subscriber: Callback function to handle events
            subscriber_name: Optional name for debugging
        """
        with self._lock:
            self._subscribers[event_type].append(subscriber)
            
            subscriber_display = subscriber_name or getattr(subscriber, '__name__', 'anonymous')
            self._debug_log(
                f"Subscribed {subscriber_display} to {event_type.name} events"
            )
    
    def subscribe_all(
        self, 
        subscriber: EventSubscriber,
        subscriber_name: Optional[str] = None
    ) -> None:
        """Subscribe to all events (universal subscriber).
        
        Args:
            subscriber: Callback function to handle events
            subscriber_name: Optional name for debugging
        """
        with self._lock:
            self._universal_subscribers.append(subscriber)
            
            subscriber_display = subscriber_name or getattr(subscriber, '__name__', 'anonymous')
            self._debug_log(f"Subscribed {subscriber_display} to ALL events")
    
    def unsubscribe(
        self, 
        event_type: "EventType", 
        subscriber: EventSubscriber
    ) -> bool:
        """Unsubscribe from events of a specific type.
        
        Args:
            event_type: The event type to unsubscribe from
            subscriber: The subscriber to remove
            
        Returns:
            True if subscriber was found and removed
        """
        with self._lock:
            try:
                self._subscribers[event_type].remove(subscriber)
                self._debug_log(f"Unsubscribed from {event_type.name} events")
                return True
            except ValueError:
                return False
    
    def unsubscribe_all(self, subscriber: EventSubscriber) -> bool:
        """Unsubscribe from all events (universal subscriber).
        
        Args:
            subscriber: The subscriber to remove
            
        Returns:
            True if subscriber was found and removed
        """
        with self._lock:
            try:
                self._universal_subscribers.remove(subscriber)
                self._debug_log("Unsubscribed from ALL events")
                return True
            except ValueError:
                return False
    
    def publish(
        self, 
        event: "GameEvent", 
        priority: EventPriority = EventPriority.NORMAL,
        source: Optional[str] = None
    ) -> None:
        """Publish an event for processing.
        
        Args:
            event: The event to publish
            priority: Processing priority for the event
            source: Optional source identifier for debugging
        """
        with self._lock:
            queued_event = QueuedEvent(
                event=event,
                priority=priority,
                source=source or "unknown"
            )
            
            self._event_queue.append(queued_event)
            self._events_published += 1
            
            self._debug_log(
                f"Published {event.__class__.__name__} (priority: {priority.name}, source: {queued_event.source})"
            )
    
    def publish_immediate(
        self, 
        event: "GameEvent",
        source: Optional[str] = None
    ) -> None:
        """Publish and immediately process an event.
        
        Args:
            event: The event to publish and process
            source: Optional source identifier for debugging
        """
        queued_event = QueuedEvent(
            event=event,
            priority=EventPriority.CRITICAL,
            source=source or "immediate"
        )
        
        self._process_event(queued_event)
    
    def process_events(self, max_events: Optional[int] = None) -> int:
        """Process queued events.
        
        Args:
            max_events: Maximum number of events to process (None for all)
            
        Returns:
            Number of events processed
        """
        processed_count = 0
        
        with self._lock:
            # Sort queue by priority and timestamp
            sorted_events = sorted(self._event_queue)
            self._event_queue.clear()
        
        # Process events in priority order
        for queued_event in sorted_events:
            if max_events is not None and processed_count >= max_events:
                # Put remaining events back in queue
                with self._lock:
                    self._event_queue.extendleft(reversed(sorted_events[processed_count:]))
                break
            
            self._process_event(queued_event)
            processed_count += 1
        
        return processed_count
    
    def _process_event(self, queued_event: QueuedEvent) -> None:
        """Process a single event by notifying all subscribers.
        
        Args:
            queued_event: The queued event to process
        """
        event = queued_event.event
        
        # Add to history for debugging
        with self._lock:
            self._event_history.append(queued_event)
            self._events_processed += 1
        
        self._debug_log(
            f"Processing {event.__class__.__name__} from {queued_event.source} "
            f"(turn: {event.turn})"
        )
        
        # Notify specific event type subscribers
        subscribers = self._subscribers.get(event.event_type, [])
        
        for subscriber in subscribers[:]:  # Use slice to avoid modification during iteration
            try:
                subscriber(event)
            except Exception as e:
                self._debug_log(
                    f"Error in subscriber {getattr(subscriber, '__name__', 'anonymous')}: {e}"
                )
        
        # Notify universal subscribers
        for subscriber in self._universal_subscribers[:]:
            try:
                subscriber(event)
            except Exception as e:
                self._debug_log(
                    f"Error in universal subscriber {getattr(subscriber, '__name__', 'anonymous')}: {e}"
                )
    
    def clear_queue(self) -> int:
        """Clear all queued events.
        
        Returns:
            Number of events that were cleared
        """
        with self._lock:
            count = len(self._event_queue)
            self._event_queue.clear()
            self._debug_log(f"Cleared {count} queued events")
            return count
    
    def get_statistics(self) -> dict[str, Any]:
        """Get event processing statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                'events_published': self._events_published,
                'events_processed': self._events_processed,
                'events_queued': len(self._event_queue),
                'subscribers_count': sum(len(subs) for subs in self._subscribers.values()),
                'universal_subscribers_count': len(self._universal_subscribers),
                'event_history_size': len(self._event_history)
            }
    
    def get_recent_events(self, count: int = 10) -> list[dict[str, Any]]:
        """Get recent events for debugging.
        
        Args:
            count: Number of recent events to return
            
        Returns:
            List of event information dictionaries
        """
        with self._lock:
            recent = list(self._event_history)[-count:]
            
            return [
                {
                    'event_type': queued.event.__class__.__name__,
                    'turn': queued.event.turn,
                    'priority': queued.priority.name,
                    'source': queued.source,
                    'timestamp': queued.timestamp.isoformat()
                }
                for queued in recent
            ]
    
    def has_queued_events(self) -> bool:
        """Check if there are events waiting to be processed."""
        with self._lock:
            return len(self._event_queue) > 0
    
    def has_high_priority_events(self) -> bool:
        """Check if there are high or critical priority events waiting."""
        with self._lock:
            return any(
                event.priority in (EventPriority.HIGH, EventPriority.CRITICAL)
                for event in self._event_queue
            )
    
    def shutdown(self) -> None:
        """Shutdown the event manager and clear all data."""
        with self._lock:
            self._subscribers.clear()
            self._universal_subscribers.clear()
            self._event_queue.clear()
            self._event_history.clear()
            self._debug_log("Event manager shutdown complete")