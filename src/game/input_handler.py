"""
Streamlined input handling system using modular architecture.

This module coordinates input processing through specialized components:
- KeyConfigLoader: Loads customizable key mappings from configuration
- InputContextManager: Manages input contexts and state
- ActionRegistry: Maps actions to commands and handles execution
- Command pattern: Encapsulates input actions as objects

The result is a clean, maintainable, and easily extensible input system.
"""

from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..core.event_manager import EventManager
    from ..core.game_state import GameState
    from ..core.renderer import Renderer
    from .combat_manager import CombatManager
    from .map import GameMap
    from .scenario_menu import ScenarioMenu
    from .timeline_manager import TimelineManager
    from .ui_manager import UIManager
    from .unit import Unit

from ..core.actions import ActionResult
from ..core.data_structures import Vector2, VectorArray
from ..core.event_manager import EventPriority
from ..core.events import (
    ActionCanceled,
    ActionSelected,
    LogMessage,
    LogSaveRequested,
    ManagerInitialized,
    MovementCanceled,
    UnitMoved,
)
from ..core.game_enums import Team
from ..core.game_state import BattlePhase
from ..core.input import InputEvent, InputType

# Import our new modular components
from ..core.input_system import (
    ActionRegistry,
    InputContext,
    InputContextManager,
    KeyConfigLoader,
)


class InputHandler:
    """Streamlined input handler using modular architecture."""

    def __init__(
        self,
        game_state: "GameState",
        renderer: "Renderer",
        event_manager: "EventManager",
        scenario_menu: "ScenarioMenu",
    ):
        # Core dependencies (required)
        self.state = game_state
        self.renderer = renderer
        self.event_manager = event_manager
        self.scenario_menu = scenario_menu

        # Optional dependencies configured when a battle is active
        self._game_map: Optional["GameMap"] = None
        self._combat_manager: Optional["CombatManager"] = None
        self._ui_manager: Optional["UIManager"] = None
        self._timeline_manager: Optional["TimelineManager"] = None

        # Initialize log manager for error logging
        from .log_manager import LogManager

        self.log_manager = LogManager(event_manager, game_state)

        # Initialize modular components
        self.context_manager = InputContextManager(game_state)
        self.action_registry = ActionRegistry()
        self.key_config = KeyConfigLoader()

        # Load key configuration
        self.key_config.load_config()

        # Callbacks that will be set by the main Game class
        self.on_quit: Optional[Callable] = None
        self.on_end_team_turn: Optional[Callable] = None
        self.on_load_selected_scenario: Optional[Callable] = None

        # Emit initialization event
        self.event_manager.publish(
            ManagerInitialized(turn=0, manager_name="InputHandler"),
            source="InputHandler",
        )

    # Properties for optional dependencies
    @property
    def game_map(self) -> "GameMap":
        if self._game_map is None:
            raise RuntimeError(
                "GameMap not set. Call configure_battle_dependencies() first."
            )
        return self._game_map

    @property
    def combat_manager(self) -> "CombatManager":
        if self._combat_manager is None:
            raise RuntimeError(
                "CombatManager not set. Call configure_battle_dependencies() first."
            )
        return self._combat_manager

    @property
    def ui_manager(self) -> "UIManager":
        if self._ui_manager is None:
            raise RuntimeError(
                "UIManager not set. Call configure_battle_dependencies() first."
            )
        return self._ui_manager

    @property
    def timeline_manager(self) -> "TimelineManager":
        if self._timeline_manager is None:
            raise RuntimeError(
                "TimelineManager not set. Call configure_battle_dependencies() first."
            )
        return self._timeline_manager

    def configure_battle_dependencies(
        self,
        *,
        game_map: "GameMap",
        combat_manager: "CombatManager",
        ui_manager: "UIManager",
        timeline_manager: "TimelineManager",
    ) -> None:
        """Configure all optional battle dependencies at once."""

        self._game_map = game_map
        self._combat_manager = combat_manager
        self._ui_manager = ui_manager
        self._timeline_manager = timeline_manager

    def _emit_log(
        self, message: str, category: str = "INPUT", level: str = "INFO"
    ) -> None:
        """Emit a log message event."""
        current_turn = getattr(self.state, "turn", 0)
        if hasattr(self.state, "battle") and hasattr(self.state.battle, "current_turn"):
            current_turn = self.state.battle.current_turn

        self.event_manager.publish(
            LogMessage(
                turn=current_turn,
                message=message,
                category=category,
                level=level,
                source="InputHandler",
            ),
            source="InputHandler",
        )

    def handle_input_events(self, events: list[InputEvent]) -> None:
        """Process a list of input events."""
        for event in events:
            if event.event_type == InputType.QUIT:
                # Show quit confirmation dialog instead of immediately quitting
                if not self.state.ui.is_dialog_open():
                    self.state.ui.open_dialog("confirm_quit")
            elif event.event_type == InputType.KEY_PRESS:
                self.handle_key_press(event)

    def handle_key_press(self, event: InputEvent) -> None:
        """Route key press events using the modular system."""
        # Get current context
        context = self.context_manager.get_current_context()

        # Get key mappings for this context
        key_mappings = self.key_config.get_key_mappings(context)

        # Look up action for this key (event.key is already a Key enum)
        action_name = key_mappings.get(event.key) if event.key else None

        if action_name:
            # Execute action through the registry
            self.action_registry.execute_action(action_name, self, context)

        # Handle special contexts that should close on unmapped keys
        if context in [InputContext.OVERLAY, InputContext.FORECAST]:
            # For overlays/forecast, any unmapped key closes them
            self.action_registry.execute_action("close_overlay", self, context)
        elif context in [InputContext.EXPANDED_LOG, InputContext.INSPECTION]:
            # For expanded log and inspection, only mapped keys should work - ignore unmapped keys
            pass
        else:
            # For other contexts, check if we should fall back to old system
            if self._should_use_fallback_for_context(context):
                self._handle_legacy_input(event, context)

    def _should_use_fallback_for_context(self, context: InputContext) -> bool:
        """Check if we should use legacy fallback for a context."""
        # Only use fallback for main menu input (not yet converted)
        return context == InputContext.MENU

    def _handle_legacy_input(self, event: InputEvent, context: InputContext) -> None:
        """Handle legacy input for contexts not yet fully converted."""
        if context == InputContext.MENU:
            self.handle_main_menu_input(event)

    def handle_main_menu_input(self, event: InputEvent) -> None:
        """Handle input while in main menu phase (legacy method)."""
        if self.scenario_menu:
            action = self.scenario_menu.handle_input(event)

            if action == "load" and self.on_load_selected_scenario:
                self.on_load_selected_scenario()
            elif action == "quit" and self.on_quit:
                self.on_quit()

    # ==================== ACTION METHODS FOR ACTION REGISTRY ====================
    # These methods are called by the ActionRegistry through ActionCommand

    def action_cycle_units(self) -> None:
        """Handle TAB key cycling for different phases."""
        if self.state.battle.phase == BattlePhase.UNIT_ACTION_SELECTION:
            self._cycle_timeline_front_units()
        elif (
            self.state.battle.phase == BattlePhase.ACTION_TARGETING
            and self.combat_manager
        ):
            self.combat_manager.cycle_targetable_enemies()

    def action_end_turn(self) -> None:
        """Handle E key press to end turn (with confirmation)."""
        self.state.ui.open_dialog("confirm_end_turn")

    def action_close_log(self) -> None:
        """Close the expanded log."""
        if self.ui_manager:
            self.ui_manager.close_overlay()

    def action_toggle_debug(self) -> None:
        """Toggle debug message visibility in log."""
        self._emit_log("=== DEBUG TOGGLE PRESSED ===", category="SYSTEM")
        # TODO: Emit toggle debug event - debug visibility should be handled by log manager
        # For now, just emit feedback messages

    def action_save_log(self) -> None:
        """Prompt to save log to file."""
        if self.state and self.ui_manager:
            # Open save confirmation dialog
            self.state.ui.open_dialog("confirm_save_log")
            self._emit_log("Save log dialog opened", category="SYSTEM")

    def action_scroll_up(self) -> None:
        """Scroll up in expanded log to see older messages."""
        if self.state:
            self.state.ui.scroll_expanded_log(5)  # Scroll up 5 lines

    def action_scroll_down(self) -> None:
        """Scroll down in expanded log to see newer messages."""
        if self.state:
            self.state.ui.scroll_expanded_log(-5)  # Scroll down 5 lines

    def action_dialog_move_left(self) -> None:
        """Move dialog selection left."""
        self.state.ui.move_dialog_selection(-1)

    def action_dialog_move_right(self) -> None:
        """Move dialog selection right."""
        self.state.ui.move_dialog_selection(1)

    def action_dialog_confirm(self) -> None:
        """Confirm dialog selection."""
        self._handle_dialog_confirmation()

    def action_dialog_cancel(self) -> None:
        """Cancel dialog."""
        self.state.ui.close_dialog()

    def action_menu_move_up(self) -> None:
        """Move menu selection up."""
        self.state.ui.move_action_menu_selection(-1)

    def action_menu_move_down(self) -> None:
        """Move menu selection down."""
        self.state.ui.move_action_menu_selection(1)

    def action_menu_select(self) -> None:
        """Select menu item."""
        if (
            self.state.ui.action_menu_items
            and 0
            <= self.state.ui.action_menu_selection
            < len(self.state.ui.action_menu_items)
        ):
            action = self.state.ui.action_menu_items[
                self.state.ui.action_menu_selection
            ]
            self._handle_action_selection(action)

    def action_menu_cancel(self) -> None:
        """Handle cancel with hierarchical logic based on current phase and unit state."""
        current_phase = self.state.battle.phase
        unit_id = self.state.battle.selected_unit_id

        # These should never be None when cancel is called - if they are, it's a bug
        assert unit_id is not None, "Cancel called but no unit is selected"
        unit = self.game_map.get_unit(unit_id)
        assert unit is not None, f"Cancel called but unit {unit_id} not found in map"

        # Scenario 1: Cancel during action targeting - return to action selection
        if current_phase == BattlePhase.ACTION_TARGETING:
            self.state.battle.clear_pending_action()
            # Clear attack state when canceling targeting
            if self.combat_manager:
                self.combat_manager.clear_attack_state()
            # Restore movement range when returning to action selection
            if self.state.battle.original_movement_range:
                self.state.battle.set_movement_range(
                    self.state.battle.original_movement_range
                )
                self._emit_log(f"Restored movement range for {unit.name}", "CANCEL")
            # Reopen the action menu for the unit
            self._build_action_menu_for_unit(unit)
            self.event_manager.publish(
                ActionCanceled(
                    turn=self.state.battle.current_turn,
                    unit_name=unit.name,
                    unit_id=unit.unit_id,
                    canceled_action="targeting",
                    return_to_phase="UNIT_ACTION_SELECTION",
                ),
                priority=EventPriority.HIGH,
                source="InputHandler",
            )

        # Scenario 2: Cancel during action selection - return to movement
        elif current_phase == BattlePhase.UNIT_ACTION_SELECTION:
            self.state.ui.close_action_menu()
            # Get the original position from when the unit's turn started
            original_pos = self.state.battle.original_unit_position
            if original_pos:
                original_position = (original_pos.y, original_pos.x)
            else:
                # Fallback to current position if no original stored
                original_position = (unit.position.y, unit.position.x)

            self.event_manager.publish(
                MovementCanceled(
                    turn=self.state.battle.current_turn,
                    unit_name=unit.name,
                    unit_id=unit.unit_id,
                    original_position=original_position,
                ),
                priority=EventPriority.HIGH,
                source="InputHandler",
            )

        # Scenario 3: Cancel during movement - return unit to original position
        elif current_phase == BattlePhase.UNIT_MOVING:
            assert (
                hasattr(self.state.battle, "original_unit_position")
                and self.state.battle.original_unit_position
            ), "Cancel called during movement but no original position stored"

            # Move unit back to original position
            original_pos = self.state.battle.original_unit_position
            self.game_map.move_unit(unit.unit_id, original_pos)

            # Clear movement state
            self.state.battle.movement_range = VectorArray()
            self.state.battle.selected_unit_id = None
            self.state.battle.original_unit_position = None

            self._emit_log(f"{unit.name} returned to original position", "CANCEL")
            # Movement cancel stays in same phase - no event needed for phase transition

        else:
            # This should never happen - cancel called in unexpected phase
            assert False, f"Cancel called in unexpected phase: {current_phase}"

    # ==================== HELPER METHODS (PRESERVED FROM ORIGINAL) ====================

    def _cycle_timeline_front_units(self) -> None:
        """Cycle through units that are at the front of the timeline."""
        if not hasattr(self.state.battle, "timeline") or not self.state.battle.timeline:
            return

        timeline = self.state.battle.timeline
        current_time = timeline.current_time

        # Get all units that can act right now
        actionable_units = []
        for entry in timeline.get_preview(5):
            if entry.execution_time <= current_time and entry.entity_type == "unit":
                unit = self.game_map.get_unit(entry.entity_id)
                if unit is None:
                    raise ValueError(
                        f"Timeline entry references non-existent unit: {entry.entity_id}"
                    )
                if unit.team == Team.PLAYER:
                    actionable_units.append(unit)

        if not actionable_units:
            return

        # Cycle between actionable units
        current_selected = self.state.battle.selected_unit_id
        current_index = -1

        for i, unit in enumerate(actionable_units):
            if unit.unit_id == current_selected:
                current_index = i
                break

        next_index = (current_index + 1) % len(actionable_units)
        next_unit = actionable_units[next_index]

        self.state.battle.selected_unit_id = next_unit.unit_id
        self.state.cursor.set_position(next_unit.position)

        self._emit_log(f"TAB: Selected {next_unit.name} (can act now)", category="UI")

    def _handle_dialog_confirmation(self) -> None:
        """Handle dialog confirmation based on dialog type."""
        dialog_type = self.state.ui.active_dialog
        selection = self.state.ui.get_dialog_selection()

        # Handle confirm_end_turn
        if dialog_type == "confirm_end_turn":
            if selection == 0 and self.on_end_team_turn:  # Yes
                self.on_end_team_turn()
            self.state.ui.close_dialog()
            return

        # Handle confirm_friendly_fire
        if dialog_type == "confirm_friendly_fire":
            if selection == 0 and self.combat_manager:  # Yes - proceed with attack
                success = self.combat_manager.execute_confirmed_attack()
            self.state.ui.close_dialog()
            return

        # Handle confirm_wait
        if dialog_type == "confirm_wait":
            if selection == 0:  # Yes - proceed with wait
                result = self.timeline_manager.execute_unit_action("Wait")

                if result == ActionResult.SUCCESS:
                    self._emit_log(
                        "Unit waits and will act again later", category="TIMELINE"
                    )
                else:
                    self._emit_log(f"Wait action failed: {result}", level="WARNING")
            self.state.ui.close_dialog()
            return

        # Handle confirm_save_log
        if dialog_type == "confirm_save_log":
            if selection == 0:  # Yes - save log
                # Emit save log event - log manager will handle file saving
                current_turn = getattr(self.state, "turn", 0)
                if hasattr(self.state, "battle") and hasattr(
                    self.state.battle, "current_turn"
                ):
                    current_turn = self.state.battle.current_turn

                self.event_manager.publish(
                    LogSaveRequested(turn=current_turn),
                    source="InputHandler",
                )
                self._emit_log("Log save requested", category="SYSTEM")
            self.state.ui.close_dialog()
            return

        # Handle confirm_quit
        if dialog_type == "confirm_quit":
            if selection == 0 and self.on_quit:  # Yes - quit
                self.on_quit()
            self.state.ui.close_dialog()
            return

        # Handle game_over
        if dialog_type == "game_over":
            if selection == 0:  # View Log
                self.state.ui.close_dialog()
                if self.ui_manager:
                    self.ui_manager.show_expanded_log()
            elif selection == 1 and self.on_quit:  # Quit Game
                self.on_quit()
            else:
                self.state.ui.close_dialog()
            return

        # Default case - close any other dialog
        self.state.ui.close_dialog()

    def _handle_action_selection(self, action: str) -> None:
        """Handle the selected action from the action menu."""
        # Close action menu first
        self.state.ui.close_action_menu()

        if action == "Wait":
            # Check if unit has only moved and needs confirmation
            unit_id = self.state.battle.selected_unit_id
            assert unit_id is not None, "Wait action called but no unit is selected"
            current_unit = self.game_map.get_unit(unit_id)
            assert current_unit is not None, f"Unit {unit_id} not found on map"

            if not current_unit.status.has_acted:
                # Unit hasn't performed any action, show confirmation dialog
                self.state.ui.open_dialog("confirm_wait")
                return

            # Execute wait action directly
            result = self.timeline_manager.execute_unit_action("Wait")

            if result == ActionResult.SUCCESS:
                self._emit_log(
                    "Unit waits and will act again later", category="TIMELINE"
                )
            else:
                self._emit_log(f"Wait action failed: {result}", level="WARNING")

        elif action == "Attack" or "Attack" in action:
            # Attack needs targeting - first set up the pending action through timeline manager
            if self.state.battle.selected_unit_id and self.combat_manager:
                unit = self.game_map.get_unit(self.state.battle.selected_unit_id)
                if unit:
                    # Set up pending action through timeline manager
                    result = self.timeline_manager.execute_unit_action(action)
                    if result == ActionResult.REQUIRES_TARGET:
                        self._emit_log(
                            f"{unit.name} preparing to attack. Select target with arrow keys, Enter to confirm.",
                            category="UI",
                        )
                        # Emit action selected event - PhaseManager will transition to ACTION_TARGETING
                        self.event_manager.publish(
                            ActionSelected(
                                turn=self.state.battle.current_turn,
                                unit_name=unit.name,
                                unit_id=unit.unit_id,
                                action_name=action,
                                action_type="Attack",
                            ),
                            priority=EventPriority.HIGH,
                            source="InputHandler",
                        )
                        self.combat_manager.setup_attack_targeting(unit)
                    else:
                        self._emit_log(
                            f"Attack action setup failed: {result}", level="WARNING"
                        )

        else:
            # Generic action
            result = self.timeline_manager.execute_unit_action(action)
            if result == ActionResult.SUCCESS:
                self._emit_log(
                    f"Action {action} executed successfully", "INPUT", "INFO"
                )
            elif result == ActionResult.REQUIRES_TARGET:
                # Emit action selected event - PhaseManager will transition to ACTION_TARGETING
                if self.state.battle.selected_unit_id:
                    unit = self.game_map.get_unit(self.state.battle.selected_unit_id)
                    if unit:
                        self.event_manager.publish(
                            ActionSelected(
                                turn=self.state.battle.current_turn,
                                unit_name=unit.name,
                                unit_id=unit.unit_id,
                                action_name=action,
                                action_type="Generic",
                            ),
                            priority=EventPriority.HIGH,
                            source="InputHandler",
                        )
                self._emit_log(
                    f"Action {action} needs target selection", "INPUT", "INFO"
                )
            else:
                self._emit_log(f"Action {action} failed: {result}", "INPUT", "WARNING")

    # ==================== PRESERVED METHODS FOR COMPLEX GAME LOGIC ====================

    def _handle_unit_selection_confirm(self, cursor_position: Vector2) -> bool:
        """Handle confirmation during unit selection phase."""
        unit = self.game_map.get_unit_at(cursor_position)
        if not unit:
            return False

        # CRITICAL: Always check team first - only player units can be selected
        if unit.team != Team.PLAYER:
            self._emit_log(
                f"Cannot select {unit.name} - not a player unit (team: {unit.team})",
                level="INFO",
            )
            return False

        # Only allow selecting the current acting unit according to timeline
        if hasattr(self.state.battle, "current_acting_unit_id"):
            # Check if this is the unit that should be acting according to timeline
            if (
                self.state.battle.current_acting_unit_id
                and unit.unit_id != self.state.battle.current_acting_unit_id
            ):
                self._emit_log(
                    f"Cannot select {unit.name} - not their turn (current: {self.state.battle.current_acting_unit_id})",
                    level="INFO",
                )
                return False  # Not this unit's turn

        # Unit is valid for selection
        self.state.battle.selected_unit_id = unit.unit_id
        self.state.battle.original_unit_position = unit.position
        # Phase transition to UNIT_MOVING will be handled by TimelineManager via UnitTurnStarted event
        movement_range = self.game_map.calculate_movement_range(unit)
        self.state.battle.set_movement_range(movement_range)
        return True

    def _handle_unit_movement_confirm(self, cursor_position: Vector2) -> bool:
        """Handle confirmation during unit movement phase."""
        if self.state.battle.is_in_movement_range(cursor_position):
            if self.state.battle.selected_unit_id:
                unit = self.game_map.get_unit(self.state.battle.selected_unit_id)
                if unit:
                    old_position = unit.position

                    # Special case: if user selects current unit tile, go directly to action selection
                    if cursor_position == unit.position:
                        # Don't clear movement_range - preserve it during action selection
                        # Emit unit moved event even though position didn't change (for phase transition)
                        self.event_manager.publish(
                            UnitMoved(
                                turn=self.state.battle.current_turn,
                                unit_name=unit.name,
                                unit_id=unit.unit_id,
                                team=unit.team,
                                from_position=(old_position.y, old_position.x),
                                to_position=(cursor_position.y, cursor_position.x),
                            ),
                            priority=EventPriority.HIGH,  # High priority for immediate phase transition
                            source="InputHandler",
                        )
                        self._emit_log(
                            f"{unit.name} stays in place, entering action selection",
                            category="MOVEMENT",
                        )
                        return True

                    # Normal movement case
                    if self.game_map.move_unit(unit.unit_id, cursor_position):
                        # Don't clear movement_range - preserve it during action selection
                        # Emit single unit moved event with unit_id for phase transitions
                        self.event_manager.publish(
                            UnitMoved(
                                turn=self.state.battle.current_turn,
                                unit_name=unit.name,
                                unit_id=unit.unit_id,
                                team=unit.team,
                                from_position=(old_position.y, old_position.x),
                                to_position=(cursor_position.y, cursor_position.x),
                            ),
                            priority=EventPriority.HIGH,  # High priority for immediate phase transition
                            source="InputHandler",
                        )
                        self._emit_log(
                            f"{unit.name} moved to {cursor_position}",
                            category="MOVEMENT",
                        )

                        # MovementCompleted event published above will trigger phase transition
                        # UIManager will detect UNIT_ACTION_SELECTION phase and show action menu
                        self._emit_log(
                            f"{unit.name} movement completed, entering action selection",
                            category="UI",
                        )
                        return True
        return False

    def _handle_action_menu_confirm(self) -> bool:
        """Handle confirmation in action menu phase."""
        selected_action = self.state.ui.get_selected_action()
        if selected_action:
            self._handle_action_selection(selected_action)
            return True
        return False

    def _handle_action_targeting_confirm(self, cursor_position: Vector2) -> bool:
        """Handle confirmation during action targeting phase."""
        # For attack actions, use the combat manager directly for AOE support
        if (
            self.state.battle.pending_action
            and self.state.battle.pending_action
            in ["Attack", "Quick Strike", "Power Attack"]
            and self.combat_manager
        ):
            # Use combat manager for attack execution (supports AOE)
            success = self.combat_manager.execute_attack_at_cursor()
            if success:
                self._emit_log(
                    f"Attack executed at {cursor_position}", category="BATTLE"
                )
                return True
            else:
                # Check if there's a unit at cursor for more specific error message
                target_unit = self.game_map.get_unit_at(cursor_position)
                if not self.state.battle.is_in_attack_range(cursor_position):
                    self._emit_log(
                        "Target position not in attack range", level="WARNING"
                    )
                elif not target_unit and not self.state.battle.aoe_tiles:
                    self._emit_log(
                        "No valid target at cursor position", level="WARNING"
                    )
                else:
                    self._emit_log("Attack failed", level="WARNING")
                return False

        # For non-attack actions, use timeline manager
        result = self.timeline_manager.handle_action_targeting(cursor_position)
        if result == ActionResult.SUCCESS:
            self._emit_log(
                f"Action executed successfully at {cursor_position}", category="UI"
            )
            return True

        self._emit_log(f"Action failed: {result}", level="WARNING")
        return False

    def _handle_unit_acting_confirm(self) -> bool:
        """Handle confirmation during unit acting phase."""
        if self.combat_manager:
            success = self.combat_manager.execute_attack_at_cursor()
            if success:
                return True
        return False

    def _handle_movement_cancel(self) -> None:
        """Handle cancel during movement phase."""
        selected_unit_id = self.state.battle.selected_unit_id
        original_position = self.state.battle.original_unit_position

        # If unit hasn't moved, do nothing (as per TODO requirements)
        if not selected_unit_id or not original_position:
            return

        unit = self.game_map.get_unit(selected_unit_id)
        if not unit:
            return

        # Check if unit has actually moved from original position
        if unit.position == original_position:
            # Unit hasn't moved, do nothing
            self._emit_log(f"{unit.name} hasn't moved - cancel ignored", category="UI")
            return

        # Unit has moved - return to original position
        self.game_map.move_unit(unit.unit_id, original_position)
        self.state.cursor.set_position(original_position)

        # Reset the unit's movement status since we're canceling the move
        unit.status.has_moved = False

        # DO NOT emit UnitMoved event - this would trigger phase transition!
        # We want to stay in UNIT_MOVING phase

        self._emit_log(
            f"{unit.name} returned to original position, can continue moving",
            category="MOVEMENT",
        )

        # Recalculate movement range for continued movement
        movement_range = self.game_map.calculate_movement_range(unit)
        self.state.battle.set_movement_range(movement_range)

        # Stay in movement phase - don't end turn or call Wait
        # This allows the player to continue moving the unit

    def _handle_targeting_cancel(self) -> None:
        """Handle cancel during targeting phase."""
        self.state.battle.attack_range = VectorArray()
        self.state.battle.selected_target = None
        self.state.battle.aoe_tiles = VectorArray()
        # Delegate to hierarchical cancel system
        self.action_menu_cancel()

    def _handle_action_targeting_cancel(self) -> None:
        """Handle cancel during action targeting phase."""
        # Use the hierarchical cancel system directly - it now handles attack state clearing
        self.action_menu_cancel()

    def _handle_unit_acting_cancel(self) -> None:
        """Handle cancel during unit acting phase."""
        if self.combat_manager:
            self.combat_manager.clear_attack_state()
        # Delegate to hierarchical cancel system
        self.action_menu_cancel()

    def _handle_inspect_confirm(self, position: Vector2) -> bool:
        """Handle Enter key in inspect mode - delegate to UI manager for panel display."""
        # Let UI manager handle building and showing the inspection panel
        # UI manager has access to game_map and game_state for data gathering
        self.ui_manager.show_inspection_at_position(position)

        # Log the inspection action
        unit = self.game_map.get_unit_at(position)
        if unit:
            self._emit_log(f"Inspecting {unit.name} at {position}", category="UI")
        else:
            self._emit_log(f"Inspecting tile at {position}", category="UI")

        return True

    def _build_action_menu_for_unit(self, unit: "Unit") -> None:
        """Build action menu items based on unit's current capabilities."""
        actions = []

        if unit.can_act:
            actions.append("Attack")

        actions.append("Wait")
        self.state.ui.open_action_menu(actions)

        # Auto-select appropriate action
        if unit.can_act:
            attack_range = self.game_map.calculate_attack_range(unit)
            has_enemy_targets = any(
                self.game_map.get_unit_at(pos)
                and self.game_map.get_unit_at(pos).team != unit.team  # type: ignore[union-attr]
                for pos in attack_range
            )

            if has_enemy_targets and "Attack" in actions:
                self.state.ui.action_menu_selection = actions.index("Attack")
            elif "Wait" in actions:
                self.state.ui.action_menu_selection = actions.index("Wait")

    # ==================== CONFIGURATION AND DEBUG ====================

    def reload_key_config(self) -> bool:
        """Reload key configuration from file."""
        return self.key_config.reload_config()

    def get_debug_info(self) -> dict[str, Any]:
        """Get debug information about the input system."""
        return {
            "current_context": self.context_manager.get_current_context().value,
            "active_scheme": self.key_config.get_active_scheme(),
            "config_validation": self.key_config.validate_config(),
            "action_registry": self.action_registry.get_debug_info(),
        }
