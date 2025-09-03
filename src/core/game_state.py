from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Any


class GamePhase(Enum):
    MAIN_MENU = auto()
    BATTLE = auto()
    CUTSCENE = auto()
    PAUSE = auto()
    GAME_OVER = auto()


class BattlePhase(Enum):
    PLAYER_TURN_START = auto()
    UNIT_SELECTION = auto()
    UNIT_MOVING = auto()
    ACTION_MENU = auto()
    TARGETING = auto()  # New phase for target selection with battle forecast
    UNIT_ACTING = auto()
    ENEMY_TURN = auto()
    TURN_END = auto()


@dataclass
class GameState:
    phase: GamePhase = GamePhase.BATTLE
    battle_phase: BattlePhase = BattlePhase.UNIT_SELECTION
    
    current_turn: int = 1
    current_team: int = 0
    
    selected_unit_id: Optional[str] = None
    selected_tile_x: Optional[int] = None
    selected_tile_y: Optional[int] = None
    
    # Original position tracking for cancellation
    original_unit_x: Optional[int] = None
    original_unit_y: Optional[int] = None
    
    cursor_x: int = 0
    cursor_y: int = 0
    
    camera_x: int = 0
    camera_y: int = 0
    
    active_menu: Optional[str] = None
    menu_selection: int = 0
    
    # Action menu state
    active_action_menu: bool = False
    action_menu_items: list[str] = field(default_factory=list)
    action_menu_selection: int = 0
    
    # Strategic TUI overlay states
    active_overlay: Optional[str] = None  # "objectives", "help", "minimap"
    active_dialog: Optional[str] = None   # "confirm_end_turn", etc.
    dialog_selection: int = 0             # For dialog option selection
    active_forecast: bool = False         # Battle forecast during targeting
    
    movement_range: list[tuple] = field(default_factory=list)
    attack_range: list[tuple] = field(default_factory=list)
    
    # Attack targeting state
    selected_target: Optional[tuple[int, int]] = None
    aoe_tiles: list[tuple[int, int]] = field(default_factory=list)
    
    # Unit cycling state
    selectable_units: list[str] = field(default_factory=list)
    current_unit_index: int = 0
    
    # Target cycling state  
    targetable_enemies: list[str] = field(default_factory=list)
    current_target_index: int = 0
    
    state_data: dict[str, Any] = field(default_factory=dict)
    
    def reset_selection(self) -> None:
        self.selected_unit_id = None
        self.selected_tile_x = None
        self.selected_tile_y = None
        self.original_unit_x = None
        self.original_unit_y = None
        self.movement_range.clear()
        self.attack_range.clear()
        self.selected_target = None
        self.aoe_tiles.clear()
        self.selectable_units.clear()
        self.current_unit_index = 0
        self.targetable_enemies.clear()
        self.current_target_index = 0
        self.close_action_menu()
        self.close_overlay()
        self.close_dialog()
        self.stop_forecast()
    
    def set_cursor_position(self, x: int, y: int) -> None:
        self.cursor_x = x
        self.cursor_y = y
    
    def move_cursor(self, dx: int, dy: int, max_x: int, max_y: int) -> None:
        self.cursor_x = max(0, min(max_x - 1, self.cursor_x + dx))
        self.cursor_y = max(0, min(max_y - 1, self.cursor_y + dy))
    
    def set_movement_range(self, tiles: list[tuple]) -> None:
        self.movement_range = tiles
    
    def set_attack_range(self, tiles: list[tuple]) -> None:
        self.attack_range = tiles
    
    def is_in_movement_range(self, x: int, y: int) -> bool:
        return (x, y) in self.movement_range
    
    def is_in_attack_range(self, x: int, y: int) -> bool:
        return (x, y) in self.attack_range
    
    def start_player_turn(self) -> None:
        self.battle_phase = BattlePhase.PLAYER_TURN_START
        self.current_turn += 1
        self.reset_selection()
    
    def start_enemy_turn(self) -> None:
        self.battle_phase = BattlePhase.ENEMY_TURN
        self.reset_selection()
    
    def open_menu(self, menu_name: str) -> None:
        self.active_menu = menu_name
        self.menu_selection = 0
    
    def close_menu(self) -> None:
        self.active_menu = None
        self.menu_selection = 0
    
    def is_menu_open(self) -> bool:
        return self.active_menu is not None
    
    # Action menu methods
    def open_action_menu(self, items: list[str]) -> None:
        self.active_action_menu = True
        self.action_menu_items = items.copy()
        self.action_menu_selection = 0
    
    def close_action_menu(self) -> None:
        self.active_action_menu = False
        self.action_menu_items.clear()
        self.action_menu_selection = 0
    
    def is_action_menu_open(self) -> bool:
        return self.active_action_menu
    
    def get_selected_action(self) -> Optional[str]:
        if self.active_action_menu and 0 <= self.action_menu_selection < len(self.action_menu_items):
            return self.action_menu_items[self.action_menu_selection]
        return None
    
    def move_action_menu_selection(self, direction: int) -> None:
        if self.active_action_menu and self.action_menu_items:
            self.action_menu_selection = (self.action_menu_selection + direction) % len(self.action_menu_items)
    
    # Strategic TUI overlay methods
    def open_overlay(self, overlay_type: str) -> None:
        """Open a full-screen overlay (objectives, help, minimap)."""
        self.active_overlay = overlay_type
    
    def close_overlay(self) -> None:
        """Close the active overlay."""
        self.active_overlay = None
    
    def is_overlay_open(self) -> bool:
        """Check if any overlay is open."""
        return self.active_overlay is not None
    
    def open_dialog(self, dialog_type: str) -> None:
        """Open a confirmation dialog."""
        self.active_dialog = dialog_type
        self.dialog_selection = 0
    
    def close_dialog(self) -> None:
        """Close the active dialog."""
        self.active_dialog = None
        self.dialog_selection = 0
    
    def is_dialog_open(self) -> bool:
        """Check if any dialog is open."""
        return self.active_dialog is not None
    
    def move_dialog_selection(self, direction: int) -> None:
        """Move dialog selection (0=Yes, 1=No typically)."""
        self.dialog_selection = (self.dialog_selection + direction) % 2
    
    def get_dialog_selection(self) -> int:
        """Get current dialog selection."""
        return self.dialog_selection
    
    def start_forecast(self) -> None:
        """Start battle forecast display."""
        self.active_forecast = True
    
    def stop_forecast(self) -> None:
        """Stop battle forecast display."""
        self.active_forecast = False
    
    def is_forecast_active(self) -> bool:
        """Check if battle forecast is active."""
        return self.active_forecast
    
    def is_any_modal_open(self) -> bool:
        """Check if any modal UI is open (overlay, dialog, forecast)."""
        return self.is_overlay_open() or self.is_dialog_open() or self.is_forecast_active()
    
    def update_camera_to_cursor(self, viewport_width: int, viewport_height: int) -> None:
        margin = 3
        
        if self.cursor_x < self.camera_x + margin:
            self.camera_x = max(0, self.cursor_x - margin)
        elif self.cursor_x >= self.camera_x + viewport_width - margin:
            self.camera_x = self.cursor_x - viewport_width + margin + 1
        
        if self.cursor_y < self.camera_y + margin:
            self.camera_y = max(0, self.cursor_y - margin)
        elif self.cursor_y >= self.camera_y + viewport_height - margin:
            self.camera_y = self.cursor_y - viewport_height + margin + 1
    
    def set_selectable_units(self, unit_ids: list[str]) -> None:
        """Set the list of units that can be selected and reset index."""
        self.selectable_units = unit_ids.copy()
        self.current_unit_index = 0
    
    def cycle_selectable_units(self) -> Optional[str]:
        """Cycle to the next selectable unit and return its ID."""
        if not self.selectable_units:
            return None
        
        self.current_unit_index = (self.current_unit_index + 1) % len(self.selectable_units)
        return self.selectable_units[self.current_unit_index]
    
    def get_current_selectable_unit(self) -> Optional[str]:
        """Get the currently selected unit ID."""
        if not self.selectable_units or self.current_unit_index >= len(self.selectable_units):
            return None
        return self.selectable_units[self.current_unit_index]
    
    def set_targetable_enemies(self, unit_ids: list[str]) -> None:
        """Set the list of enemies that can be targeted and reset index."""
        self.targetable_enemies = unit_ids.copy()
        self.current_target_index = 0
    
    def cycle_targetable_enemies(self) -> Optional[str]:
        """Cycle to the next targetable enemy and return its ID."""
        if not self.targetable_enemies:
            return None
        
        self.current_target_index = (self.current_target_index + 1) % len(self.targetable_enemies)
        return self.targetable_enemies[self.current_target_index]
    
    def get_current_targetable_enemy(self) -> Optional[str]:
        """Get the currently targeted enemy ID."""
        if not self.targetable_enemies or self.current_target_index >= len(self.targetable_enemies):
            return None
        return self.targetable_enemies[self.current_target_index]