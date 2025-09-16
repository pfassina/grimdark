"""
Configuration loader for key mappings.

This module handles loading and parsing of YAML configuration files
for customizable key bindings.
"""
import os
import yaml
from typing import Optional, Any
from pathlib import Path

from .context_manager import InputContext
from ..input import Key


class KeyConfigLoader:
    """Loads and manages key mapping configurations from YAML files."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "assets/config/key_mappings.yaml"
        self._config: dict[str, Any] = {}
        self._key_mappings: dict[InputContext, dict[Key, str]] = {}
        self._active_scheme: str = "default"
        
    def load_config(self) -> bool:
        """
        Load configuration from the YAML file.
        
        Returns:
            bool: True if config was loaded successfully
        """
        try:
            # Handle both absolute and relative paths
            if not os.path.isabs(self.config_path):
                # Assume relative to project root
                project_root = Path(__file__).parent.parent.parent.parent
                config_file = project_root / self.config_path
            else:
                config_file = Path(self.config_path)
            
            if not config_file.exists():
                print(f"Warning: Key config file not found: {config_file}")
                self._load_fallback_config()
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            
            # Get active scheme from config
            config_section = self._config.get('config', {})
            self._active_scheme = config_section.get('active_scheme', 'default')
            
            # Parse the key mappings
            self._parse_key_mappings()
            
            return True
            
        except Exception as e:
            print(f"Error loading key config: {e}")
            self._load_fallback_config()
            return False
    
    def _parse_key_mappings(self) -> None:
        """Parse the key mappings from the loaded config."""
        self._key_mappings.clear()
        
        contexts_config = self._config.get('contexts', {})
        schemes_config = self._config.get('schemes', {})
        
        for context_name, context_data in contexts_config.items():
            # Convert context name to enum
            try:
                context = InputContext(context_name.lower())
            except ValueError:
                print(f"Warning: Unknown context '{context_name}' in config")
                continue
            
            # Get base mappings
            base_mappings = context_data.get('mappings', {})
            
            # Apply scheme overrides if applicable
            final_mappings = dict(base_mappings)
            if self._active_scheme != 'default' and self._active_scheme in schemes_config:
                scheme = schemes_config[self._active_scheme]
                overrides = scheme.get('overrides', {}).get(context_name, {})
                final_mappings.update(overrides)
            
            # Convert string keys to Key enums
            key_mapping = {}
            for key_str, action in final_mappings.items():
                key = self._parse_key_string(key_str)
                if key:
                    key_mapping[key] = action
            
            self._key_mappings[context] = key_mapping
    
    def _parse_key_string(self, key_str: str) -> Optional[Key]:
        """
        Parse a key string into a Key enum.
        
        Args:
            key_str: String representation of the key
            
        Returns:
            Key: The corresponding Key enum, or None if invalid
        """
        key_str = key_str.upper().strip()
        
        # Handle special cases
        key_map = {
            'HELP': Key.HELP,
            'ESCAPE': Key.ESCAPE,
            'ENTER': Key.ENTER,
            'SPACE': Key.SPACE,
            'TAB': Key.TAB,
            'UP': Key.UP,
            'DOWN': Key.DOWN,
            'LEFT': Key.LEFT,
            'RIGHT': Key.RIGHT
        }
        
        if key_str in key_map:
            return key_map[key_str]
        
        # Try to get from Key enum directly
        try:
            return getattr(Key, key_str)
        except AttributeError:
            print(f"Warning: Unknown key '{key_str}' in config")
            return None
    
    def get_key_mappings(self, context: InputContext) -> dict[Key, str]:
        """
        Get key mappings for a specific context.
        
        Args:
            context: The input context
            
        Returns:
            Dict[Key, str]: Dictionary mapping keys to actions
        """
        return self._key_mappings.get(context, {})
    
    def get_all_key_mappings(self) -> dict[InputContext, dict[Key, str]]:
        """
        Get all key mappings for all contexts.
        
        Returns:
            Dict: All key mappings organized by context
        """
        return dict(self._key_mappings)
    
    def get_action_for_key(self, key: Key, context: InputContext) -> Optional[str]:
        """
        Get the action associated with a key in a specific context.
        
        Args:
            key: The key to check
            context: The input context
            
        Returns:
            str: The action name, or None if not mapped
        """
        context_mappings = self._key_mappings.get(context, {})
        return context_mappings.get(key)
    
    def get_available_schemes(self) -> list[str]:
        """
        Get list of available key schemes.
        
        Returns:
            list[str]: List of scheme names
        """
        schemes = self._config.get('schemes', {})
        return ['default'] + [name for name in schemes.keys() if name != 'default']
    
    def get_active_scheme(self) -> str:
        """
        Get the currently active key scheme.
        
        Returns:
            str: The active scheme name
        """
        return self._active_scheme
    
    def set_active_scheme(self, scheme_name: str) -> bool:
        """
        Set the active key scheme.
        
        Args:
            scheme_name: Name of the scheme to activate
            
        Returns:
            bool: True if scheme was set successfully
        """
        available_schemes = self.get_available_schemes()
        if scheme_name not in available_schemes:
            return False
        
        self._active_scheme = scheme_name
        self._parse_key_mappings()  # Reparse with new scheme
        return True
    
    def get_context_info(self, context: InputContext) -> dict[str, Any]:
        """
        Get information about a context from the config.
        
        Args:
            context: The context to get info for
            
        Returns:
            Dict: Context information (name, description, etc.)
        """
        contexts = self._config.get('contexts', {})
        context_data = contexts.get(context.value, {})
        
        return {
            'name': context_data.get('name', context.value.title()),
            'description': context_data.get('description', ''),
            'key_count': len(self.get_key_mappings(context))
        }
    
    def _load_fallback_config(self) -> None:
        """Load hardcoded fallback configuration if file loading fails."""
        self._key_mappings = {
            InputContext.BATTLEFIELD: {
                Key.UP: "move_cursor_up",
                Key.DOWN: "move_cursor_down",
                Key.LEFT: "move_cursor_left",
                Key.RIGHT: "move_cursor_right",
                Key.ENTER: "confirm_selection",
                Key.SPACE: "confirm_selection",
                Key.ESCAPE: "cancel_action",
                Key.Q: "quit_game",
                Key.A: "direct_attack",
                Key.W: "wait_unit",
                Key.E: "end_turn",
                Key.TAB: "cycle_units",
                Key.O: "show_objectives",
                Key.HELP: "show_help",
                Key.M: "show_minimap",
                Key.L: "show_expanded_log"
            },
            InputContext.EXPANDED_LOG: {
                Key.Q: "close_log",
                Key.D: "toggle_debug",
                Key.S: "save_log",
                Key.UP: "scroll_up",
                Key.DOWN: "scroll_down"
            },
            InputContext.DIALOG: {
                Key.LEFT: "dialog_move_left",
                Key.RIGHT: "dialog_move_right",
                Key.ENTER: "dialog_confirm",
                Key.SPACE: "dialog_confirm",
                Key.ESCAPE: "dialog_cancel"
            },
            InputContext.ACTION_MENU: {
                Key.UP: "menu_move_up",
                Key.DOWN: "menu_move_down",
                Key.ENTER: "menu_select",
                Key.SPACE: "menu_select",
                Key.ESCAPE: "menu_cancel"
            },
            InputContext.FORECAST: {
                Key.ENTER: "close_forecast",
                Key.SPACE: "close_forecast",
                Key.ESCAPE: "close_forecast"
            },
            InputContext.OVERLAY: {
                Key.ENTER: "close_overlay",
                Key.SPACE: "close_overlay", 
                Key.ESCAPE: "close_overlay"
            }
        }
        print("Loaded fallback key configuration")
    
    def reload_config(self) -> bool:
        """
        Reload the configuration from the file.
        
        Returns:
            bool: True if reload was successful
        """
        return self.load_config()
    
    def validate_config(self) -> dict[str, Any]:
        """
        Validate the loaded configuration.
        
        Returns:
            Dict: Validation results including errors and warnings
        """
        errors = []
        warnings = []
        
        # Check for required contexts
        required_contexts = [context.value for context in InputContext]
        contexts = self._config.get('contexts', {})
        
        for required in required_contexts:
            if required not in contexts:
                errors.append(f"Missing required context: {required}")
        
        # Check for unknown contexts
        for context_name in contexts.keys():
            try:
                InputContext(context_name.lower())
            except ValueError:
                warnings.append(f"Unknown context in config: {context_name}")
        
        # Check key mappings
        total_mappings = sum(len(mappings) for mappings in self._key_mappings.values())
        if total_mappings == 0:
            errors.append("No valid key mappings found")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'contexts': len(self._key_mappings),
            'total_mappings': total_mappings,
            'active_scheme': self._active_scheme
        }