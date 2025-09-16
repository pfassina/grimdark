"""
Command pattern implementation for input actions.

This module defines the command interface and concrete command implementations
for handling different types of user input actions.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from ..actions import ActionResult
from ..game_state import BattlePhase
from ..data_structures import VectorArray
from ..events import ActionSelected, ActionExecuted

if TYPE_CHECKING:
    from ...game.input_handler import InputHandler



class Command(ABC):
    """Abstract base class for all input commands."""
    
    @abstractmethod
    def execute(self, handler: "InputHandler") -> bool:
        """
        Execute the command.
        
        Args:
            handler: The input handler instance
            
        Returns:
            bool: True if command was handled successfully, False otherwise
        """
        pass


class ActionCommand(Command):
    """Generic command that delegates to a handler method."""
    
    def __init__(self, action_name: str, **kwargs: Any):
        self.action_name = action_name
        self.kwargs = kwargs
    
    def execute(self, handler: "InputHandler") -> bool:
        """Execute by calling the corresponding action method on the handler."""
        method_name = f"action_{self.action_name}"
        if hasattr(handler, method_name):
            method = getattr(handler, method_name)
            if self.kwargs:
                return method(**self.kwargs) is not False
            else:
                return method() is not False
        return False


# Concrete command implementations for common actions

class MoveCursorCommand(Command):
    """Command for moving the cursor in a specific direction."""
    
    def __init__(self, dx: int, dy: int):
        self.dx = dx
        self.dy = dy
    
    def execute(self, handler: "InputHandler") -> bool:
        """Move cursor by the specified delta."""
        if not handler.state or not handler.game_map:
            return False
        
        old_pos = handler.state.cursor.position
        handler.state.cursor.move(
            self.dx, self.dy, 
            handler.game_map.width, 
            handler.game_map.height
        )
        new_pos = handler.state.cursor.position
        
        if hasattr(handler, 'log_manager') and handler.log_manager:
            handler.log_manager.debug(f"MoveCursor: {old_pos} -> {new_pos} (delta: {self.dx}, {self.dy})")
        
        # Emit cursor moved event for systems that need to react to cursor changes
        from ..events import CursorMoved
        handler.event_manager.publish(
            CursorMoved(
                turn=handler.state.battle.current_turn,
                from_position=(old_pos.y, old_pos.x),
                to_position=(new_pos.y, new_pos.x),
                context="targeting" if handler.state.battle.phase.name in ["ACTION_EXECUTION", "ACTION_TARGETING"] else "navigation"
            ),
            source="MoveCursorCommand"
        )
        
        # For targeting phases, also update attack targeting immediately
        if handler.state.battle.phase.name in ["ACTION_EXECUTION", "ACTION_TARGETING"]:
            if hasattr(handler, 'combat_manager') and handler.combat_manager:
                handler.combat_manager.update_attack_targeting()
        
        # Update movement preview if needed (non-targeting cursor movement)
        if (handler.state.battle.selected_unit_id 
            and handler.on_movement_preview_update
            and handler.state.battle.phase.name not in ["ACTION_EXECUTION", "ACTION_TARGETING"]):
            handler.on_movement_preview_update()
        
        return True


class ConfirmSelectionCommand(Command):
    """Command for confirming the current selection."""
    
    def execute(self, handler: "InputHandler") -> bool:
        """Handle confirmation based on current battle phase."""
        cursor_position = handler.state.cursor.position
        phase = handler.state.battle.phase

        # Log using event system
        from ..events import DebugMessage
        handler.event_manager.publish(
            DebugMessage(turn=0, message=f"ConfirmSelection: cursor at {cursor_position}, phase: {phase.name}", source="ConfirmSelectionCommand"),
            source="ConfirmSelectionCommand"
        )

        # Check phase names correctly - timeline system uses different phases
        if phase.name == "INSPECT":
            return handler._handle_inspect_confirm(cursor_position)
        elif phase.name in ["UNIT_SELECTION", "TIMELINE_PROCESSING"]:
            return handler._handle_unit_selection_confirm(cursor_position)
        elif phase.name == "UNIT_MOVING":
            # Log using event system
            handler.event_manager.publish(
                DebugMessage(turn=0, message="Calling _handle_unit_movement_confirm for UNIT_MOVING phase", source="ConfirmSelectionCommand"),
                source="ConfirmSelectionCommand"
            )
            return handler._handle_unit_movement_confirm(cursor_position)
        elif phase.name in ["ACTION_MENU", "UNIT_ACTION_SELECTION"]:
            return handler._handle_action_menu_confirm()
        elif phase.name == "ACTION_TARGETING":
            return handler._handle_action_targeting_confirm(cursor_position)
        elif phase.name == "ACTION_EXECUTION":
            return handler._handle_unit_acting_confirm()
        
        return False


class CancelActionCommand(Command):
    """Command for canceling the current action."""
    
    def execute(self, handler: "InputHandler") -> bool:
        """Handle cancel based on current battle phase."""
        # First check if there's an active dialog - if so, just close it
        if handler.state.ui.active_dialog:
            handler.state.ui.close_dialog()
            return True
            
        phase = handler.state.battle.phase
        
        if phase.name == "INSPECT":
            # Exit inspect mode - same as pressing V
            if handler.state.battle.previous_phase:
                handler.state.battle.phase = handler.state.battle.previous_phase
                handler.state.battle.previous_phase = None
            else:
                handler.state.battle.phase = BattlePhase.TIMELINE_PROCESSING
            if handler.log_manager:
                handler.log_manager.ui("Inspect mode ended")
        elif phase.name == "UNIT_MOVING":
            handler._handle_movement_cancel()
        elif phase.name in ["ACTION_MENU", "UNIT_ACTION_SELECTION"]:
            handler.action_menu_cancel()
        elif phase.name == "TARGETING":
            handler._handle_targeting_cancel()
        elif phase.name == "ACTION_TARGETING":
            handler._handle_action_targeting_cancel()
        elif phase.name == "ACTION_EXECUTION":
            handler._handle_unit_acting_cancel()
        
        return True


class ShowOverlayCommand(Command):
    """Command for showing an information overlay."""
    
    def __init__(self, overlay_type: str):
        self.overlay_type = overlay_type
    
    def execute(self, handler: "InputHandler") -> bool:
        """Show the specified overlay type."""
        if not handler.ui_manager:
            return False
            
        if self.overlay_type == "objectives":
            handler.ui_manager.show_objectives()
        elif self.overlay_type == "help":
            handler.ui_manager.show_help()
        elif self.overlay_type == "minimap":
            handler.ui_manager.show_minimap()
        elif self.overlay_type == "expanded_log":
            handler.ui_manager.show_expanded_log()
        else:
            return False
            
        return True


class CloseOverlayCommand(Command):
    """Command for closing the current overlay."""
    
    def execute(self, handler: "InputHandler") -> bool:
        """Close the current overlay or forecast."""
        if handler.state.ui.is_forecast_active():
            handler.state.ui.stop_forecast()
        elif handler.ui_manager:
            handler.ui_manager.close_overlay()
        return True


class QuitGameCommand(Command):
    """Command for quitting the game."""
    
    def execute(self, handler: "InputHandler") -> bool:
        """Show quit confirmation dialog instead of immediately quitting."""
        if not handler.state.ui.is_dialog_open():
            handler.state.ui.open_dialog("confirm_quit")
            return True
        return False


class DirectAttackCommand(Command):
    """Command for initiating a direct attack."""
    
    def execute(self, handler: "InputHandler") -> bool:
        """Handle direct attack based on current game state."""
        # Only allow during player turn and when a unit is selected
        if handler.state.battle.current_team != 0 or not handler.state.battle.selected_unit_id:
            return False

        unit = handler.game_map.get_unit(handler.state.battle.selected_unit_id)
        if not unit or not unit.can_act or not handler.combat_manager:
            return False
        
        phase = handler.state.battle.phase
        
        # Handle quick attack based on current phase
        if phase.name == "UNIT_SELECTION":
            # Unit just selected, transition to attack directly
            handler.event_manager.publish(
                ActionSelected(
                    turn=handler.state.battle.current_turn,
                    unit_name=unit.name,
                    unit_id=unit.unit_id,
                    action_name="Quick Attack",
                    action_type="Attack"
                ),
                source="QuickAttackCommand"
            )
            handler.combat_manager.setup_attack_targeting(unit)
        elif phase.name == "UNIT_MOVING":
            # Unit is in movement, skip to attack
            handler.state.battle.movement_range = VectorArray()
            handler.event_manager.publish(
                ActionSelected(
                    turn=handler.state.battle.current_turn,
                    unit_name=unit.name,
                    unit_id=unit.unit_id,
                    action_name="Quick Attack",
                    action_type="Attack"
                ),
                source="QuickAttackCommand"
            )
            handler.combat_manager.setup_attack_targeting(unit)
        elif phase.name == "ACTION_MENU":
            # Use normal action selection
            handler._handle_action_selection("Attack")
        
        return True


class WaitUnitCommand(Command):
    """Command for making a unit wait (end turn)."""
    
    def execute(self, handler: "InputHandler") -> bool:
        """Make the selected unit wait."""
        # Check if a unit is selected
        if not handler.state.battle.selected_unit_id:
            return False

        unit = handler.game_map.get_unit(handler.state.battle.selected_unit_id)
        if not unit:
            return False
        
        # Execute wait action through timeline system (timeline manager is always present)
        if not handler.timeline_manager:
            raise RuntimeError("Timeline manager is required but not present")
        result = handler.timeline_manager.execute_unit_action("Wait")
        return result == ActionResult.SUCCESS


class StartInspectModeCommand(Command):
    """Command for toggling free cursor inspect mode."""
    
    def execute(self, handler: "InputHandler") -> bool:
        """Toggle inspect mode - start if not in inspect, exit if already inspecting."""
        current_phase = handler.state.battle.phase
        
        if current_phase == BattlePhase.INSPECT:
            # Exit inspect mode - restore previous phase
            if handler.state.battle.previous_phase:
                handler.state.battle.phase = handler.state.battle.previous_phase
                handler.state.battle.previous_phase = None
            else:
                # Fallback to timeline processing if no previous phase stored
                handler.state.battle.phase = BattlePhase.TIMELINE_PROCESSING
            
            if handler.log_manager:
                handler.log_manager.ui("Inspect mode ended")
        else:
            # Enter inspect mode
            handler.state.battle.previous_phase = current_phase
            handler.state.battle.phase = BattlePhase.INSPECT
            
            # Clear any active selections to free up the cursor
            handler.state.battle.movement_range = VectorArray()
            handler.state.battle.attack_range = VectorArray() 
            handler.state.battle.aoe_tiles = VectorArray()
            handler.state.ui.close_action_menu()
            
            if handler.log_manager:
                handler.log_manager.ui("Inspect mode active - use arrow keys to explore, V to exit")
        
        return True