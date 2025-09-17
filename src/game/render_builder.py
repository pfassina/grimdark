"""
Render context building system for converting game state to renderable data.

This module handles the conversion from game state to render contexts
that can be consumed by any renderer implementation.
"""
import time
from typing import TYPE_CHECKING, Optional

import numpy as np

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
    LogPanelRenderData,
    MenuRenderData,
    OverlayTileRenderData,
    RenderContext,
    TextRenderData,
    TileRenderData,
    TimelineRenderData,
    TimelineEntryRenderData,
)


class RenderBuilder:
    """Builds render contexts from game state data."""
    
    def __init__(
        self,
        game_map: Optional["GameMap"],
        game_state: "GameState",
        renderer: "Renderer",
        scenario_menu: Optional["ScenarioMenu"] = None,
        ui_manager=None,
        log_manager=None
    ):
        self.game_map = game_map
        self.state = game_state
        self.renderer = renderer
        self.scenario_menu = scenario_menu
        self.ui_manager = ui_manager
        self.log_manager = log_manager
        
        # Timing system for animations
        self.game_start_time = time.time()
        self.cursor_blink_interval = 0.5  # 2Hz blinking
    
    def set_scenario_menu(self, scenario_menu: "ScenarioMenu") -> None:
        """Update the scenario menu reference."""
        self.scenario_menu = scenario_menu
    
    def set_ui_manager(self, ui_manager) -> None:
        """Update the UI manager reference."""
        self.ui_manager = ui_manager
    
    def _ensure_game_map(self) -> "GameMap":
        """Ensure game_map is initialized, raise error if not."""
        if self.game_map is None:
            raise RuntimeError("Game map not initialized. Render builder requires game map for battle rendering.")
        return self.game_map
    
    def build_render_context(self) -> RenderContext:
        """Build complete render context from current game state."""
        context = RenderContext()
        
        screen_width, screen_height = self.renderer.get_screen_size()
        viewport_height = screen_height - 3
        
        # Handle main menu rendering
        if self.state.phase == GamePhase.MAIN_MENU:
            return self._build_main_menu_context(screen_width, screen_height)
        
        # Ensure we have a game map for game rendering
        if self.game_map is None:
            raise RuntimeError("Cannot render game content without a game map")
        
        # Update camera to follow cursor
        self.state.update_camera_to_cursor(screen_width, viewport_height)

        # Set viewport information
        context.viewport_x = self.state.cursor.camera_position.x
        context.viewport_y = self.state.cursor.camera_position.y
        context.viewport_width = screen_width
        context.viewport_height = viewport_height
        
        game_map = self._ensure_game_map()
        context.world_width = game_map.width
        context.world_height = game_map.height
        
        # Add game state information
        context.current_turn = self.state.battle.current_turn
        context.current_team = self.state.battle.current_team
        context.game_phase = self.state.phase.name
        context.battle_phase = self.state.battle.phase.name if self.state.battle else None
        
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
        
        # Add hazards to render context
        self._add_hazards_to_context(context)
        
        # Add timeline visualization
        self._add_timeline_to_context(context)
        
        # Add cursor
        self._add_cursor_to_context(context)
        
        # Add action menu if active
        self._add_action_menu(context, screen_width, screen_height)
        
        # Add status text
        self._add_status_text(context, screen_width, screen_height)
        
        # Add UI elements if managers are available
        self._add_ui_elements(context)
        
        # Add new 4-panel UI data
        self._add_unit_info_panel(context, screen_width, screen_height)
        self._add_action_menu_panel(context, screen_width, screen_height)
        
        # Add log panel
        self._add_log_panel(context, screen_width, screen_height)
        
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
        from ..core.game_enums import TerrainType
        
        # Get structured tile data from game map
        game_map = self._ensure_game_map()
        terrain_types = game_map.tiles['terrain_type']
        elevations = game_map.tiles['elevation']
        height, width = game_map.height, game_map.width
        
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
        """Add movement range overlay tiles with terrain preservation."""
        game_map = self._ensure_game_map()
        for pos in self.state.battle.movement_range:
            # Get underlying terrain information
            tile = game_map.get_tile(pos)
            
            context.overlays.append(
                OverlayTileRenderData(
                    position=pos, 
                    overlay_type="movement", 
                    opacity=0.5,
                    underlying_terrain=tile.terrain_type,
                    terrain_elevation=tile.elevation
                )
            )
    
    def _add_attack_targeting(self, context: RenderContext) -> None:
        """Add attack targeting overlays."""
        # Calculate blink phase for animation (500ms cycle)
        blink_phase = (context.current_time_ms // 500) % 2 == 1
        
        # Add all attack range tiles first
        for pos in self.state.battle.attack_range:
            # Skip if this position will be handled as AOE or selected
            if not self.state.battle.aoe_tiles.contains(pos) and pos != self.state.battle.selected_target:
                context.attack_targets.append(
                    AttackTargetRenderData(
                        position=pos, target_type="range", blink_phase=blink_phase
                    )
                )

        # Add AOE tiles (including those outside attack range)
        for pos in self.state.battle.aoe_tiles:
            if pos == self.state.battle.selected_target:
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
                self.state.battle.phase == BattlePhase.ACTION_EXECUTION
                and self.state.battle.targetable_enemies
                and unit.unit_id in self.state.battle.targetable_enemies
            ):
                return "target"
            return None
        
        game_map = self._ensure_game_map()
        context.units.extend(
            DataConverter.units_to_render_data_list(game_map.units, highlight_units)
        )
    
    def _is_in_viewport(self, position: Vector2) -> bool:
        """Check if a position is within the current viewport."""
        # TODO: Re-implement viewport culling when camera system is restored
        # For now, always render everything (renderer will handle viewport clipping)
        return True
    
    def _add_hazards_to_context(self, context: RenderContext) -> None:
        """Add hazard data to the render context."""
        from ..core.renderable import HazardRenderData
        
        # TODO: Enable hazard rendering when hazard system is complete
        # The hazard manager is WIP - skip hazard rendering until fully implemented
        if not hasattr(self.state, 'hazard_manager') or self.state.hazard_manager is None:
            return
        
        hazard_manager = self.state.hazard_manager
        
        # Add render data for each active hazard
        for _, instance in hazard_manager.active_hazards.items():
            hazard = instance.hazard
            
            # Create render data for each position the hazard affects
            for pos_tuple in instance.positions:
                y, x = pos_tuple
                position = Vector2(x, y)
                
                # Viewport culling handled by renderer
                # (all hazards are sent to renderer which handles clipping)
                
                # Determine if this is a warning state (e.g., collapsing terrain about to collapse)
                warning = False
                if hasattr(hazard, 'warning_given'):
                    warning = hazard.warning_given
                
                # Create hazard render data
                context.hazards.append(HazardRenderData(
                    position=position,
                    hazard_type=hazard.properties.hazard_type.name.lower(),
                    intensity=hazard.intensity,
                    symbol=hazard.properties.symbol,
                    color_hint=hazard.properties.color_hint,
                    animation_phase=int(self.state.current_time_ms / 500) % 4,  # Simple animation
                    warning=warning
                ))
    
    def _add_cursor_to_context(self, context: RenderContext) -> None:
        """Add cursor to the render context."""
        # Always set cursor position (for panels to read)
        context.cursor_x = self.state.cursor.position.x
        context.cursor_y = self.state.cursor.position.y
        
        # Add cursor with blinking effect (only visible when blinking on)
        if self._is_cursor_visible():
            context.cursor = CursorRenderData(
                position=self.state.cursor.position, cursor_type="default"
            )
    
    def _add_action_menu(
        self, context: RenderContext, screen_width: int, _screen_height: int
    ) -> None:
        """Add action menu if active."""
        if not self.state.ui.is_action_menu_open():
            return
        
        # Position the action menu in the sidebar area
        sidebar_width = 28 if screen_width >= 90 else 24
        menu_x = screen_width - sidebar_width + 1
        
        # Position will be handled by sidebar renderer - just provide the menu data
        # The sidebar renderer will calculate proper positioning based on actual panel heights
        menu_width = sidebar_width - 2
        menu_height = (
            len(self.state.ui.action_menu_items) + 3
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
                items=self.state.ui.action_menu_items,
                selected_index=self.state.ui.action_menu_selection,
            )
        )
    
    def _add_status_text(
        self, context: RenderContext, _screen_width: int, screen_height: int
    ) -> None:
        """Add status bar text."""
        status_text = f"Turn {self.state.battle.current_turn} | "
        status_text += f"Phase: {self.state.battle.phase.name} | "
        status_text += f"Cursor: ({self.state.cursor.position.x}, {self.state.cursor.position.y}) | "
        status_text += "[Q]uit [Z]Confirm [X]Cancel"
        
        context.texts.append(
            TextRenderData(x=0, y=screen_height - 1, text=status_text)
        )
    
    def _add_ui_elements(self, context: RenderContext) -> None:
        """Add UI elements from UI manager if available."""
        if not self.ui_manager:
            return
        
        # Add strategic TUI overlays if active
        if self.state.ui.is_overlay_open():
            if self.state.ui.active_overlay == "objectives":
                context.overlay = self.ui_manager.build_objectives_overlay()
            elif self.state.ui.active_overlay == "help":
                context.overlay = self.ui_manager.build_help_overlay()
            elif self.state.ui.active_overlay == "minimap":
                context.overlay = self.ui_manager.build_minimap_overlay()
            elif self.state.ui.active_overlay == "expanded_log":
                context.overlay = self.ui_manager.build_expanded_log_overlay()
            elif self.state.ui.active_overlay == "inspection":
                context.overlay = self.ui_manager.build_inspection_overlay()
        
        # Add dialog if active
        if self.state.ui.is_dialog_open() and self.state.ui.active_dialog is not None:
            context.dialog = self.ui_manager.build_dialog(self.state.ui.active_dialog)
        
        # Add battle forecast if active
        if self.state.ui.is_forecast_active():
            context.battle_forecast = self.ui_manager.build_battle_forecast()
        
        # Add banner if active
        banner = self.ui_manager.build_banner()
        if banner:
            context.banner = banner
    
    def _add_timeline_to_context(self, context: RenderContext) -> None:
        """Add timeline visualization to render context."""
        timeline_entries = []
        current_time = 0
        
        # Get real timeline data if available
        if hasattr(self.state.battle, 'timeline') and self.state.battle.timeline:
            timeline = self.state.battle.timeline
            current_time = timeline.current_time
            
            # Get timeline preview (next 8 entries)
            timeline_preview = timeline.get_preview(8)
            
            for index, entry in enumerate(timeline_preview):
                try:
                    timeline_entry = self._convert_timeline_entry(entry, index, current_time)
                    timeline_entries.append(timeline_entry)
                except Exception as e:
                    print(f"Error converting timeline entry: {e}")
                    # Skip problematic entries rather than crash
                    continue
        else:
            # Fallback to simple unit listing if timeline not available
            game_map = self._ensure_game_map()
            for i, unit in enumerate(game_map.units):
                if unit and unit.is_alive and i < 8:  # Limit to 8 entries
                    timeline_entry = self._create_fallback_entry(unit, i)
                    timeline_entries.append(timeline_entry)
        
        context.timeline = TimelineRenderData(
            current_time=current_time,
            entries=timeline_entries,
            max_entries=8,
            show_weights=True,  # Show action weights for tactical decisions
            show_times=True    # Show timing information
        )
        
    
    def _convert_timeline_entry(self, entry, index: int, current_time: int) -> "TimelineEntryRenderData":
        """Convert a timeline entry to render data."""
        from ..core.renderable import TimelineEntryRenderData
        
        # Just provide raw data, let renderer decide symbols/formatting
        entity_name = "Unknown"
        team = 0
        
        if entry.entity_type == "unit":
            # Find the unit by its ID - this MUST exist if timeline is correct
            game_map = self._ensure_game_map()
            unit = game_map.get_unit(entry.entity_id)
            if not unit:
                raise ValueError(f"Timeline entry references non-existent unit ID: {entry.entity_id}")
            
            entity_name = unit.actor.name
            team = unit.team.value
        elif entry.entity_type == "hazard":
            entity_name = f"{entry.entity_type.title()}"
        
        action_desc = entry.action_description or "Acting"
        is_hidden = "???" in action_desc
        action_weight = getattr(entry, 'action_weight', 100)
        
        # Basic visibility logic - renderer can enhance this
        visibility = "full"
        if team != 0 and is_hidden:
            visibility = "hidden"
        elif team != 0 and hasattr(entry, 'hidden_intent') and entry.hidden_intent:
            visibility = "partial"
        
        ticks_remaining = max(0, entry.execution_time - current_time)
        
        return TimelineEntryRenderData(
            entity_name=entity_name,
            action_description=action_desc,
            execution_time=entry.execution_time,
            relative_time=index,
            entity_type=entry.entity_type,
            team=team,
            is_hidden_intent=is_hidden,
            action_weight=action_weight,
            icon="",  # Let renderer decide
            visibility=visibility,
            ticks_remaining=ticks_remaining
        )
    
    def _create_fallback_entry(self, unit, index: int) -> "TimelineEntryRenderData":
        """Create fallback timeline entry for unit.""" 
        from ..core.renderable import TimelineEntryRenderData
        
        # Determine basic action status
        action_desc = "Ready"
        if hasattr(unit, 'has_acted') and unit.has_acted:
            action_desc = "Acted"
        elif hasattr(unit, 'has_moved') and unit.has_moved:
            action_desc = "Moved"
        
        return TimelineEntryRenderData(
            entity_name=unit.name,
            action_description=action_desc,
            execution_time=index * 100,  # Simple ordering
            relative_time=index,
            entity_type="unit",
            team=unit.team.value,
            is_hidden_intent=False,
            action_weight=100,
            icon="",  # Let renderer decide based on unit class
            visibility="full",
            ticks_remaining=0
        )
    
    def _add_unit_info_panel(self, context: RenderContext, screen_width: int, screen_height: int) -> None:
        """Add unit info panel data to render context."""
        from ..core.renderable import UnitInfoPanelRenderData
        
        # Calculate panel dimensions (same as terminal renderer)
        bottom_panel_height = max(4, int(screen_height * 0.20))
        unit_info_width = max(20, int(screen_width * 0.20))
        bottom_panels_y = screen_height - bottom_panel_height
        
        # Get currently selected unit for display
        selected_unit = None
        if hasattr(self.state.battle, 'selected_unit_id') and self.state.battle.selected_unit_id:
            game_map = self._ensure_game_map()
            for unit in game_map.units:
                if unit and unit.is_alive and unit.name == self.state.battle.selected_unit_id:
                    selected_unit = unit
                    break
        
        # If no selected unit, try to get unit at cursor position
        if not selected_unit:
            game_map = self._ensure_game_map()
            for unit in game_map.units:
                if unit and unit.is_alive and unit.position == self.state.cursor.position:
                    selected_unit = unit
                    break
        
        # Always create panel data - either unit info or tile info
        if selected_unit:
            # Get status effects and wounds (if components exist)
            status_effects = []
            wounds = []
            next_action_ticks = None
            is_acting_now = False
            
            # Try to get enhanced unit data if available
            try:
                if hasattr(selected_unit, 'status_effects'):
                    status_effects = selected_unit.status_effects
                if hasattr(selected_unit, 'wound') and hasattr(selected_unit.wound, 'get_active_wounds'):
                    wounds = [str(wound) for wound in selected_unit.wound.get_active_wounds()]
                
                # Get timeline information if available
                if hasattr(self.state.battle, 'timeline') and self.state.battle.timeline:
                    timeline = self.state.battle.timeline
                    # Find next action for this unit in timeline
                    for entry in timeline.get_preview(10):  # Look at next 10 entries
                        if entry.entity_type == "unit" and entry.entity_id == selected_unit.unit_id:
                            next_action_ticks = entry.execution_time - timeline.current_time
                            is_acting_now = next_action_ticks <= 0
                            break
            except AttributeError:
                pass  # Use defaults if enhanced systems not available
            
            # Get mana information (default to 0 if not available)
            mana_current = 0
            mana_max = 0
            try:
                if hasattr(selected_unit, 'mana_current'):
                    mana_current = selected_unit.mana_current
                if hasattr(selected_unit, 'mana_max'):
                    mana_max = selected_unit.mana_max
            except AttributeError:
                pass
            
            context.unit_info_panel = UnitInfoPanelRenderData(
                x=0,
                y=bottom_panels_y,
                width=unit_info_width,
                height=bottom_panel_height,
                unit_name=selected_unit.name,
                unit_class=selected_unit.actor.get_class_name() if hasattr(selected_unit, 'actor') else str(selected_unit.actor.unit_class.name).title(),
                hp_current=selected_unit.hp_current,
                hp_max=selected_unit.health.hp_max if hasattr(selected_unit, 'health') else 100,
                mana_current=mana_current,
                mana_max=mana_max,
                status_effects=status_effects,
                wounds=wounds,
                next_action_ticks=next_action_ticks,
                is_acting_now=is_acting_now,
                show_mana=mana_max > 0,
            )
        else:
            # Show tile information when no unit is selected
            cursor_pos = self.state.cursor.position
            game_map = self._ensure_game_map()
            if not game_map.is_valid_position(cursor_pos):
                # Don't show panel for out of bounds positions
                return
            tile = game_map.get_tile(cursor_pos)
            
            # Get terrain information
            terrain_name = tile.terrain_type.name.replace('_', ' ').title() if hasattr(tile.terrain_type, 'name') else str(tile.terrain_type)
            
            # Get tile properties if available
            tile_info = []
            try:
                from ..core.tileset_loader import get_tileset_config
                tileset = get_tileset_config()
                if hasattr(tile.terrain_type, 'name'):
                    terrain_props = tileset.get_terrain_gameplay_info(tile.terrain_type.name.lower())
                    if terrain_props:
                        move_cost = terrain_props.get('move_cost', 1)
                        defense_bonus = terrain_props.get('defense_bonus', 0)
                        tile_info.append(f"Move Cost: {move_cost}")
                        if defense_bonus > 0:
                            tile_info.append(f"Defense: +{defense_bonus}")
            except (ImportError, AttributeError, KeyError, TypeError):
                # Ignore tileset loading errors - tile info will be empty
                pass
            
            context.unit_info_panel = UnitInfoPanelRenderData(
                x=0,
                y=bottom_panels_y,
                width=unit_info_width,
                height=bottom_panel_height,
                unit_name="Tile Info",
                unit_class=terrain_name,
                hp_current=0,
                hp_max=0,
                mana_current=0,
                mana_max=0,
                status_effects=tile_info,  # Use status_effects list for tile properties
                wounds=[],
                next_action_ticks=None,
                is_acting_now=False,
                show_mana=False,
                title="Tile Info"
            )
    
    def _add_action_menu_panel(self, context: RenderContext, screen_width: int, screen_height: int) -> None:
        """Add action menu panel data to render context."""
        from ..core.renderable import ActionMenuPanelRenderData, ActionMenuItemRenderData
        
        # Calculate panel dimensions
        bottom_panel_height = max(4, int(screen_height * 0.20))
        action_menu_width = max(25, int(screen_width * 0.25))
        action_menu_x = screen_width - action_menu_width
        bottom_panels_y = screen_height - bottom_panel_height
        
        # Only show action menu if action menu is active
        if not self.state.ui.is_action_menu_open():
            return
        
        # Convert existing action menu items to enhanced format
        action_items = []
        if hasattr(self.state.ui, 'action_menu_items') and self.state.ui.action_menu_items:
            for item_str in self.state.ui.action_menu_items:
                # Parse action items from string format (basic parsing)
                # This is a simplified version - a full implementation would have 
                # structured action data from the game system
                if "Attack" in item_str:
                    action_items.append(ActionMenuItemRenderData(
                        name="Attack",
                        action_type="Normal",
                        weight_cost=100,
                        icon="⚔",
                        is_available=True
                    ))
                elif "Move" in item_str:
                    action_items.append(ActionMenuItemRenderData(
                        name="Move",
                        action_type="Light",
                        weight_cost=80,
                        icon="🏃",
                        is_available=True
                    ))
                elif "Wait" in item_str:
                    action_items.append(ActionMenuItemRenderData(
                        name="Wait",
                        action_type="Light",
                        weight_cost=50,
                        icon="⏸",
                        is_available=True
                    ))
                elif "Item" in item_str:
                    action_items.append(ActionMenuItemRenderData(
                        name="Item",
                        action_type="Normal",
                        weight_cost=90,
                        icon="🧪",
                        is_available=True
                    ))
                else:
                    # Generic action
                    action_items.append(ActionMenuItemRenderData(
                        name=item_str,
                        action_type="Normal",
                        weight_cost=100,
                        icon="⚔",
                        is_available=True
                    ))
        
        if action_items:
            context.action_menu_panel = ActionMenuPanelRenderData(
                x=action_menu_x,
                y=bottom_panels_y,
                width=action_menu_width,
                height=bottom_panel_height,
                title="Actions",
                actions=action_items,
                selected_index=self.state.ui.action_menu_selection if hasattr(self.state.ui, 'action_menu_selection') else 0,
                selection_indicator="➤",
                show_weights=True,
                show_mana_costs=True
            )
    
    def _add_log_panel(self, context: RenderContext, screen_width: int, screen_height: int) -> None:
        """Add log panel data to render context."""
        if not self.log_manager:
            return
        
        # Calculate panel dimensions - log panel takes right side of battlefield
        timeline_height = max(2, int(screen_height * 0.12))
        bottom_panel_height = max(5, int(screen_height * 0.20))
        battlefield_height = screen_height - timeline_height - bottom_panel_height
        
        # Split battlefield area: 60% for map, 40% for log
        map_width = int(screen_width * 0.6)
        log_width = screen_width - map_width - 1  # -1 for separator
        log_x = map_width + 1
        log_y = timeline_height
        
        # Get recent messages from log manager
        messages = self.log_manager.get_messages(count=100)  # Get last 100 messages
        
        # Format messages for display
        formatted_messages = []
        for msg in messages:
            formatted = msg.format(include_timestamp=False, include_category=True)
            formatted_messages.append(formatted)
        
        # Add a welcome message if no messages exist
        if not formatted_messages:
            formatted_messages = ["[SYS] Welcome to Grimdark SRPG!", "[SYS] Message log initialized"]
        
        # Create log panel render data
        context.log_panel = LogPanelRenderData(
            x=log_x,
            y=log_y,
            width=log_width,
            height=battlefield_height,
            messages=formatted_messages,
            title="Message Log",
            show_timestamps=False,
            show_categories=True,
            scroll_offset=0,
            total_messages=len(messages)
        )
    
    def _is_cursor_visible(self) -> bool:
        """Check if cursor should be visible (2Hz blinking)."""
        elapsed_time = time.time() - self.game_start_time
        # Calculate which blink cycle we're in
        cycle_position = elapsed_time % (self.cursor_blink_interval * 2)
        # Cursor is visible during the first half of each cycle
        return cycle_position < self.cursor_blink_interval