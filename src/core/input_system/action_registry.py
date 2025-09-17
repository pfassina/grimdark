"""
Action registry system for dynamic command dispatch.

This module provides a registry pattern for mapping action names to command
instances, enabling clean separation of input handling from action implementation.
"""
from typing import TYPE_CHECKING, Callable, Optional, Any

if TYPE_CHECKING:
    from ...game.input_handler import InputHandler

from .commands import (
    Command, ActionCommand, MoveCursorCommand, ConfirmSelectionCommand,
    CancelActionCommand, ShowOverlayCommand, CloseOverlayCommand,
    QuitGameCommand, DirectAttackCommand, WaitUnitCommand,
    StartInspectModeCommand, CloseInspectionCommand
)
from .context_manager import InputContext


class ActionRegistry:
    """Registry for mapping action names to command instances."""
    
    def __init__(self):
        self._commands: dict[str, Command] = {}
        self._context_commands: dict[InputContext, dict[str, Command]] = {}
        self._setup_default_commands()
    
    def register_command(self, action_name: str, command: Command, context: Optional[InputContext] = None) -> None:
        """
        Register a command for an action.
        
        Args:
            action_name: The name of the action
            command: The command instance to execute
            context: Optional specific context for the command
        """
        if context:
            if context not in self._context_commands:
                self._context_commands[context] = {}
            self._context_commands[context][action_name] = command
        else:
            self._commands[action_name] = command
    
    def register_action_method(self, action_name: str, context: Optional[InputContext] = None) -> None:
        """
        Register an action that delegates to a handler method.
        
        Args:
            action_name: The name of the action (will call handler.action_{name})
            context: Optional specific context for the action
        """
        command = ActionCommand(action_name)
        self.register_command(action_name, command, context)
    
    def get_command(self, action_name: str, context: Optional[InputContext] = None) -> Optional[Command]:
        """
        Get a command for the specified action and context.
        
        Args:
            action_name: The name of the action
            context: The current input context
            
        Returns:
            Command: The command instance, or None if not found
        """
        # First check context-specific commands
        if context and context in self._context_commands:
            if action_name in self._context_commands[context]:
                return self._context_commands[context][action_name]
        
        # Fall back to global commands
        return self._commands.get(action_name)
    
    def execute_action(self, action_name: str, handler: "InputHandler", context: Optional[InputContext] = None) -> bool:
        """
        Execute an action by name.
        
        Args:
            action_name: The name of the action to execute
            handler: The input handler instance
            context: The current input context
            
        Returns:
            bool: True if action was executed successfully
        """
        command = self.get_command(action_name, context)
        if command:
            try:
                return command.execute(handler)
            except Exception as e:
                # Log error but don't crash
                if hasattr(handler, 'log_manager') and handler.log_manager:
                    handler.log_manager.error(f"Error executing action '{action_name}': {e}")
                return False
        return False
    
    def is_action_registered(self, action_name: str, context: Optional[InputContext] = None) -> bool:
        """
        Check if an action is registered.
        
        Args:
            action_name: The name of the action
            context: The input context to check
            
        Returns:
            bool: True if action is registered
        """
        return self.get_command(action_name, context) is not None
    
    def get_registered_actions(self, context: Optional[InputContext] = None) -> list[str]:
        """
        Get list of all registered action names.
        
        Args:
            context: Optional context to filter by
            
        Returns:
            list[str]: List of action names
        """
        actions = set(self._commands.keys())
        
        if context and context in self._context_commands:
            actions.update(self._context_commands[context].keys())
        elif context is None:
            # Include all context-specific actions
            for ctx_commands in self._context_commands.values():
                actions.update(ctx_commands.keys())
        
        return sorted(list(actions))
    
    def clear_context_commands(self, context: InputContext) -> None:
        """
        Clear all commands for a specific context.
        
        Args:
            context: The context to clear
        """
        if context in self._context_commands:
            del self._context_commands[context]
    
    def clear_all_commands(self) -> None:
        """Clear all registered commands."""
        self._commands.clear()
        self._context_commands.clear()
        self._setup_default_commands()
    
    def _setup_default_commands(self) -> None:
        """Set up the default command mappings."""
        # Movement commands
        self.register_command("move_cursor_up", MoveCursorCommand(0, -1))
        self.register_command("move_cursor_down", MoveCursorCommand(0, 1))
        self.register_command("move_cursor_left", MoveCursorCommand(-1, 0))
        self.register_command("move_cursor_right", MoveCursorCommand(1, 0))
        
        # Selection commands
        self.register_command("confirm_selection", ConfirmSelectionCommand())
        self.register_command("cancel_action", CancelActionCommand())
        
        # Overlay commands
        self.register_command("show_objectives", ShowOverlayCommand("objectives"))
        self.register_command("show_help", ShowOverlayCommand("help"))
        self.register_command("show_minimap", ShowOverlayCommand("minimap"))
        self.register_command("show_expanded_log", ShowOverlayCommand("expanded_log"))
        self.register_command("close_overlay", CloseOverlayCommand())
        self.register_command("close_forecast", CloseOverlayCommand())
        
        # Game control commands
        self.register_command("quit_game", QuitGameCommand())
        self.register_command("direct_attack", DirectAttackCommand())
        self.register_command("wait_unit", WaitUnitCommand())
        self.register_command("start_inspect_mode", StartInspectModeCommand())
        self.register_command("close_inspection", CloseInspectionCommand())
        
        # Unit cycling - delegate to handler method
        self.register_action_method("cycle_units")
        self.register_action_method("end_turn")
        
        # Expanded log specific actions
        self.register_action_method("close_log", InputContext.EXPANDED_LOG)
        self.register_action_method("toggle_debug", InputContext.EXPANDED_LOG)
        self.register_action_method("save_log", InputContext.EXPANDED_LOG)
        self.register_action_method("scroll_up", InputContext.EXPANDED_LOG)
        self.register_action_method("scroll_down", InputContext.EXPANDED_LOG)
        
        # Dialog specific actions
        self.register_action_method("dialog_move_left", InputContext.DIALOG)
        self.register_action_method("dialog_move_right", InputContext.DIALOG)
        self.register_action_method("dialog_confirm", InputContext.DIALOG)
        self.register_action_method("dialog_cancel", InputContext.DIALOG)
        
        # Action menu specific actions
        self.register_action_method("menu_move_up", InputContext.ACTION_MENU)
        self.register_action_method("menu_move_down", InputContext.ACTION_MENU)
        self.register_action_method("menu_select", InputContext.ACTION_MENU)
        self.register_action_method("menu_cancel", InputContext.ACTION_MENU)
    
    def create_command_factory(self) -> Callable[[str], Optional[Command]]:
        """
        Create a factory function for commands.
        
        Returns:
            Callable: Factory function that takes action name and returns command
        """
        def factory(action_name: str) -> Optional[Command]:
            return self.get_command(action_name)
        return factory
    
    def register_bulk_actions(self, actions: dict[str, Command], context: Optional[InputContext] = None) -> None:
        """
        Register multiple actions at once.
        
        Args:
            actions: Dictionary of action names to commands
            context: Optional context for all actions
        """
        for action_name, command in actions.items():
            self.register_command(action_name, command, context)
    
    def get_debug_info(self) -> dict[str, Any]:
        """
        Get debug information about registered commands.
        
        Returns:
            Dict: Debug information including command counts and registrations
        """
        return {
            "global_commands": len(self._commands),
            "context_commands": {
                ctx.value: len(commands) 
                for ctx, commands in self._context_commands.items()
            },
            "total_commands": len(self._commands) + sum(
                len(commands) for commands in self._context_commands.values()
            ),
            "global_actions": list(self._commands.keys()),
            "context_actions": {
                ctx.value: list(commands.keys())
                for ctx, commands in self._context_commands.items()
            }
        }