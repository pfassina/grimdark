"""
Render context building system for converting game state to renderable data.

This module handles the conversion from game state to render contexts
that can be consumed by any renderer implementation.
"""
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .map import GameMap
    from .scenario_menu import ScenarioMenu
    from ..core.game_state import GameState
    from ..core.renderer import Renderer

from ..core.data_structures import DataConverter, Vector2
from ..core.game_state import GamePhase
from ..core.renderable import (
    AttackTargetRenderData,
    CursorRenderData,
    MenuRenderData,
    OverlayTileRenderData,
    RenderContext,
    TextRenderData,
    TileRenderData,
)


class RenderBuilder:
    """Builds render contexts from game state data."""
    
    def __init__(
        self,
        game_map: "GameMap",
        game_state: "GameState",
        renderer: "Renderer",
        scenario_menu: Optional["ScenarioMenu"] = None,
        ui_manager=None
    ):
        self.game_map = game_map
        self.state = game_state
        self.renderer = renderer
        self.scenario_menu = scenario_menu
        self.ui_manager = ui_manager
        
        # Timing system for animations
        self.game_start_time = time.time()
        self.cursor_blink_interval = 0.5  # 2Hz blinking
    
    def set_scenario_menu(self, scenario_menu: "ScenarioMenu") -> None:
        """Update the scenario menu reference."""
        self.scenario_menu = scenario_menu
    
    def set_ui_manager(self, ui_manager) -> None:
        """Update the UI manager reference."""
        self.ui_manager = ui_manager
    
    def build_render_context(self) -> RenderContext:
        """Build complete render context from current game state."""
        context = RenderContext()
        
        screen_width, screen_height = self.renderer.get_screen_size()
        viewport_height = screen_height - 3
        
        # Handle main menu rendering
        if self.state.phase == GamePhase.MAIN_MENU:
            return self._build_main_menu_context(screen_width, screen_height)
        
        # Update camera to follow cursor
        self.state.update_camera_to_cursor(screen_width, viewport_height)
        
        # Set viewport information
        context.viewport_x = self.state.camera_position.x
        context.viewport_y = self.state.camera_position.y
        context.viewport_width = screen_width
        context.viewport_height = viewport_height
        
        context.world_width = self.game_map.width
        context.world_height = self.game_map.height
        
        # Add game state information
        context.current_turn = self.state.current_turn
        context.current_team = self.state.current_team
        
        # Set timing for animations (convert to milliseconds)
        context.current_time_ms = int((time.time() - self.game_start_time) * 1000)
        
        # Build tile data
        self._add_tiles_to_context(context)
        
        # Add movement range overlay
        self._add_movement_overlays(context)
        
        # Add attack targeting overlays
        self._add_attack_targeting(context)
        
        # Add unit data with highlighting
        self._add_units_to_context(context)
        
        # Add cursor
        self._add_cursor_to_context(context)
        
        # Add action menu if active
        self._add_action_menu(context, screen_width, screen_height)
        
        # Add status text
        self._add_status_text(context, screen_width, screen_height)
        
        # Add UI elements if managers are available
        self._add_ui_elements(context)
        
        return context
    
    def _build_main_menu_context(
        self, screen_width: int, screen_height: int
    ) -> RenderContext:
        """Build render context for the main menu."""
        context = RenderContext()
        context.viewport_width = screen_width
        context.viewport_height = screen_height
        
        if not self.scenario_menu:
            return context
        
        # Create menu data - allow wider menus for better formatting
        menu_width = min(90, screen_width - 4)
        self.scenario_menu.update_display_items(menu_width)
        menu_items = self.scenario_menu.display_items
        menu_height = min(len(menu_items) + 4, screen_height - 6)
        
        menu_x = (screen_width - menu_width) // 2
        menu_y = (screen_height - menu_height) // 2
        
        context.menus.append(
            MenuRenderData(
                x=menu_x,
                y=menu_y,
                width=menu_width,
                height=menu_height,
                title="Select Scenario",
                items=menu_items,
                selected_index=self.scenario_menu.selected_display_line,
            )
        )
        
        # Add instructions
        instructions = "[↑↓/WS] Navigate [Enter/Z] Select [Q] Quit"
        context.texts.append(
            TextRenderData(x=0, y=screen_height - 1, text=instructions[:screen_width])
        )
        
        return context
    
    def _add_tiles_to_context(self, context: RenderContext) -> None:
        """Add tile data to the render context using vectorized operations."""
        self._add_tiles_to_context_vectorized(context)
    
    def _add_tiles_to_context_vectorized(self, context: RenderContext) -> None:
        """Vectorized implementation of tile data generation.
        
        Creates all tile render data at once using numpy operations
        instead of nested loops for significant performance improvement.
        """
        import numpy as np
        from ..core.game_enums import TerrainType
        
        # Get structured tile data from game map
        terrain_types = self.game_map.tiles['terrain_type']
        elevations = self.game_map.tiles['elevation']
        height, width = self.game_map.height, self.game_map.width
        
        # Create coordinate meshgrid
        y_coords, x_coords = np.mgrid[0:height, 0:width]
        
        # Flatten all arrays for vectorized processing
        y_flat = y_coords.flatten()
        x_flat = x_coords.flatten()
        terrain_flat = terrain_types.flatten()
        elevation_flat = elevations.flatten()
        
        # Convert terrain type integers to string names
        terrain_names = np.empty(len(terrain_flat), dtype=object)
        for terrain_type in TerrainType:
            mask = terrain_flat == terrain_type.value
            terrain_names[mask] = terrain_type.name.lower()
        
        # Create TileRenderData objects efficiently
        for i in range(len(y_flat)):
            position = Vector2(int(y_flat[i]), int(x_flat[i]))
            context.tiles.append(
                TileRenderData(
                    position=position,
                    terrain_type=terrain_names[i],
                    elevation=int(elevation_flat[i]),
                )
            )
    
    def _add_movement_overlays(self, context: RenderContext) -> None:
        """Add movement range overlay tiles."""
        for pos in self.state.movement_range:
            context.overlays.append(
                OverlayTileRenderData(
                    position=pos, overlay_type="movement", opacity=0.5
                )
            )
    
    def _add_attack_targeting(self, context: RenderContext) -> None:
        """Add attack targeting overlays."""
        # Calculate blink phase for animation (500ms cycle)
        blink_phase = (context.current_time_ms // 500) % 2 == 1
        
        # Add all attack range tiles first
        for pos in self.state.attack_range:
            # Skip if this position will be handled as AOE or selected
            if not self.state.aoe_tiles.contains(pos) and pos != self.state.selected_target:
                context.attack_targets.append(
                    AttackTargetRenderData(
                        position=pos, target_type="range", blink_phase=blink_phase
                    )
                )
        
        # Add AOE tiles (including those outside attack range)
        for pos in self.state.aoe_tiles:
            if pos == self.state.selected_target:
                # Selected tile gets special treatment
                context.attack_targets.append(
                    AttackTargetRenderData(
                        position=pos,
                        target_type="selected",
                        blink_phase=blink_phase,
                    )
                )
            else:
                # Other AOE tiles
                context.attack_targets.append(
                    AttackTargetRenderData(
                        position=pos, target_type="aoe", blink_phase=blink_phase
                    )
                )
    
    def _add_units_to_context(self, context: RenderContext) -> None:
        """Add unit data to the render context with highlighting."""
        def highlight_units(unit):
            """Determine highlight type for units."""
            from ..core.game_state import BattlePhase
            
            if (
                self.state.battle_phase == BattlePhase.UNIT_ACTING
                and self.state.targetable_enemies
                and unit.unit_id in self.state.targetable_enemies
            ):
                return "target"
            return None
        
        context.units.extend(
            DataConverter.units_to_render_data_list(self.game_map.units, highlight_units)
        )
    
    def _add_cursor_to_context(self, context: RenderContext) -> None:
        """Add cursor to the render context."""
        # Always set cursor position (for panels to read)
        context.cursor_x = self.state.cursor_position.x
        context.cursor_y = self.state.cursor_position.y
        
        # Add cursor with blinking effect (only visible when blinking on)
        if self._is_cursor_visible():
            context.cursor = CursorRenderData(
                position=self.state.cursor_position, cursor_type="default"
            )
    
    def _add_action_menu(
        self, context: RenderContext, screen_width: int, _screen_height: int
    ) -> None:
        """Add action menu if active."""
        if not self.state.is_action_menu_open():
            return
        
        # Position the action menu in the sidebar area
        sidebar_width = 28 if screen_width >= 90 else 24
        menu_x = screen_width - sidebar_width + 1
        
        # Position will be handled by sidebar renderer - just provide the menu data
        # The sidebar renderer will calculate proper positioning based on actual panel heights
        menu_width = sidebar_width - 2
        menu_height = (
            len(self.state.action_menu_items) + 3
        )  # +3 for title and borders
        
        # Set a placeholder position - sidebar renderer will reposition it properly
        menu_y = 0
        
        context.menus.append(
            MenuRenderData(
                x=menu_x,
                y=menu_y,
                width=menu_width,
                height=menu_height,
                title="Actions",
                items=self.state.action_menu_items,
                selected_index=self.state.action_menu_selection,
            )
        )
    
    def _add_status_text(
        self, context: RenderContext, _screen_width: int, screen_height: int
    ) -> None:
        """Add status bar text."""
        status_text = f"Turn {self.state.current_turn} | "
        status_text += f"Phase: {self.state.battle_phase.name} | "
        status_text += f"Cursor: ({self.state.cursor_position.x}, {self.state.cursor_position.y}) | "
        status_text += "[Q]uit [Z]Confirm [X]Cancel"
        
        context.texts.append(
            TextRenderData(x=0, y=screen_height - 1, text=status_text)
        )
    
    def _add_ui_elements(self, context: RenderContext) -> None:
        """Add UI elements from UI manager if available."""
        if not self.ui_manager:
            return
        
        # Add strategic TUI overlays if active
        if self.state.is_overlay_open():
            if self.state.active_overlay == "objectives":
                context.overlay = self.ui_manager.build_objectives_overlay()
            elif self.state.active_overlay == "help":
                context.overlay = self.ui_manager.build_help_overlay()
            elif self.state.active_overlay == "minimap":
                context.overlay = self.ui_manager.build_minimap_overlay()
        
        # Add dialog if active
        if self.state.is_dialog_open() and self.state.active_dialog is not None:
            context.dialog = self.ui_manager.build_dialog(self.state.active_dialog)
        
        # Add battle forecast if active
        if self.state.is_forecast_active():
            context.battle_forecast = self.ui_manager.build_battle_forecast()
        
        # Add banner if active
        banner = self.ui_manager.build_banner()
        if banner:
            context.banner = banner
    
    def _is_cursor_visible(self) -> bool:
        """Check if cursor should be visible (2Hz blinking)."""
        elapsed_time = time.time() - self.game_start_time
        # Calculate which blink cycle we're in
        cycle_position = elapsed_time % (self.cursor_blink_interval * 2)
        # Cursor is visible during the first half of each cycle
        return cycle_position < self.cursor_blink_interval