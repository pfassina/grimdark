"""Timeline management for fluid turn-based combat.

This module implements the core timeline system that replaces phase-based combat
with a fluid, action-weight driven turn order. Units and actions are scheduled
on a timeline queue based on their action weights and base speed.

Core Concepts:
- Timeline uses discrete ticks (integers) for deterministic scheduling
- Each unit has a base speed that affects when they act
- Actions have weights that determine how long until the unit's next turn
- Timeline queue processes entries in chronological order
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ...game.entities.unit import Unit
    from ..hidden_intent import IntentInfo


@dataclass
class TimelineEntry:
    """A scheduled event on the timeline.
    
    Each entry represents an entity (unit, hazard, etc.) that will act at a specific time.
    The timeline queue is ordered by execution_time, with earlier times processed first.
    """
    
    # When this entry should be processed (discrete ticks)
    execution_time: int
    
    # The entity that will act (unit, hazard, etc.)
    entity_id: str  # Unique identifier for the entity
    entity_type: str = "unit"  # "unit", "hazard", "event", etc.
    
    
    # Unique ID for stable sorting when times are equal
    sequence_id: int = 0
    
    # Optional scheduled action (for prepared actions/interrupts)
    scheduled_action: Optional[Any] = None
    
    # Action description for display
    action_description: str = ""
    
    # Hidden intent information (legacy - use intent_info instead)
    intent_visible: bool = True
    intent_description: str = ""
    
    # New hidden intent system
    intent_info: Optional["IntentInfo"] = None
    
    def __lt__(self, other: "TimelineEntry") -> bool:
        """Define ordering for heap queue.
        
        Primary: execution_time (earlier times first)
        Secondary: sequence_id (stable ordering for simultaneous events)
        """
        if self.execution_time != other.execution_time:
            return self.execution_time < other.execution_time
        return self.sequence_id < other.sequence_id
    
    def __eq__(self, other: object) -> bool:
        """Check equality based on execution_time and sequence_id."""
        if not isinstance(other, TimelineEntry):
            return NotImplemented
        return (self.execution_time == other.execution_time and 
                self.sequence_id == other.sequence_id)


class Timeline:
    """Manages the fluid turn order system.
    
    The Timeline uses a priority queue (min-heap) to maintain entries in 
    chronological order. Units are scheduled based on their speed and action
    weights, creating a fluid turn system where fast units with light actions
    can act multiple times before slow units with heavy actions.
    
    Key Features:
    - Discrete tick system for deterministic behavior
    - Action weight system affects turn scheduling
    - Support for simultaneous actions via sequence IDs
    - Hidden intent system for incomplete information
    - Efficient insertion and removal of timeline entries
    """
    
    def __init__(self):
        self._queue: list[TimelineEntry] = []
        self._current_time: int = 0
        self._sequence_counter: int = 0
        self._removed_entries: set[int] = set()  # Track removed sequence IDs
        
    @property
    def current_time(self) -> int:
        """Get the current timeline time in ticks."""
        return self._current_time
        
    @property
    def is_empty(self) -> bool:
        """Check if the timeline has any pending entries."""
        # Filter out removed entries
        return not any(entry.sequence_id not in self._removed_entries 
                      for entry in self._queue)
    
    def schedule_unit(self, 
                     unit: "Unit", 
                     action_weight: int, 
                     scheduled_action: Optional[Any] = None,
                     action_description: str = "") -> TimelineEntry:
        """Schedule a unit for their next turn.
        
        Args:
            unit: The unit to schedule
            action_weight: Weight of the action that determines next turn timing
            scheduled_action: Optional pre-planned action (for prepared actions)
            action_description: Description of the intended action
            
        Returns:
            The created timeline entry
        """
        # Calculate next turn time: base_speed + action_weight
        base_speed = unit.status.speed
        next_time = self._current_time + base_speed + action_weight
        
        # Create timeline entry
        entry = TimelineEntry(
            execution_time=next_time,
            entity_id=unit.unit_id,
            entity_type="unit",
            sequence_id=self._get_next_sequence_id(),
            scheduled_action=scheduled_action,
            action_description=action_description
        )
        
        # Add to priority queue
        heapq.heappush(self._queue, entry)
        
        return entry
    
    def add_entry(self, 
                  time: int,
                  entity_id: str,
                  entity_type: str = "event",
                  action_description: str = "",
                  scheduled_action: Optional[Any] = None) -> str:
        """Add a generic entry to the timeline.
        
        This method supports adding non-unit entities like hazards, events, etc.
        
        Args:
            time: Absolute time when this entry should execute
            entity_id: Unique identifier for the entity
            entity_type: Type of entity (hazard, event, etc.)
            action_description: Description of what will happen
            scheduled_action: Optional action data
            
        Returns:
            Entity ID for tracking/removal
        """
        entry = TimelineEntry(
            execution_time=time,
            entity_id=entity_id,
            entity_type=entity_type,
            sequence_id=self._get_next_sequence_id(),
            action_description=action_description,
            scheduled_action=scheduled_action,
            intent_visible=True,
            intent_description=action_description
        )
        
        heapq.heappush(self._queue, entry)
        return entity_id
    
    def remove_entry(self, entity_id: str) -> int:
        """Remove all timeline entries for an entity by its ID.
        
        Args:
            entity_id: The entity ID (unit UUID, hazard ID, etc.)
            
        Returns:
            Number of entries removed
        """
        removed_count = 0
        
        # Mark matching entries as removed (lazy deletion)
        for entry in self._queue:
            if (entry.entity_id == entity_id and 
                entry.sequence_id not in self._removed_entries):
                self._removed_entries.add(entry.sequence_id)
                removed_count += 1
        
        return removed_count
    
    def peek_next(self) -> Optional[TimelineEntry]:
        """Get the next timeline entry without removing it.
        
        Returns:
            The next timeline entry or None if queue is empty
        """
        while self._queue:
            entry = self._queue[0]
            if entry.sequence_id in self._removed_entries:
                heapq.heappop(self._queue)
                continue
            return entry
        return None
    
    def pop_next(self) -> Optional[TimelineEntry]:
        """Remove and return the next timeline entry.
        
        Updates current_time to the entry's execution_time.
        
        Returns:
            The next timeline entry or None if queue is empty
        """
        while self._queue:
            entry = heapq.heappop(self._queue)
            if entry.sequence_id in self._removed_entries:
                continue
                
            # Update current time to this entry's time
            self._current_time = entry.execution_time
            return entry
        
        return None
    
    def remove_unit_entries(self, unit: "Unit") -> int:
        """Remove all timeline entries for a specific unit.
        
        Used when units die or are otherwise removed from combat.
        
        Args:
            unit: The unit whose entries should be removed
            
        Returns:
            Number of entries removed
        """
        removed_count = 0
        
        # Mark matching entries as removed (lazy deletion)
        for entry in self._queue:
            if (entry.entity_type == "unit" and 
                entry.entity_id == unit.unit_id and 
                entry.sequence_id not in self._removed_entries):
                self._removed_entries.add(entry.sequence_id)
                removed_count += 1
        
        return removed_count
    
    def get_preview(self, count: int) -> list[TimelineEntry]:
        """Get the next N timeline entries.
        
        Args:
            count: Number of entries to return
            
        Returns:
            List of upcoming timeline entries (excluding removed ones)
        """
        preview = []
        temp_queue = self._queue.copy()
        
        while temp_queue and len(preview) < count:
            entry = heapq.heappop(temp_queue)
            if entry.sequence_id not in self._removed_entries:
                preview.append(entry)
        
        return preview
    
    def get_unit_ids_in_order(self, count: int) -> list[str]:
        """Get unit IDs in timeline order for UI display.
        
        Args:
            count: Maximum number of unit IDs to return
            
        Returns:
            List of unit IDs in chronological order of their next actions
        """
        entries = self.get_preview(count)
        return [entry.entity_id for entry in entries if entry.entity_type == "unit"]
    
    def advance_time(self, ticks: int) -> None:
        """Advance the timeline by a number of ticks.
        
        Used for testing or for skipping empty periods in the timeline.
        
        Args:
            ticks: Number of ticks to advance
        """
        self._current_time += ticks
    
    def clear(self) -> None:
        """Clear all entries from the timeline."""
        self._queue.clear()
        self._removed_entries.clear()
        self._current_time = 0
        self._sequence_counter = 0
    
    def _get_next_sequence_id(self) -> int:
        """Get the next unique sequence ID for stable sorting."""
        self._sequence_counter += 1
        return self._sequence_counter
    
    def cleanup_removed_entries(self) -> int:
        """Rebuild the queue without removed entries.
        
        This is an expensive operation that should only be called periodically
        when the removed entries set becomes too large.
        
        Returns:
            Number of entries actually removed from the queue
        """
        old_size = len(self._queue)
        
        # Rebuild queue without removed entries
        self._queue = [entry for entry in self._queue 
                      if entry.sequence_id not in self._removed_entries]
        heapq.heapify(self._queue)
        
        # Clear removed set
        self._removed_entries.clear()
        
        return old_size - len(self._queue)
    
    def get_stats(self) -> dict[str, Any]:
        """Get timeline statistics for debugging/monitoring.
        
        Returns:
            Dictionary with timeline statistics
        """
        active_entries = len([e for e in self._queue 
                            if e.sequence_id not in self._removed_entries])
        
        return {
            "current_time": self._current_time,
            "total_entries": len(self._queue),
            "active_entries": active_entries,
            "removed_entries": len(self._removed_entries),
            "sequence_counter": self._sequence_counter
        }