"""
Unit tests for the Timeline system.

Tests the core timeline functionality including entry scheduling, ordering,
and timeline management for the timeline-based combat system.
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.engine.timeline import TimelineEntry


class TestTimelineEntry:
    """Test TimelineEntry functionality."""

    def test_entry_creation(self):
        """Test basic timeline entry creation."""
        entry = TimelineEntry(
            execution_time=10,
            entity_id="unit_123",
            entity_type="unit",
            sequence_id=1
        )
        
        assert entry.execution_time == 10
        assert entry.entity_id == "unit_123"
        assert entry.entity_type == "unit"
        assert entry.sequence_id == 1

    def test_entry_ordering_by_time(self):
        """Test that entries are ordered by execution time."""
        entry1 = TimelineEntry(execution_time=5, entity_id="a", sequence_id=1)
        entry2 = TimelineEntry(execution_time=10, entity_id="b", sequence_id=2)
        
        assert entry1 < entry2
        assert not entry2 < entry1

    def test_entry_ordering_by_sequence_id(self):
        """Test that entries with same time are ordered by sequence ID."""
        entry1 = TimelineEntry(execution_time=10, entity_id="a", sequence_id=1)
        entry2 = TimelineEntry(execution_time=10, entity_id="b", sequence_id=2)
        
        assert entry1 < entry2
        assert not entry2 < entry1

    def test_entry_equality(self):
        """Test timeline entry equality."""
        entry1 = TimelineEntry(execution_time=10, entity_id="a", sequence_id=1)
        entry2 = TimelineEntry(execution_time=10, entity_id="a", sequence_id=1)
        entry3 = TimelineEntry(execution_time=10, entity_id="a", sequence_id=2)
        
        assert entry1 == entry2
        assert entry1 != entry3


class TestTimeline:
    """Test Timeline functionality."""

    def test_timeline_creation(self, timeline):
        """Test timeline initialization."""
        assert timeline.current_time == 0
        assert timeline.is_empty

    def test_add_entry(self, timeline):
        """Test adding entries to timeline."""
        entity_id = timeline.add_entry(
            time=10,
            entity_id="hazard_1",
            entity_type="hazard",
            action_description="Fire damage"
        )
        
        assert entity_id == "hazard_1"
        assert not timeline.is_empty

    def test_peek_next(self, timeline):
        """Test peeking at next entry without removing it."""
        timeline.add_entry(time=10, entity_id="a", entity_type="event")
        timeline.add_entry(time=5, entity_id="b", entity_type="event")
        
        # Should return earliest entry
        entry = timeline.peek_next()
        assert entry is not None
        assert entry.entity_id == "b"
        assert entry.execution_time == 5
        
        # Timeline should still have entries
        assert not timeline.is_empty

    def test_pop_next(self, timeline):
        """Test popping next entry and time advancement."""
        timeline.add_entry(time=10, entity_id="a", entity_type="event")
        timeline.add_entry(time=5, entity_id="b", entity_type="event")
        
        # Pop earliest entry
        entry = timeline.pop_next()
        assert entry is not None
        assert entry.entity_id == "b"
        assert timeline.current_time == 5
        
        # Pop next entry
        entry = timeline.pop_next()
        assert entry is not None
        assert entry.entity_id == "a"
        assert timeline.current_time == 10

    def test_remove_entry(self, timeline):
        """Test removing entries by entity ID."""
        timeline.add_entry(time=10, entity_id="unit_1", entity_type="unit")
        timeline.add_entry(time=15, entity_id="unit_1", entity_type="unit")
        timeline.add_entry(time=20, entity_id="unit_2", entity_type="unit")
        
        # Remove all entries for unit_1
        removed_count = timeline.remove_entry("unit_1")
        assert removed_count == 2
        
        # Only unit_2 entry should remain
        entry = timeline.peek_next()
        assert entry.entity_id == "unit_2"

    def test_get_preview(self, timeline):
        """Test getting preview of upcoming entries."""
        timeline.add_entry(time=5, entity_id="a", entity_type="event")
        timeline.add_entry(time=10, entity_id="b", entity_type="event")
        timeline.add_entry(time=15, entity_id="c", entity_type="event")
        
        preview = timeline.get_preview(count=2)
        assert len(preview) == 2
        assert preview[0].entity_id == "a"
        assert preview[1].entity_id == "b"

    def test_advance_time(self, timeline):
        """Test manually advancing timeline time."""
        initial_time = timeline.current_time
        timeline.advance_time(50)
        assert timeline.current_time == initial_time + 50

    def test_clear(self, timeline):
        """Test clearing timeline."""
        timeline.add_entry(time=10, entity_id="a", entity_type="event")
        timeline.advance_time(5)
        
        timeline.clear()
        assert timeline.is_empty
        assert timeline.current_time == 0

    def test_lazy_deletion(self, timeline):
        """Test that removed entries are handled with lazy deletion."""
        timeline.add_entry(time=10, entity_id="unit_1", entity_type="unit")
        timeline.add_entry(time=15, entity_id="unit_2", entity_type="unit")
        
        # Remove first unit
        timeline.remove_entry("unit_1")
        
        # Peek should skip removed entry and return second unit
        entry = timeline.peek_next()
        assert entry.entity_id == "unit_2"

    def test_cleanup_removed_entries(self, timeline):
        """Test cleanup of removed entries."""
        timeline.add_entry(time=10, entity_id="unit_1", entity_type="unit")
        timeline.add_entry(time=15, entity_id="unit_2", entity_type="unit")
        timeline.add_entry(time=20, entity_id="unit_3", entity_type="unit")
        
        # Remove some entries
        timeline.remove_entry("unit_1")
        timeline.remove_entry("unit_3")
        
        # Cleanup should remove 2 entries from queue
        removed_count = timeline.cleanup_removed_entries()
        assert removed_count == 2
        
        # Only unit_2 should remain
        entry = timeline.peek_next()
        assert entry.entity_id == "unit_2"

    def test_get_stats(self, timeline):
        """Test getting timeline statistics."""
        timeline.add_entry(time=10, entity_id="unit_1", entity_type="unit")
        timeline.add_entry(time=15, entity_id="unit_2", entity_type="unit")
        timeline.remove_entry("unit_1")
        
        stats = timeline.get_stats()
        assert stats["current_time"] == 0
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 1
        assert stats["removed_entries"] == 1

    def test_empty_timeline_operations(self, timeline):
        """Test operations on empty timeline."""
        assert timeline.peek_next() is None
        assert timeline.pop_next() is None
        assert timeline.get_preview(5) == []
        assert timeline.remove_entry("nonexistent") == 0