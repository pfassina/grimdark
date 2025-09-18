"""Selection and cursor management system.

This module consolidates cursor positioning and unit selection logic that was
previously scattered across timeline_manager and input_handler. It provides
centralized management of:
- Cursor positioning based on timeline events
- Unit selection state management
- Selection validation and cleanup
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.events.event_manager import EventManager
    from ...core.engine.game_state import GameState
    from ..map import GameMap

from ...core.events.events import (
    EventType,
    GameEvent,
    LogMessage,
    ManagerInitialized,
    UnitDefeated,
    UnitTurnEnded,
    UnitTurnStarted,
)
from ...core.data.game_enums import Team


class SelectionManager:
    """Manages cursor positioning and unit selection state.
    
    Centralizes logic that was previously scattered across:
    - TimelineManager: cursor positioning on timeline units
    - InputHandler: unit selection and cursor movement
    - Game: legacy cursor positioning methods
    """

    def __init__(
        self,
        game_map: "GameMap",
        game_state: "GameState", 
        event_manager: "EventManager",
    ):
        self.game_map = game_map
        self.state = game_state
        self.event_manager = event_manager

        # Subscribe to relevant events
        self._setup_event_subscriptions()

        # Emit initialization event
        self.event_manager.publish(
            ManagerInitialized(turn=0, manager_name="SelectionManager"),
            source="SelectionManager",
        )

    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for selection manager."""
        self.event_manager.subscribe(
            event_type=EventType.UNIT_DEFEATED,
            subscriber=self._handle_unit_defeated,
            subscriber_name="SelectionManager.unit_defeated",
        )
        
        self.event_manager.subscribe(
            event_type=EventType.UNIT_TURN_STARTED,
            subscriber=self._handle_unit_turn_started,
            subscriber_name="SelectionManager.unit_turn_started",
        )
        
        self.event_manager.subscribe(
            event_type=EventType.UNIT_TURN_ENDED,
            subscriber=self._handle_unit_turn_ended,
            subscriber_name="SelectionManager.unit_turn_ended",
        )

    def _emit_log(
        self, message: str, category: str = "SELECTION", level: str = "DEBUG"
    ) -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=self.state.battle.current_turn,
                message=message,
                category=category,
                level=level,
                source="SelectionManager",
            ),
            source="SelectionManager",
        )

    def position_cursor_and_select_unit(self, unit_id: str) -> None:
        """Position cursor on unit and set it as selected."""
        unit = self.game_map.get_unit(unit_id)
        assert unit, f"Unit {unit_id} not found on map"
        
        self.state.cursor.set_position(unit.position)
        self.state.battle.selected_unit_id = unit.unit_id
        self.state.battle.current_acting_unit_id = unit.unit_id
        
        self._emit_log(f"Positioned cursor and selected unit {unit.name} at {unit.position}")

    def select_unit_at_cursor(self) -> bool:
        """Select unit at current cursor position."""
        unit = self.game_map.get_unit_at(self.state.cursor.position)
        if not unit:
            return False
        
        # Only allow selecting player units
        if unit.team != Team.PLAYER:
            self._emit_log(f"Cannot select {unit.name} - not a player unit", level="WARNING")
            return False
        
        # Check if it's the unit's turn
        if (self.state.battle.current_acting_unit_id and 
            unit.unit_id != self.state.battle.current_acting_unit_id):
            self._emit_log(
                f"Cannot select {unit.name} - not their turn (current: {self.state.battle.current_acting_unit_id})",
                level="WARNING"
            )
            return False
        
        self.state.battle.selected_unit_id = unit.unit_id
        self._emit_log(f"Selected unit {unit.name}")
        return True

    def cycle_to_next_selectable_unit(self) -> bool:
        """Cycle to next selectable player unit."""
        current_selected = self.state.battle.selected_unit_id
        
        # Get all player units that can act
        player_units = self.game_map.get_units_by_team(Team.PLAYER)
        selectable_units = [unit for unit in player_units if unit.can_move or unit.can_act]
        
        if not selectable_units:
            return False
        
        # Find next unit in cycle
        if current_selected:
            current_unit = self.game_map.get_unit(current_selected)
            if current_unit and current_unit in selectable_units:
                current_index = selectable_units.index(current_unit)
                next_index = (current_index + 1) % len(selectable_units)
                next_unit = selectable_units[next_index]
            else:
                next_unit = selectable_units[0]
        else:
            next_unit = selectable_units[0]
        
        # Update selection and cursor
        self.state.battle.selected_unit_id = next_unit.unit_id
        self.state.cursor.set_position(next_unit.position)
        
        self._emit_log(f"Cycled to next selectable unit: {next_unit.name}")
        return True

    def clear_selection(self) -> None:
        """Clear unit selection and acting unit."""
        self.state.battle.selected_unit_id = None
        self.state.battle.current_acting_unit_id = None
        self._emit_log("Cleared unit selection")

    def _handle_unit_defeated(self, event: GameEvent) -> None:
        """Handle unit defeat by cleaning up selection state."""
        assert isinstance(event, UnitDefeated), f"Expected UnitDefeated, got {type(event)}"
        
        # Clear selection if the defeated unit was selected or acting
        if (self.state.battle.selected_unit_id == event.unit_id or 
            self.state.battle.current_acting_unit_id == event.unit_id):
            self.clear_selection()
            self._emit_log(f"Cleared selection for defeated unit {event.unit_name}")

    def _handle_unit_turn_started(self, event: GameEvent) -> None:
        """Handle unit turn started by positioning cursor and selecting unit."""
        assert isinstance(event, UnitTurnStarted), f"Expected UnitTurnStarted, got {type(event)}"
        
        unit = self.game_map.get_unit(event.unit_id)
        assert unit, f"Unit {event.unit_id} not found on map"
        
        # Position cursor and select unit (for all units, AI and player)
        self.position_cursor_and_select_unit(event.unit_id)
        
        if unit.team == Team.PLAYER:
            self._emit_log(f"Player unit {unit.name} turn started - ready for input")
        else:
            self._emit_log(f"AI unit {unit.name} turn started - AI will handle")

    def _handle_unit_turn_ended(self, event: GameEvent) -> None:
        """Handle unit turn ended by clearing selection state."""
        assert isinstance(event, UnitTurnEnded), f"Expected UnitTurnEnded, got {type(event)}"
        
        # Clear unit selection (selection state)
        self.state.battle.selected_unit_id = None
        
        self._emit_log("Unit turn ended - cleared selection state")