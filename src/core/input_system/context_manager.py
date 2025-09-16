"""
Input context management system.

This module handles the context stack and determines which input context
is currently active based on game state.
"""
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...core.game_state import GameState


class InputContext(Enum):
    """Input context defines which keys are active and what they do."""
    BATTLEFIELD = "battlefield"
    EXPANDED_LOG = "expanded_log"
    DIALOG = "dialog"
    MENU = "menu"
    ACTION_MENU = "action_menu"
    FORECAST = "forecast"
    OVERLAY = "overlay"


class InputContextManager:
    """Manages input contexts and determines the active context."""
    
    def __init__(self, game_state: "GameState"):
        self.state = game_state
        self._context_stack: list[InputContext] = [InputContext.BATTLEFIELD]
    
    def get_current_context(self) -> InputContext:
        """
        Determine the current input context based on game state.
        
        Returns:
            InputContext: The currently active input context
        """
        # Check if state exists and has UI
        if not self.state or not hasattr(self.state, 'ui'):
            return InputContext.BATTLEFIELD
        
        # Check UI state to determine context (priority order matters)
        # Dialog has highest priority - must be handled when open
        if self.state.ui.is_dialog_open():
            return InputContext.DIALOG
        elif self.state.ui.is_expanded_log_open():
            return InputContext.EXPANDED_LOG
        elif self.state.ui.is_forecast_active():
            return InputContext.FORECAST
        elif self.state.ui.is_action_menu_open():
            return InputContext.ACTION_MENU
        elif self.state.ui.is_overlay_open():
            return InputContext.OVERLAY
        elif self.state.ui.is_menu_open():
            return InputContext.MENU
        else:
            return InputContext.BATTLEFIELD
    
    def push_context(self, context: InputContext) -> None:
        """
        Push a new context onto the stack.
        
        Args:
            context: The context to push
        """
        self._context_stack.append(context)
    
    def pop_context(self) -> Optional[InputContext]:
        """
        Pop the top context from the stack.
        
        Returns:
            InputContext: The popped context, or None if stack would be empty
        """
        if len(self._context_stack) > 1:  # Always keep at least one context
            return self._context_stack.pop()
        return None
    
    def peek_context(self) -> InputContext:
        """
        Get the top context without removing it.
        
        Returns:
            InputContext: The current top context
        """
        return self._context_stack[-1] if self._context_stack else InputContext.BATTLEFIELD
    
    def clear_context_stack(self) -> None:
        """Reset the context stack to the default battlefield context."""
        self._context_stack = [InputContext.BATTLEFIELD]
    
    def is_in_context(self, context: InputContext) -> bool:
        """
        Check if the specified context is in the stack.
        
        Args:
            context: The context to check for
            
        Returns:
            bool: True if context is in the stack
        """
        return context in self._context_stack
    
    def get_context_priority(self, context: InputContext) -> int:
        """
        Get the priority level of a context (higher = more important).
        
        Args:
            context: The context to check
            
        Returns:
            int: Priority level (0-10, with 10 being highest priority)
        """
        priority_map = {
            InputContext.DIALOG: 10,        # Highest - blocks all other input
            InputContext.FORECAST: 9,       # Combat forecasts
            InputContext.EXPANDED_LOG: 8,   # Full-screen log viewer
            InputContext.ACTION_MENU: 7,    # Action selection menus
            InputContext.OVERLAY: 6,        # Information overlays
            InputContext.MENU: 5,           # General menus
            InputContext.BATTLEFIELD: 1     # Default/lowest priority
        }
        return priority_map.get(context, 0)
    
    def should_handle_in_context(self, context: InputContext) -> bool:
        """
        Check if input should be handled in the specified context.
        
        Args:
            context: The context to check
            
        Returns:
            bool: True if input should be handled in this context
        """
        current = self.get_current_context()
        
        # Handle input if we're in the exact context
        if current == context:
            return True
        
        # Special cases for contexts that allow certain keys from other contexts
        if current == InputContext.BATTLEFIELD:
            # Battlefield allows overlay shortcuts even during other phases
            return context in [InputContext.OVERLAY, InputContext.EXPANDED_LOG]
        
        return False
    
    def get_context_name(self, context: InputContext) -> str:
        """
        Get a human-readable name for the context.
        
        Args:
            context: The context to get the name for
            
        Returns:
            str: Human-readable context name
        """
        name_map = {
            InputContext.BATTLEFIELD: "Battlefield",
            InputContext.EXPANDED_LOG: "Expanded Log",
            InputContext.DIALOG: "Dialog",
            InputContext.MENU: "Menu",
            InputContext.ACTION_MENU: "Action Menu",
            InputContext.FORECAST: "Battle Forecast",
            InputContext.OVERLAY: "Information Overlay"
        }
        return name_map.get(context, context.value.title())
    
    def validate_context_transition(self, from_context: InputContext, to_context: InputContext) -> bool:
        """
        Validate if a context transition is allowed.
        
        Args:
            from_context: The source context
            to_context: The destination context
            
        Returns:
            bool: True if transition is valid
        """
        # Some contexts can't be interrupted
        if from_context == InputContext.DIALOG and to_context != InputContext.BATTLEFIELD:
            return False
        
        # All other transitions are generally allowed
        return True