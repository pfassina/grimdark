"""Game state management with structured substates.

This module defines the top-level :class:`GameState` along with more focused
dataclasses for battle logic, UI/dialog handling and cursor/camera tracking.
Splitting the state into these components makes intent clearer and keeps
related behaviour together while still exposing a unified interface through
``GameState`` for backwards compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from .data_structures import Vector2, VectorArray


class GamePhase(Enum):
    """High level game phases."""

    MAIN_MENU = auto()
    BATTLE = auto()
    CUTSCENE = auto()
    PAUSE = auto()
    GAME_OVER = auto()


class BattlePhase(Enum):
    """Phases within a battle."""

    PLAYER_TURN_START = auto()
    UNIT_SELECTION = auto()
    UNIT_MOVING = auto()
    ACTION_MENU = auto()
    TARGETING = auto()  # Target selection with battle forecast
    UNIT_ACTING = auto()
    ENEMY_TURN = auto()
    TURN_END = auto()


@dataclass
class CursorState:
    """Tracks cursor position and camera viewport."""

    position: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    camera_position: Vector2 = field(default_factory=lambda: Vector2(0, 0))

    def set_position(self, position: Vector2) -> None:
        self.position = position

    def move(self, dx: int, dy: int, max_x: int, max_y: int) -> None:
        """Move cursor within the bounds of the map."""

        new_x = max(0, min(max_x - 1, self.position.x + dx))
        new_y = max(0, min(max_y - 1, self.position.y + dy))
        self.position = Vector2(new_y, new_x)

    def update_camera(self, viewport_width: int, viewport_height: int) -> None:
        """Keep the camera near the cursor with a margin."""

        margin = 3

        if self.position.x < self.camera_position.x + margin:
            self.camera_position = Vector2(
                self.camera_position.y, max(0, self.position.x - margin)
            )
        elif self.position.x >= self.camera_position.x + viewport_width - margin:
            self.camera_position = Vector2(
                self.camera_position.y,
                self.position.x - viewport_width + margin + 1,
            )

        if self.position.y < self.camera_position.y + margin:
            self.camera_position = Vector2(
                max(0, self.position.y - margin), self.camera_position.x
            )
        elif self.position.y >= self.camera_position.y + viewport_height - margin:
            self.camera_position = Vector2(
                self.position.y - viewport_height + margin + 1,
                self.camera_position.x,
            )


@dataclass
class UIState:
    """Holds menu, dialog and overlay UI state."""

    active_menu: Optional[str] = None
    menu_selection: int = 0

    active_action_menu: bool = False
    action_menu_items: list[str] = field(default_factory=list)
    action_menu_selection: int = 0

    active_overlay: Optional[str] = None  # "objectives", "help", "minimap"
    active_dialog: Optional[str] = None  # "confirm_end_turn", etc.
    dialog_selection: int = 0  # For dialog option selection
    active_forecast: bool = False  # Battle forecast during targeting

    def open_menu(self, menu_name: str) -> None:
        self.active_menu = menu_name
        self.menu_selection = 0

    def close_menu(self) -> None:
        self.active_menu = None
        self.menu_selection = 0

    def is_menu_open(self) -> bool:
        return self.active_menu is not None

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
        if self.active_action_menu and 0 <= self.action_menu_selection < len(
            self.action_menu_items
        ):
            return self.action_menu_items[self.action_menu_selection]
        return None

    def move_action_menu_selection(self, direction: int) -> None:
        if self.active_action_menu and self.action_menu_items:
            self.action_menu_selection = (
                self.action_menu_selection + direction
            ) % len(self.action_menu_items)

    # Strategic TUI overlay methods
    def open_overlay(self, overlay_type: str) -> None:
        self.active_overlay = overlay_type

    def close_overlay(self) -> None:
        self.active_overlay = None

    def is_overlay_open(self) -> bool:
        return self.active_overlay is not None

    def open_dialog(self, dialog_type: str) -> None:
        self.active_dialog = dialog_type
        self.dialog_selection = 0

    def close_dialog(self) -> None:
        self.active_dialog = None
        self.dialog_selection = 0

    def is_dialog_open(self) -> bool:
        return self.active_dialog is not None

    def move_dialog_selection(self, direction: int) -> None:
        self.dialog_selection = (self.dialog_selection + direction) % 2

    def get_dialog_selection(self) -> int:
        return self.dialog_selection

    def start_forecast(self) -> None:
        self.active_forecast = True

    def stop_forecast(self) -> None:
        self.active_forecast = False

    def is_forecast_active(self) -> bool:
        return self.active_forecast

    def is_any_modal_open(self) -> bool:
        return (
            self.is_overlay_open()
            or self.is_dialog_open()
            or self.is_forecast_active()
        )


@dataclass
class BattleState:
    """Encapsulates battle-specific state and behaviour."""

    phase: BattlePhase = BattlePhase.UNIT_SELECTION

    current_turn: int = 1
    current_team: int = 0

    selected_unit_id: Optional[str] = None
    selected_tile_position: Optional[Vector2] = None
    original_unit_position: Optional[Vector2] = None

    movement_range: VectorArray = field(default_factory=VectorArray)
    attack_range: VectorArray = field(default_factory=VectorArray)

    selected_target: Optional[Vector2] = None
    aoe_tiles: VectorArray = field(default_factory=VectorArray)

    selectable_units: list[str] = field(default_factory=list)
    current_unit_index: int = 0

    targetable_enemies: list[str] = field(default_factory=list)
    current_target_index: int = 0

    def reset_selection(self) -> None:
        self.selected_unit_id = None
        self.selected_tile_position = None
        self.original_unit_position = None
        self.movement_range = VectorArray()
        self.attack_range = VectorArray()
        self.selected_target = None
        self.aoe_tiles = VectorArray()
        self.selectable_units.clear()
        self.current_unit_index = 0
        self.targetable_enemies.clear()
        self.current_target_index = 0

    def set_movement_range(self, tiles: VectorArray) -> None:
        self.movement_range = tiles

    def set_attack_range(self, tiles: VectorArray) -> None:
        self.attack_range = tiles

    def is_in_movement_range(self, position: Vector2) -> bool:
        return self.movement_range.contains(position)

    def is_in_attack_range(self, position: Vector2) -> bool:
        return self.attack_range.contains(position)

    def start_player_turn(self) -> None:
        self.phase = BattlePhase.PLAYER_TURN_START
        self.current_turn += 1
        self.reset_selection()

    def start_enemy_turn(self) -> None:
        self.phase = BattlePhase.ENEMY_TURN
        self.reset_selection()

    def set_selectable_units(self, unit_ids: list[str]) -> None:
        self.selectable_units = unit_ids.copy()
        self.current_unit_index = 0

    def cycle_selectable_units(self) -> Optional[str]:
        if not self.selectable_units:
            return None
        self.current_unit_index = (self.current_unit_index + 1) % len(
            self.selectable_units
        )
        return self.selectable_units[self.current_unit_index]

    def get_current_selectable_unit(self) -> Optional[str]:
        if not self.selectable_units or self.current_unit_index >= len(
            self.selectable_units
        ):
            return None
        return self.selectable_units[self.current_unit_index]

    def set_targetable_enemies(self, unit_ids: list[str]) -> None:
        self.targetable_enemies = unit_ids.copy()
        self.current_target_index = 0

    def cycle_targetable_enemies(self) -> Optional[str]:
        if not self.targetable_enemies:
            return None
        self.current_target_index = (self.current_target_index + 1) % len(
            self.targetable_enemies
        )
        return self.targetable_enemies[self.current_target_index]

    def get_current_targetable_enemy(self) -> Optional[str]:
        if not self.targetable_enemies or self.current_target_index >= len(
            self.targetable_enemies
        ):
            return None
        return self.targetable_enemies[self.current_target_index]


@dataclass
class GameState:
    """Top-level game state composed of focused substates."""

    phase: GamePhase = GamePhase.BATTLE
    battle: BattleState = field(default_factory=BattleState)
    ui: UIState = field(default_factory=UIState)
    cursor: CursorState = field(default_factory=CursorState)

    state_data: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience methods operating across substates
    # ------------------------------------------------------------------
    def reset_selection(self) -> None:
        """Reset selection state and close any active UI elements."""

        self.battle.reset_selection()
        self.ui.close_action_menu()
        self.ui.close_overlay()
        self.ui.close_dialog()
        self.ui.stop_forecast()

    def start_player_turn(self) -> None:
        self.battle.start_player_turn()

    def start_enemy_turn(self) -> None:
        self.battle.start_enemy_turn()

    def move_cursor(self, dx: int, dy: int, max_x: int, max_y: int) -> None:
        self.cursor.move(dx, dy, max_x, max_y)

    def set_cursor_position(self, position: Vector2) -> None:
        self.cursor.set_position(position)

    def update_camera_to_cursor(self, viewport_width: int, viewport_height: int) -> None:
        self.cursor.update_camera(viewport_width, viewport_height)

