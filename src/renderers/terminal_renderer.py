import sys
import termios
import tty
import select
from typing import Optional
from collections import defaultdict

from ..core.renderer import Renderer, RendererConfig
from ..core.renderable import (
    RenderContext, TileRenderData, UnitRenderData, 
    CursorRenderData, OverlayTileRenderData, MenuRenderData,
    BattleForecastRenderData, DialogRenderData, BannerRenderData,
    OverlayRenderData, LayerType
)
from ..core.input import InputEvent, Key
from ..core.tileset_loader import get_tileset_config


class TerminalRenderer(Renderer):
    
    def __init__(self, config: Optional[RendererConfig] = None):
        super().__init__(config)
        self._old_settings = None
        self._buffer = []
        self._cursor_position: Optional[tuple[int, int]] = None
        # Load tileset configuration for gameplay data only
        self.tileset_config = get_tileset_config()
        
        # Terminal-specific terrain symbol mappings (Unicode)
        self.terrain_symbols = {
            "plain": ".",
            "forest": "♣",
            "mountain": "▲",
            "water": "≈",
            "road": "=",
            "fort": "■",
            "bridge": "╬",
            "wall": "█"
        }
        
        # Terminal-specific terrain color mappings (ANSI codes)
        self.terrain_colors = {
            "plain": "\033[97m",    # white
            "forest": "\033[92m",   # green
            "mountain": "\033[37m", # gray
            "water": "\033[96m",    # cyan
            "road": "\033[93m",     # yellow
            "fort": "\033[37m",     # gray
            "bridge": "\033[93m",   # yellow
            "wall": "\033[37m"      # gray
        }
        
        # Terminal-specific UI symbol mappings
        self.ui_symbols = {
            "cursor": "◎",
            "movement_overlay": "◦",
            "attack_overlay": "◆",
            "danger_overlay": "⚠",
            "highlight_overlay": "◊"
        }
        
        # Terminal-specific UI color mappings (ANSI codes)
        self.ui_colors = {
            "movement": "\033[46m",   # Cyan background
            "attack": "\033[41m",     # Red background
            "danger": "\033[43m",     # Yellow background
            "highlight": "\033[45m",  # Magenta background
        }
        
        # Attack targeting colors
        self.attack_colors = {
            "range_subtle": "\033[48;5;52m",    # Dark red background (subtle)
            "aoe_red": "\033[41m",              # Bright red background for AOE
            "text_white": "\033[97m",            # White foreground
            "text_black": "\033[30m",            # Black foreground
        }
        
        # Terminal-specific unit class symbols
        self.unit_symbols = {
            "knight": "K",
            "archer": "A",
            "mage": "M",
            "priest": "P",
            "thief": "T",
            "warrior": "W"
        }
        
        # Terminal-specific team colors (ANSI codes)
        self.team_colors = {
            0: "\033[94m",    # Player - Blue
            1: "\033[91m",    # Enemy - Red
            2: "\033[92m",    # Ally - Green
            3: "\033[93m",    # Neutral - Yellow
        }
        
        # Terminal control codes
        self.terminal_codes = {
            "reset": "\033[0m",
            "clear_screen": "\033[2J",
            "cursor_home": "\033[H",
            "hide_cursor": "\033[?25l",
            "show_cursor": "\033[?25h",
            "text_normal": "\033[97m",      # White
            "text_dim": "\033[37m",         # Light gray
            "text_bright": "\033[1;97m",    # Bright white
            "text_success": "\033[92m",     # Green
            "text_warning": "\033[93m",     # Yellow
            "text_error": "\033[91m",       # Red
            "text_red": "\033[91m",         # Red
            "text_green": "\033[92m",       # Green
            "text_yellow": "\033[93m",      # Yellow
            "text_blue": "\033[94m",        # Blue
            "text_magenta": "\033[95m",     # Magenta
            "text_cyan": "\033[96m",        # Cyan
            "text_white": "\033[97m",       # White
            "text_bright_red": "\033[1;91m",    # Bright red
            "text_bright_green": "\033[1;92m",  # Bright green
            "text_bright_yellow": "\033[1;93m", # Bright yellow
            "text_bright_blue": "\033[1;94m",   # Bright blue
            "text_bright_cyan": "\033[1;96m"    # Bright cyan
        }
        
        # Layout configuration
        self.sidebar_width = 28  # Width of right sidebar
        self.bottom_strip_height = 3  # Height of bottom message area
        self.min_terminal_width = 80
        self.min_terminal_height = 26
        
        # Message log for bottom strip
        self.message_log = []
        self.max_messages = 20  # Keep last 20 messages
        
    def initialize(self) -> None:
        self._old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        print(self.terminal_codes["hide_cursor"], end='', flush=True)
        self.clear()
    
    def cleanup(self) -> None:
        if self._old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
        print(self.terminal_codes["show_cursor"], end='', flush=True)
        print(self.terminal_codes["reset"], end='', flush=True)
    
    def clear(self) -> None:
        print(self.terminal_codes["clear_screen"] + self.terminal_codes["cursor_home"], end='', flush=True)
    
    def present(self) -> None:
        # Clear screen and go to home position
        print(self.terminal_codes["clear_screen"] + self.terminal_codes["cursor_home"], end='', flush=True)
        
        # Print each line with explicit carriage return and newline for raw terminal mode
        for line in self._buffer:
            print(line + '\r\n', end='', flush=True)
        self._buffer.clear()
    
    def render_frame(self, context: RenderContext) -> None:
        self._buffer.clear()
        
        # Calculate layout dimensions
        screen_width = self.config.width
        screen_height = self.config.height
        
        # Create grid for entire screen
        grid = [[' ' for _ in range(screen_width)] for _ in range(screen_height)]
        colors = [['' for _ in range(screen_width)] for _ in range(screen_height)]
        
        # Check if we have battle-specific content - be more inclusive
        # Use 4-panel layout if we have a timeline (even if empty), units, or world dimensions
        has_timeline = context.timeline is not None  # Timeline object exists, even if empty
        has_world = context.world_width > 0 and context.world_height > 0
        has_units = context.units and len(context.units) > 0
        
        is_battle_phase = has_timeline or has_world or has_units
        
        if is_battle_phase:
            # Battle phase: render with 4-panel layout
            self._render_four_panel_layout(context, grid, colors, screen_width, screen_height)
        else:
            # Menu phase: render with simple full-screen layout
            self._render_simple_layout(context, grid, colors, screen_width, screen_height)
        
        # Convert grid to buffer lines
        for y in range(len(grid)):
            line = []
            for x in range(len(grid[y])):
                if colors[y][x]:
                    line.append(colors[y][x] + grid[y][x] + self.terminal_codes["reset"])
                else:
                    line.append(grid[y][x])
            self._buffer.append(''.join(line))
    
    def _render_battle_layout(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                            screen_width: int, screen_height: int) -> None:
        """Render the 3-panel battle layout with map, sidebar, and message strip."""
        # Reset cursor position tracking
        self._cursor_position = None
        
        # Adjust sidebar width for smaller terminals
        if screen_width < 90:
            self.sidebar_width = 24
        else:
            self.sidebar_width = 28
            
        # Reserve space for timeline at top (2 lines: timeline + separator)
        timeline_height = 2 if context.timeline else 0
        
        # Calculate viewport dimensions with timeline space
        map_viewport_width = screen_width - self.sidebar_width
        map_viewport_height = screen_height - self.bottom_strip_height - timeline_height
        
        # Render timeline at top if available
        if context.timeline and timeline_height > 0:
            self._render_timeline(context, grid, colors, 0, 0, screen_width)
            
            # Draw horizontal separator below timeline
            for x in range(screen_width):
                grid[timeline_height - 1][x] = '─'
                colors[timeline_height - 1][x] = self.terminal_codes["text_dim"]
        
        # Render map viewport (left side, offset by timeline height)
        self._render_map_viewport(context, grid, colors, map_viewport_width, map_viewport_height, timeline_height)
        
        # Draw vertical separator between map and sidebar (offset by timeline height)
        for y in range(timeline_height, timeline_height + map_viewport_height):
            grid[y][map_viewport_width] = '│'
            colors[y][map_viewport_width] = self.terminal_codes["text_dim"]
        
        # Render sidebar panels (right side, offset by timeline height)
        self._render_sidebar(context, grid, colors, map_viewport_width + 1, timeline_height, 
                           self.sidebar_width - 1, map_viewport_height)
        
        # Draw horizontal separator above bottom strip
        separator_y = timeline_height + map_viewport_height
        for x in range(screen_width):
            grid[separator_y][x] = '─'
            colors[separator_y][x] = self.terminal_codes["text_dim"]
        
        # Render bottom message strip
        self._render_message_strip(context, grid, colors, 0, separator_y + 1, 
                                 screen_width, self.bottom_strip_height - 1)
        
        # Apply cursor effect AFTER panels are rendered (only to map area)
        cursor_pos: Optional[tuple[int, int]] = self._cursor_position
        if cursor_pos is not None:
            cx, cy = cursor_pos
            # Only apply cursor effect if it's in the map viewport area
            if cx < map_viewport_width and cy < map_viewport_height:
                colors[cy][cx] = "\033[7m" + (colors[cy][cx] if colors[cy][cx] else "")
        
        # Render new strategic TUI elements (on top of everything else)
        if context.battle_forecast:
            self._render_battle_forecast_on_grid(context.battle_forecast, grid, colors)
        
        if context.dialog:
            self._render_dialog_on_grid(context.dialog, grid, colors)
        
        if context.banner:
            self._render_banner_on_grid(context.banner, grid, colors)
        
        if context.overlay:
            self._render_overlay_on_grid(context.overlay, grid, colors)
    
    def _render_four_panel_layout(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                                screen_width: int, screen_height: int) -> None:
        """Render the new 4-panel UI layout: Timeline (top) + Battlefield (center) + Unit Info (bottom-left) + Action Menu (bottom-right)."""
        # Reset cursor position tracking
        self._cursor_position = None
        
        # Calculate panel dimensions based on ui.md specifications
        timeline_height = max(2, int(screen_height * 0.12))  # 10-15% -> use 12%
        bottom_panel_height = max(5, int(screen_height * 0.20))  # 20% height for bottom panels, min 5 lines
        battlefield_height = screen_height - timeline_height - bottom_panel_height
        
        # Bottom panel width splits: give more space to unit info panel
        unit_info_width = max(30, int(screen_width * 0.35))  # Increased to 35% for better visibility
        action_menu_width = max(25, int(screen_width * 0.25)) 
        battlefield_width = screen_width  # Full width for battlefield
        
        # Panel positioning
        timeline_y = 0
        battlefield_y = timeline_height
        bottom_panels_y = timeline_height + battlefield_height
        
        # 1. Render Timeline Panel (full width at top)
        if context.timeline:
            self._render_timeline_panel(context, grid, colors, 0, timeline_y, screen_width, timeline_height)
        else:
            # Draw separator below timeline
            separator_y = timeline_height - 1
            for x in range(screen_width):
                grid[separator_y][x] = '─'
                colors[separator_y][x] = self.terminal_codes["text_dim"]
        
        # 2. Render Battlefield Panel and Log Panel (split horizontally)
        # Split the battlefield area: 60% for map, 40% for log
        map_width = int(battlefield_width * 0.6)
        log_width = battlefield_width - map_width - 1  # -1 for separator
        
        # Render battlefield on the left
        self._render_battlefield_panel(context, grid, colors, 0, battlefield_y, map_width, battlefield_height)
        
        # Draw vertical separator between battlefield and log
        separator_x = map_width
        for y in range(battlefield_y, battlefield_y + battlefield_height):
            if separator_x < screen_width:
                grid[y][separator_x] = '│'
                colors[y][separator_x] = self.terminal_codes["text_dim"]
        
        # Render log panel on the right
        if context.log_panel and log_width > 10:  # Only render if we have enough width
            self._render_log_panel(context, grid, colors, map_width + 1, battlefield_y, log_width, battlefield_height)
        
        # Draw separator above bottom panels
        separator_y = bottom_panels_y - 1
        for x in range(screen_width):
            grid[separator_y][x] = '─'
            colors[separator_y][x] = self.terminal_codes["text_dim"]
        
        # 3. Render Unit Info Panel (bottom-left)
        if context.unit_info_panel:
            self._render_unit_info_panel(context, grid, colors, 0, bottom_panels_y, unit_info_width, bottom_panel_height)
        
        # 4. Render Action Menu Panel (bottom-right)
        if context.action_menu_panel:
            action_menu_x = screen_width - action_menu_width
            self._render_action_menu_panel(context, grid, colors, action_menu_x, bottom_panels_y, action_menu_width, bottom_panel_height)
        
        # Draw vertical separator between bottom panels
        separator_x = unit_info_width
        for y in range(bottom_panels_y, screen_height):
            if separator_x < screen_width:
                grid[y][separator_x] = '│'
                colors[y][separator_x] = self.terminal_codes["text_dim"]
        
        # Apply cursor effect AFTER panels are rendered (only to battlefield area)
        cursor_pos: Optional[tuple[int, int]] = self._cursor_position
        if cursor_pos is not None:
            cx, cy = cursor_pos
            # Only apply cursor effect if it's in the battlefield area
            if cx < battlefield_width and battlefield_y <= cy < battlefield_y + battlefield_height:
                adjusted_cy = cy  # Cursor position is already adjusted by viewport
                if 0 <= adjusted_cy < screen_height:
                    colors[adjusted_cy][cx] = "\033[7m" + (colors[adjusted_cy][cx] if colors[adjusted_cy][cx] else "")
        
        # Render strategic TUI overlays (on top of everything else)
        if context.battle_forecast:
            self._render_battle_forecast_on_grid(context.battle_forecast, grid, colors)
        
        if context.banner:
            self._render_banner_on_grid(context.banner, grid, colors)
        
        if context.overlay:
            self._render_overlay_on_grid(context.overlay, grid, colors)
        
        if context.dialog:
            self._render_dialog_on_grid(context.dialog, grid, colors)

    def _render_simple_layout(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                            screen_width: int, screen_height: int) -> None:
        """Render simple full-screen layout for menus."""
        # Render menus centered on full screen
        if context.menus:
            for menu in context.menus:
                self._render_menu_on_grid(menu, grid, colors)
        
        # Render any text elements (like instructions at bottom)
        if context.texts:
            for text in context.texts:
                if 0 <= text.y < screen_height:
                    line_text = text.text[:screen_width]
                    for i, char in enumerate(line_text):
                        if text.x + i < screen_width:
                            grid[text.y][text.x + i] = char
        
        # Render strategic TUI elements in simple layout too
        if context.overlay:
            self._render_overlay_on_grid(context.overlay, grid, colors)
        
        if context.dialog:
            self._render_dialog_on_grid(context.dialog, grid, colors)
    
    def _render_map_viewport(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                           width: int, height: int, y_offset: int = 0) -> None:
        """Render the map area in the left portion of the screen."""
        render_items = defaultdict(list)
        
        if context.tiles:
            render_items[LayerType.TERRAIN].extend(context.tiles)
        if context.overlays:
            render_items[LayerType.OVERLAY].extend(context.overlays)
        if context.attack_targets:
            render_items[LayerType.OVERLAY].extend(context.attack_targets)
        if context.units:
            render_items[LayerType.UNITS].extend(context.units)
        if context.cursor:
            render_items[LayerType.UI].append(context.cursor)
        
        # Render menus that should appear on the map (not sidebar menus)
        if context.menus:
            for menu in context.menus:
                # Only render menus positioned within the map viewport (exclude sidebar menus)
                if menu.x < width and menu.title != "Actions":
                    render_items[LayerType.UI].append(menu)
        
        for layer in [LayerType.TERRAIN, LayerType.OVERLAY, LayerType.UNITS, LayerType.UI]:
            for item in render_items[layer]:
                self._render_item(item, grid, colors, context, width, height, y_offset)
    
    def _render_sidebar(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]],
                       x_offset: int, y_offset: int, width: int, height: int) -> None:
        """Render the sidebar panels on the right side of the screen."""
        current_y = y_offset
        
        # Render terrain info panel
        terrain_height = self._render_terrain_panel(context, grid, colors, x_offset, current_y, width)
        current_y += terrain_height  # No extra spacing
        
        # Check if we have an action menu to determine if unit panel should be compact
        has_action_menu = any(menu.title == "Actions" for menu in context.menus) if context.menus else False
        
        # Render unit info panel (compact if action menu is active)
        unit_height = self._render_unit_panel(context, grid, colors, x_offset, current_y, width, compact=has_action_menu)
        current_y += unit_height  # No extra spacing
        
        # Render action menu if active, otherwise show game state panel
        available_space = height - current_y
        if context.menus:
            # Check if there's an action menu in the sidebar area
            action_menu = None
            for menu in context.menus:
                if menu.x >= x_offset and menu.title == "Actions":
                    action_menu = menu
                    break
            
            if action_menu and available_space >= 3:  # Minimum space for action menu (title + 1 item + border)
                # Position the action menu at current_y and render it
                # Ensure menu doesn't extend beyond the sidebar area
                max_menu_height = min(len(action_menu.items) + 3, available_space)
                
                repositioned_menu = MenuRenderData(
                    x=x_offset,
                    y=current_y,
                    width=width,
                    height=max_menu_height,
                    title=action_menu.title,
                    items=action_menu.items[:max_menu_height-3] if max_menu_height < len(action_menu.items) + 3 else action_menu.items,
                    selected_index=min(action_menu.selected_index, len(action_menu.items[:max_menu_height-3])-1) if max_menu_height < len(action_menu.items) + 3 else action_menu.selected_index
                )
                self._render_menu_on_grid(repositioned_menu, grid, colors)
            elif available_space >= 5:
                # No action menu or insufficient space, show game state panel if it fits
                self._render_game_state_panel(context, grid, colors, x_offset, current_y, width)
        elif available_space >= 5:
            # No menus at all, show game state panel if it fits
            self._render_game_state_panel(context, grid, colors, x_offset, current_y, width)
    
    def _render_terrain_panel(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]],
                            x_offset: int, y_offset: int, width: int) -> int:
        """Render terrain information panel. Returns height used."""
        panel_height = 6  # Reduced from 7 to make it more compact
        
        # Draw panel border
        self._draw_box(grid, colors, x_offset, y_offset, width, panel_height, "Terrain")
        
        # Get terrain at cursor position (always available)
        cursor_x, cursor_y = context.cursor_x, context.cursor_y
        terrain_tile = None
        
        # Find terrain tile at cursor position
        for tile in context.tiles:
            if tile.position.x == cursor_x and tile.position.y == cursor_y:
                terrain_tile = tile
                break
        
        if terrain_tile:
            # Terrain type
            terrain_name = terrain_tile.terrain_type.replace('_', ' ').title()
            self._draw_text(grid, f"Type: {terrain_name}", x_offset + 2, y_offset + 2, width - 4, "", colors)
            
            # Movement cost and evasion on same line to save space
            move_costs = {"plain": 1, "forest": 2, "mountain": 3, "water": 99, "road": 1, "fort": 1}
            move_cost = move_costs.get(terrain_tile.terrain_type, 1)
            eva_bonus = {"forest": 15, "mountain": 20, "fort": 25}.get(terrain_tile.terrain_type, 0)
            self._draw_text(grid, f"Move:{move_cost} EVA:+{eva_bonus}%", x_offset + 2, y_offset + 3, width - 4, "", colors)
            
            # Coordinates
            self._draw_text(grid, f"Pos: ({cursor_x}, {cursor_y})", x_offset + 2, y_offset + 4, width - 4, "", colors)
        else:
            # Show cursor position even if no terrain tile
            self._draw_text(grid, f"Pos: ({cursor_x}, {cursor_y})", x_offset + 2, y_offset + 2, width - 4, "", colors)
        
        return panel_height
    
    def _render_unit_panel(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]],
                         x_offset: int, y_offset: int, width: int, compact: bool = False) -> int:
        """Render enhanced unit information panel. Returns height used."""
        # Use compact mode when action menu needs space
        panel_height = 12 if compact else 17  # Increased to accommodate wound/morale info
        
        # Draw panel border
        self._draw_box(grid, colors, x_offset, y_offset, width, panel_height, "Unit")
        
        # Find unit at cursor position (always available)
        cursor_x, cursor_y = context.cursor_x, context.cursor_y
        unit = None
        
        for u in context.units:
            if u.position.x == cursor_x and u.position.y == cursor_y:
                unit = u
                break
        
        if unit:
            current_line = 2
            
            # Unit class and team
            team_names = {0: "Player", 1: "Enemy", 2: "Ally", 3: "Neutral"}
            team_name = team_names.get(unit.team, "Unknown")
            self._draw_text(grid, f"{unit.unit_type} ({team_name})", x_offset + 2, y_offset + current_line, width - 4, "", colors)
            current_line += 1
            
            # Level and EXP
            self._draw_text(grid, f"LV {unit.level}  EXP {unit.exp}", x_offset + 2, y_offset + current_line, width - 4, "", colors)
            current_line += 1
            
            # HP bar with text
            hp_text = f"HP {unit.hp_current}/{unit.hp_max}"
            self._draw_text(grid, hp_text, x_offset + 2, y_offset + current_line, width - 4, "", colors)
            current_line += 1
            
            # Draw HP bar
            bar_width = width - 6
            filled = int(unit.hp_percent * bar_width)
            empty = bar_width - filled
            
            # Determine bar color based on HP percentage
            if unit.hp_percent > 0.6:
                bar_color = self.terminal_codes["text_success"]
            elif unit.hp_percent > 0.3:
                bar_color = self.terminal_codes["text_warning"]
            else:
                bar_color = self.terminal_codes["text_error"]
            
            bar_text = "[" + "█" * filled + "░" * empty + "]"
            self._draw_text(grid, bar_text, x_offset + 2, y_offset + current_line, width - 4, bar_color, colors)
            current_line += 1
            
            # Combat stats
            self._draw_text(grid, f"ATK {unit.attack}  DEF {unit.defense}  SPD {unit.speed}", x_offset + 2, y_offset + current_line, width - 4, "", colors)
            current_line += 1
            
            # Status
            status = "Can Act" if unit.is_active else "Acted"
            self._draw_text(grid, f"Status: {status}", x_offset + 2, y_offset + current_line, width - 4, "", colors)
            current_line += 1
            
            # Status effects (only show in full mode, not compact)
            if not compact:
                if unit.status_effects:
                    effects_text = "Effects: " + ", ".join(unit.status_effects)
                    # Truncate if too long
                    if len(effects_text) > width - 6:
                        effects_text = effects_text[:width - 9] + "..."
                    self._draw_text(grid, effects_text, x_offset + 2, y_offset + current_line, width - 4, "", colors)
                else:
                    self._draw_text(grid, "Effects: None", x_offset + 2, y_offset + current_line, width - 4, "", colors)
                current_line += 1
            
            # Morale information
            morale_color = ""
            if unit.morale_state in ["Routed", "Terrified"]:
                morale_color = self.terminal_codes.get("text_error", "")
            elif unit.morale_state in ["Panicked", "Afraid", "Shaken"]:
                morale_color = self.terminal_codes.get("text_warning", "")
            elif unit.morale_state in ["Heroic", "Confident"]:
                morale_color = self.terminal_codes.get("text_success", "")
                
            self._draw_text(grid, f"Morale: {unit.morale_current} ({unit.morale_state})", 
                           x_offset + 2, y_offset + current_line, width - 4, morale_color, colors)
            current_line += 1
            
            # Wound information  
            if unit.wound_count > 0:
                wound_color = self.terminal_codes.get("text_error", "")
                plural = "s" if unit.wound_count > 1 else ""
                self._draw_text(grid, f"Wounds: {unit.wound_count} active injury{plural}", 
                               x_offset + 2, y_offset + current_line, width - 4, wound_color, colors)
                current_line += 1
                
                # Show wound details in full mode
                if not compact and unit.wound_descriptions:
                    for i, wound_desc in enumerate(unit.wound_descriptions[:3]):  # Show max 3 wounds
                        # Truncate if too long
                        if len(wound_desc) > width - 6:
                            wound_desc = wound_desc[:width - 9] + "..."
                        icon = "🩸" if i == 0 else " "
                        self._draw_text(grid, f"{icon} {wound_desc}", 
                                       x_offset + 2, y_offset + current_line, width - 4, wound_color, colors)
                        current_line += 1
                        
                    # Show "and X more" if there are additional wounds
                    if len(unit.wound_descriptions) > 3:
                        remaining = len(unit.wound_descriptions) - 3
                        self._draw_text(grid, f"  ...and {remaining} more", 
                                       x_offset + 2, y_offset + current_line, width - 4, wound_color, colors)
                        current_line += 1
            else:
                self._draw_text(grid, "Wounds: None", x_offset + 2, y_offset + current_line, width - 4, "", colors)
                current_line += 1
        else:
            self._draw_text(grid, "No unit", x_offset + 2, y_offset + 2, width - 4, "", colors)
        
        return panel_height
    
    def _render_game_state_panel(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]],
                                x_offset: int, y_offset: int, width: int) -> int:
        """Render game state information panel. Returns height used."""
        panel_height = 5  # Reduced to be more compact
        
        # Draw panel border
        self._draw_box(grid, colors, x_offset, y_offset, width, panel_height, "Game Info")
        
        # Show current turn and team phase
        team_names = {0: "Player", 1: "Enemy", 2: "Ally", 3: "Neutral"}
        current_team_name = team_names.get(context.current_team, "Unknown")
        
        self._draw_text(grid, f"Turn: {context.current_turn}", x_offset + 2, y_offset + 2, width - 4, "", colors)
        self._draw_text(grid, f"Team: {current_team_name}", x_offset + 2, y_offset + 3, width - 4, "", colors)
        
        # Add game phase and battle phase for debugging
        self._draw_text(grid, f"Game Phase: {context.game_phase}", x_offset + 2, y_offset + 4, width - 4, "", colors)
        battle_phase = context.battle_phase if context.battle_phase else "None"
        self._draw_text(grid, f"Battle Phase: {battle_phase}", x_offset + 2, y_offset + 5, width - 4, "", colors)
        
        return panel_height
    
    def _draw_box(self, grid: list[list[str]], colors: list[list[str]], 
                  x: int, y: int, width: int, height: int, title: str = "") -> None:
        """Draw a box with Unicode box-drawing characters."""
        # Top border
        grid[y][x] = '┌'
        grid[y][x + width - 1] = '┐'
        for i in range(1, width - 1):
            grid[y][x + i] = '─'
        
        # Title if provided
        if title:
            title_text = f" {title} "
            title_start = x + (width - len(title_text)) // 2
            for i, char in enumerate(title_text):
                if title_start + i < x + width - 1:
                    grid[y][title_start + i] = char
        
        # Sides
        for i in range(1, height - 1):
            if y + i < len(grid):
                grid[y + i][x] = '│'
                grid[y + i][x + width - 1] = '│'
        
        # Bottom border
        if y + height - 1 < len(grid):
            grid[y + height - 1][x] = '└'
            grid[y + height - 1][x + width - 1] = '┘'
            for i in range(1, width - 1):
                grid[y + height - 1][x + i] = '─'
        
        # Set color for all box characters
        for i in range(height):
            if y + i < len(grid):
                colors[y + i][x] = self.terminal_codes["text_dim"]
                colors[y + i][x + width - 1] = self.terminal_codes["text_dim"]
        for i in range(width):
            colors[y][x + i] = self.terminal_codes["text_dim"]
            if y + height - 1 < len(grid):
                colors[y + height - 1][x + i] = self.terminal_codes["text_dim"]
    
    def _render_timeline(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                        x_offset: int, y_offset: int, width: int) -> None:
        """Render timeline visualization at the top of the screen."""
        if not context.timeline or not context.timeline.entries:
            return
        
        timeline_text = []
        remaining_width = width
        
        # Show "NOW →" indicator
        now_indicator = "NOW → "
        timeline_text.append(now_indicator)
        remaining_width -= len(now_indicator)
        
        for i, entry in enumerate(context.timeline.entries):
            if remaining_width <= 10:  # Need space for at least one more entry
                timeline_text.append("...")
                break
                
            # Build entry text: [Icon Name Action (+weight)]
            entry_parts = []
            
            # Add icon and name
            entry_parts.append(f"{entry.icon} {entry.entity_name[:8]}")  # Limit name length
            
            # Add action description (abbreviated if hidden)
            if entry.is_hidden_intent:
                entry_parts.append("???")
            else:
                action = entry.action_description[:12]  # Limit action length
                entry_parts.append(action)
            
            # Add weight if showing weights
            if context.timeline.show_weights:
                entry_parts.append(f"(+{entry.action_weight})")
            
            entry_text = " ".join(entry_parts)
            
            # Check if this entry fits
            separator = " → " if i < len(context.timeline.entries) - 1 else ""
            full_entry_text = f"[ {entry_text} ]{separator}"
            
            if len(full_entry_text) > remaining_width:
                timeline_text.append("...")
                break
            
            timeline_text.append(f"[ {entry_text} ]")
            remaining_width -= len(full_entry_text)
            
            # Add separator if not last entry
            if i < len(context.timeline.entries) - 1 and remaining_width > 3:
                timeline_text.append(" → ")
                remaining_width -= 3
        
        # Join all parts and render
        full_timeline_text = "".join(timeline_text)
        
        # Truncate if still too long
        if len(full_timeline_text) > width:
            full_timeline_text = full_timeline_text[:width-3] + "..."
        
        # Render the timeline text
        for i, char in enumerate(full_timeline_text):
            if x_offset + i < width:
                grid[y_offset][x_offset + i] = char
                # Color code based on teams and special indicators
                if char in "⚔🏃🛡🔥":  # Icons
                    colors[y_offset][x_offset + i] = self.terminal_codes["text_warning"]
                elif "???" in full_timeline_text[max(0, i-2):i+3]:  # Hidden intents
                    colors[y_offset][x_offset + i] = self.terminal_codes["text_dim"]
                elif "NOW" in full_timeline_text[max(0, i-3):i+1]:  # NOW indicator
                    colors[y_offset][x_offset + i] = self.terminal_codes["text_success"]
    
    def _draw_text(self, grid: list[list[str]], text: str, x: int, y: int, max_width: int, color: str = "", colors: Optional[list[list[str]]] = None) -> None:
        """Draw text at the specified position, truncating if needed."""
        if y >= len(grid):
            return
            
        text = text[:max_width]
        for i, char in enumerate(text):
            if x + i < len(grid[y]):
                grid[y][x + i] = char
                if color and colors:
                    colors[y][x + i] = color
    
    def _render_message_strip(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]],
                            x_offset: int, y_offset: int, width: int, height: int) -> None:
        """Render the message log at the bottom of the screen."""
        # Add border line at top of message strip
        for x in range(width):
            grid[y_offset - 1][x_offset + x] = '─'
            colors[y_offset - 1][x_offset + x] = self.terminal_codes["text_dim"]
        
        # Add title for message area
        title = " Message Log "
        title_x = (width - len(title)) // 2
        for i, char in enumerate(title):
            if title_x + i < width:
                grid[y_offset - 1][x_offset + title_x + i] = char
                colors[y_offset - 1][x_offset + title_x + i] = self.terminal_codes["text_normal"]
        
        # Render messages from context.texts or placeholder messages
        if context.texts:
            # Show the most recent messages
            for i, text in enumerate(context.texts[-height:]):
                if y_offset + i < len(grid):
                    line_text = text.text[:width]
                    for j, char in enumerate(line_text):
                        if x_offset + j < len(grid[0]):
                            grid[y_offset + i][x_offset + j] = char
        else:
            # Show placeholder message
            placeholder_msg = "Welcome to Grimdark SRPG! Use arrow keys to move cursor, Enter to select."
            if height >= 1:
                line_text = placeholder_msg[:width]
                for j, char in enumerate(line_text):
                    if x_offset + j < len(grid[0]):
                        grid[y_offset][x_offset + j] = char
    
    def _render_item(self, item, grid, colors, context, max_width=None, max_height=None, y_offset=0):
        vx = context.viewport_x
        vy = context.viewport_y
        vw = max_width if max_width else self.config.width
        vh = max_height if max_height else self.config.height - 3
        
        screen_x = item.position.x - vx
        screen_y = item.position.y - vy + y_offset
        
        if 0 <= screen_x < vw and 0 <= screen_y - y_offset < vh:
            if isinstance(item, TileRenderData):
                # Get symbol from renderer's own terrain mapping
                symbol = self.terrain_symbols.get(item.terrain_type, "?")
                grid[screen_y][screen_x] = symbol
                
                if item.highlight:
                    colors[screen_y][screen_x] = self.ui_colors.get(item.highlight, "")
                else:
                    # Apply terrain-specific colors from renderer's own mapping
                    color = self.terrain_colors.get(item.terrain_type, "")
                    if color:
                        colors[screen_y][screen_x] = color
                    
            elif isinstance(item, OverlayTileRenderData):
                symbol = self.ui_symbols.get(f"{item.overlay_type}_overlay", "?")
                grid[screen_y][screen_x] = symbol
                colors[screen_y][screen_x] = self.ui_colors.get(item.overlay_type, "")
            
            elif hasattr(item, 'target_type'):  # AttackTargetRenderData
                # Store original color before modifying
                original_color = colors[screen_y][screen_x]
                
                if item.target_type == "range":
                    # Subtle dark red background for attack range
                    colors[screen_y][screen_x] = self.attack_colors["range_subtle"] + original_color
                elif item.target_type == "aoe":
                    # AOE tiles: blink between normal and red background with white symbol
                    if item.blink_phase:
                        colors[screen_y][screen_x] = self.attack_colors["aoe_red"] + self.attack_colors["text_white"]
                    else:
                        colors[screen_y][screen_x] = self.attack_colors["range_subtle"] + original_color
                elif item.target_type == "selected":
                    # Selected tile: blink between normal and red background with black X
                    if item.blink_phase:
                        grid[screen_y][screen_x] = "X"
                        colors[screen_y][screen_x] = self.attack_colors["aoe_red"] + self.attack_colors["text_black"]
                    else:
                        colors[screen_y][screen_x] = self.attack_colors["range_subtle"] + original_color
                    
            elif isinstance(item, UnitRenderData):
                symbol = self.unit_symbols.get(item.unit_type.lower(), "?")
                grid[screen_y][screen_x] = symbol
                
                # Get current color (might have attack target background)
                current_color = colors[screen_y][screen_x] or ""
                
                # Check if this position has attack target background
                has_attack_background = (self.attack_colors["range_subtle"] in current_color or 
                                       self.attack_colors["aoe_red"] in current_color)
                
                if has_attack_background:
                    # Preserve attack target background, set unit foreground color
                    unit_color = self.team_colors.get(item.team, "")
                    if item.highlight_type == "target":
                        unit_color = self.attack_colors["text_white"]  # White text for better visibility
                    elif not item.is_active:
                        unit_color = "\033[90m"  # Dark gray for inactive units
                    
                    # Extract background from current color and combine with unit foreground
                    if self.attack_colors["aoe_red"] in current_color:
                        colors[screen_y][screen_x] = self.attack_colors["aoe_red"] + unit_color
                    else:
                        colors[screen_y][screen_x] = self.attack_colors["range_subtle"] + unit_color
                else:
                    # No attack background, use normal unit colors
                    color = self.team_colors.get(item.team, "")
                    
                    # Apply special highlighting for targets
                    if item.highlight_type == "target":
                        color = "\033[7;31m"  # Inverted red for targetable enemies
                    elif not item.is_active:
                        color = "\033[90m"  # Dark gray for inactive units
                        
                    colors[screen_y][screen_x] = color
                
            elif isinstance(item, CursorRenderData):
                # Store cursor position for special rendering after all items
                # This prevents cursor blink from affecting panel display
                self._cursor_position = (screen_x, screen_y)
                
            elif isinstance(item, MenuRenderData):
                # Don't render action menus here - they're handled by the sidebar
                if item.title != "Actions":
                    self._render_menu_on_grid(item, grid, colors)
                
            elif isinstance(item, BattleForecastRenderData):
                # Render battle forecast popup
                self._render_battle_forecast_on_grid(item, grid, colors)
                
            elif isinstance(item, DialogRenderData):
                # Render confirmation dialog
                self._render_dialog_on_grid(item, grid, colors)
                
            elif isinstance(item, BannerRenderData):
                # Render phase banner
                self._render_banner_on_grid(item, grid, colors)
                
            elif isinstance(item, OverlayRenderData):
                # Render full-screen overlay
                self._render_overlay_on_grid(item, grid, colors)
    
    def _render_menu_on_grid(self, menu: MenuRenderData, grid: list[list[str]], colors: list[list[str]]) -> None:
        """Render menu directly onto the character grid."""
        menu_lines = []
        menu_lines.append('┌' + '─' * (menu.width - 2) + '┐')
        
        if menu.title:
            title_line = '│ ' + menu.title.center(menu.width - 4) + ' │'
            menu_lines.append(title_line)
            menu_lines.append('├' + '─' * (menu.width - 2) + '┤')
        
        for i, item in enumerate(menu.items):
            # Only show selection marker for the selected line, and only if not indented
            is_selected = (i == menu.selected_index)
            is_indented = item.startswith('  ')  # Description lines start with 2 spaces
            
            if is_selected and not is_indented:
                prefix = '>'
            else:
                prefix = ' '
                
            item_text = f" {prefix} {item}"
            item_line = '│' + item_text.ljust(menu.width - 2) + '│'
            menu_lines.append(item_line)
        
        menu_lines.append('└' + '─' * (menu.width - 2) + '┘')
        
        # Render menu lines onto the grid
        for i, menu_line in enumerate(menu_lines):
            grid_y = menu.y + i
            if 0 <= grid_y < len(grid):
                for j, char in enumerate(menu_line):
                    grid_x = menu.x + j
                    if 0 <= grid_x < len(grid[grid_y]):
                        grid[grid_y][grid_x] = char
                        # Add background color for menu
                        colors[grid_y][grid_x] = "\033[47;30m"  # White background, black text
    
    def _render_battle_forecast_on_grid(self, forecast: BattleForecastRenderData, grid: list[list[str]], colors: list[list[str]]) -> None:
        """Render battle forecast popup onto the character grid."""
        forecast_lines = []
        forecast_lines.append('┌' + '─' * (forecast.width - 2) + '┐')
        forecast_lines.append('│ Battle Forecast          │')
        forecast_lines.append('├' + '─' * (forecast.width - 2) + '┤')
        
        # Unit matchup line
        matchup = f'│ {forecast.attacker_name} ▶ {forecast.defender_name}'
        forecast_lines.append(matchup[:forecast.width-2].ljust(forecast.width-2) + '│')
        
        # Damage range line
        if forecast.min_damage == forecast.max_damage:
            damage_text = f'│ Dmg: {forecast.damage}  Hit: {forecast.hit_chance}%'
        else:
            damage_text = f'│ Dmg: {forecast.min_damage}-{forecast.max_damage}  Hit: {forecast.hit_chance}%'
        forecast_lines.append(damage_text[:forecast.width-2].ljust(forecast.width-2) + '│')
        
        # Crit and counter info
        crit_counter_text = f'│ Crit: {forecast.crit_chance}%  Counter: {"Yes" if forecast.can_counter else "No"}'
        forecast_lines.append(crit_counter_text[:forecast.width-2].ljust(forecast.width-2) + '│')
        
        # Counter damage line if applicable
        if forecast.can_counter:
            if forecast.counter_min_damage == forecast.counter_max_damage:
                counter_text = f'│ Counter Dmg: {forecast.counter_damage}'
            else:
                counter_text = f'│ Counter Dmg: {forecast.counter_min_damage}-{forecast.counter_max_damage}'
            forecast_lines.append(counter_text[:forecast.width-2].ljust(forecast.width-2) + '│')
        
        forecast_lines.append('└' + '─' * (forecast.width - 2) + '┘')
        
        # Render forecast lines onto the grid
        for i, forecast_line in enumerate(forecast_lines):
            grid_y = forecast.y + i
            if 0 <= grid_y < len(grid):
                for j, char in enumerate(forecast_line):
                    grid_x = forecast.x + j
                    if 0 <= grid_x < len(grid[grid_y]):
                        grid[grid_y][grid_x] = char
                        # Add background color for forecast popup
                        colors[grid_y][grid_x] = "\033[43;30m"  # Yellow background, black text
    
    def _render_dialog_on_grid(self, dialog: DialogRenderData, grid: list[list[str]], colors: list[list[str]]) -> None:
        """Render confirmation dialog onto the character grid."""
        dialog_lines = []
        dialog_lines.append('┌' + '─' * (dialog.width - 2) + '┐')
        dialog_lines.append(f'│ {dialog.title.center(dialog.width - 4)} │')
        dialog_lines.append('├' + '─' * (dialog.width - 2) + '┤')
        dialog_lines.append(f'│ {dialog.message.center(dialog.width - 4)} │')
        
        # Options line with selection highlighting
        options_text = f"  {dialog.options[0]}     {dialog.options[1]}"
        if dialog.selected_option == 0:
            options_text = f"> {dialog.options[0]}     {dialog.options[1]}"
        else:
            options_text = f"  {dialog.options[0]}   > {dialog.options[1]}"
        dialog_lines.append(f'│{options_text.center(dialog.width - 2)}│')
        dialog_lines.append('└' + '─' * (dialog.width - 2) + '┘')
        
        # Render dialog lines onto the grid
        for i, dialog_line in enumerate(dialog_lines):
            grid_y = dialog.y + i
            if 0 <= grid_y < len(grid):
                for j, char in enumerate(dialog_line):
                    grid_x = dialog.x + j
                    if 0 <= grid_x < len(grid[grid_y]):
                        grid[grid_y][grid_x] = char
                        # Add background color for dialog
                        colors[grid_y][grid_x] = "\033[46;30m"  # Cyan background, black text
    
    def _render_banner_on_grid(self, banner: BannerRenderData, grid: list[list[str]], colors: list[list[str]]) -> None:
        """Render phase banner onto the character grid."""
        # Calculate opacity-based color
        opacity = banner.opacity
        if opacity <= 0:
            return  # Don't render invisible banner
        
        banner_lines = []
        banner_lines.append('┌' + '─' * (banner.width - 2) + '┐')
        banner_lines.append(f'│{banner.text.center(banner.width - 2)}│')
        banner_lines.append('└' + '─' * (banner.width - 2) + '┘')
        
        # Choose color based on opacity (fade effect)
        if opacity > 0.7:
            banner_color = "\033[42;37m"  # Bright green background, white text
        elif opacity > 0.3:
            banner_color = "\033[102;30m"  # Light green background, black text  
        else:
            banner_color = "\033[100;37m"  # Dark gray background, white text
        
        # Render banner lines onto the grid
        for i, banner_line in enumerate(banner_lines):
            grid_y = banner.y + i
            if 0 <= grid_y < len(grid):
                for j, char in enumerate(banner_line):
                    grid_x = banner.x + j
                    if 0 <= grid_x < len(grid[grid_y]):
                        grid[grid_y][grid_x] = char
                        colors[grid_y][grid_x] = banner_color
    
    def _render_overlay_on_grid(self, overlay: OverlayRenderData, grid: list[list[str]], colors: list[list[str]]) -> None:
        """Render full-screen overlay onto the character grid."""
        # Clear the area behind the overlay
        for y in range(overlay.y, min(overlay.y + overlay.height, len(grid))):
            for x in range(overlay.x, min(overlay.x + overlay.width, len(grid[0]))):
                grid[y][x] = ' '
                colors[y][x] = "\033[48;5;19;37m"  # Dark blue background, white text
        
        # Render border
        for i in range(overlay.width):
            # Top border
            if overlay.y < len(grid):
                grid[overlay.y][overlay.x + i] = '─'
            # Bottom border  
            if overlay.y + overlay.height - 1 < len(grid):
                grid[overlay.y + overlay.height - 1][overlay.x + i] = '─'
        
        for i in range(overlay.height):
            # Left border
            if overlay.y + i < len(grid):
                grid[overlay.y + i][overlay.x] = '│'
            # Right border
            if overlay.y + i < len(grid):
                grid[overlay.y + i][overlay.x + overlay.width - 1] = '│'
        
        # Corners
        if overlay.y < len(grid):
            grid[overlay.y][overlay.x] = '┌'
            grid[overlay.y][overlay.x + overlay.width - 1] = '┐'
        if overlay.y + overlay.height - 1 < len(grid):
            grid[overlay.y + overlay.height - 1][overlay.x] = '└'
            grid[overlay.y + overlay.height - 1][overlay.x + overlay.width - 1] = '┘'
        
        # Title
        if overlay.title:
            title_line = f" {overlay.title} "
            title_x = overlay.x + (overlay.width - len(title_line)) // 2
            if overlay.y < len(grid):
                for i, char in enumerate(title_line):
                    if title_x + i < overlay.x + overlay.width - 1:
                        grid[overlay.y][title_x + i] = char
        
        # Content
        for i, line in enumerate(overlay.content[:overlay.height-3]):  # Leave room for borders and title
            content_y = overlay.y + 2 + i
            if content_y < overlay.y + overlay.height - 1:
                line_text = line[:overlay.width-4]  # Leave room for borders
                for j, char in enumerate(line_text):
                    grid[content_y][overlay.x + 2 + j] = char
    
    def _render_menu_on_lines(self, menu: MenuRenderData, display_lines: list[str]):
        menu_lines = []
        menu_lines.append('┌' + '─' * (menu.width - 2) + '┐')
        
        if menu.title:
            title_line = '│ ' + menu.title.center(menu.width - 4) + ' │'
            menu_lines.append(title_line)
            menu_lines.append('├' + '─' * (menu.width - 2) + '┤')
        
        for i, item in enumerate(menu.items):
            prefix = '>' if i == menu.selected_index else ' '
            item_text = f" {prefix} {item}"
            item_line = '│' + item_text.ljust(menu.width - 2) + '│'
            menu_lines.append(item_line)
        
        menu_lines.append('└' + '─' * (menu.width - 2) + '┘')
        
        # Overlay menu on the display lines
        for i, menu_line in enumerate(menu_lines):
            line_idx = menu.y + i
            if 0 <= line_idx < len(display_lines):
                # Get the current line and overlay the menu
                current_line = display_lines[line_idx]
                # Ensure line is long enough
                if len(current_line) < menu.x:
                    current_line = current_line.ljust(menu.x)
                # Replace the portion of the line with the menu
                new_line = current_line[:menu.x] + menu_line
                if menu.x + len(menu_line) < len(current_line):
                    new_line += current_line[menu.x + len(menu_line):]
                display_lines[line_idx] = new_line
    
    
    def get_input_events(self) -> list[InputEvent]:
        events = []
        
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            
            if key == '\x1b':
                next_chars = sys.stdin.read(2)
                
                if next_chars == '[A':
                    events.append(InputEvent.key_press(Key.UP))
                elif next_chars == '[B':  
                    events.append(InputEvent.key_press(Key.DOWN))
                elif next_chars == '[C':
                    events.append(InputEvent.key_press(Key.RIGHT))
                elif next_chars == '[D':
                    events.append(InputEvent.key_press(Key.LEFT))
                else:
                    events.append(InputEvent.key_press(Key.ESCAPE))
            
            elif key == '\r' or key == '\n':
                events.append(InputEvent.key_press(Key.ENTER))
            elif key == ' ':
                events.append(InputEvent.key_press(Key.SPACE))
            elif key == '\t':
                events.append(InputEvent.key_press(Key.TAB))
            elif key == 'q' or key == 'Q':
                events.append(InputEvent.key_press(Key.Q))
            # Strategic action keys (handle before movement to avoid conflicts)
            elif key == 'a' or key == 'A':
                events.append(InputEvent.key_press(Key.A))  # Attack
            elif key == 'w' or key == 'W':
                events.append(InputEvent.key_press(Key.W))  # Wait
            elif key == 'e' or key == 'E':
                events.append(InputEvent.key_press(Key.E))  # End turn
            elif key == 'o' or key == 'O':
                events.append(InputEvent.key_press(Key.O))  # Objectives
            elif key == 'm' or key == 'M':
                events.append(InputEvent.key_press(Key.M))  # Minimap
            elif key == 'l' or key == 'L':
                events.append(InputEvent.key_press(Key.L))  # Expanded log
            elif key == '?':
                events.append(InputEvent.key_press(Key.HELP))  # Help
            elif key in 'xzXZ':
                action_map = {
                    'z': Key.Z, 'Z': Key.Z,
                    'x': Key.X, 'X': Key.X,
                }
                events.append(InputEvent.key_press(action_map[key]))
            elif key.lower() in 'abcdefghijklmnopqrstuvwxyz':
                key_enum = getattr(Key, key.upper(), Key.UNKNOWN)
                events.append(InputEvent.key_press(key_enum))
        
        return events
    
    # ============== New 4-Panel Layout Rendering Methods ==============
    
    def _render_timeline_panel(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                             x_offset: int, y_offset: int, width: int, height: int) -> None:
        """Render the enhanced timeline panel for the 4-panel layout."""
        if not context.timeline or height < 2:
            return
        
        timeline = context.timeline
        
        # Title line with phase debug info
        game_phase = context.game_phase if hasattr(context, 'game_phase') else "UNKNOWN"
        battle_phase = context.battle_phase if hasattr(context, 'battle_phase') and context.battle_phase else "None"
        title = f" TIMELINE | {game_phase}/{battle_phase} "
        title_x = max(0, (width - len(title)) // 2)
        
        # Truncate title if it's too long for the panel
        if len(title) > width:
            title = f" TL | {game_phase[:4]}/{battle_phase[:4] if battle_phase != 'None' else 'None'} "
            if len(title) > width:
                title = f" TL | {game_phase[:3]} "
        
        for i, char in enumerate(title):
            if i < width and x_offset + title_x + i < len(grid[0]) and y_offset < len(grid):
                grid[y_offset][x_offset + title_x + i] = char
                colors[y_offset][x_offset + title_x + i] = self.terminal_codes["text_normal"]
        
        # Timeline entries line
        if len(timeline.entries) > 0 and height >= 2:
            entries_line = []
            for i, entry in enumerate(timeline.entries[:6]):  # Show up to 6 entries
                
                # Renderer decides icons based on unit class/action
                icon = self._get_timeline_icon(entry)
                name = entry.entity_name
                
                if entry.visibility == "hidden":
                    name = "???"
                    action = "??? Hidden Action"
                elif entry.visibility == "partial":
                    action = "???"
                else:
                    action = entry.action_description
                
                
                # Format with ticks remaining if > 0
                if entry.ticks_remaining > 0:
                    entry_text = f"[ {name} {icon} {action} ({entry.ticks_remaining} ticks) ]"
                else:
                    entry_text = f"[ {name} {icon} {action} ]"
                
                entries_line.append(entry_text)
                
                if i < len(timeline.entries) - 1:
                    entries_line.append(" → ")
            
            # Render timeline entries (truncate if too long)
            timeline_text = "".join(entries_line)[:width-2]
            for i, char in enumerate(timeline_text):
                if x_offset + 1 + i < len(grid[0]) and y_offset + 1 < len(grid):
                    grid[y_offset + 1][x_offset + 1 + i] = char
                    colors[y_offset + 1][x_offset + 1 + i] = self.terminal_codes["text_normal"]
        elif len(timeline.entries) == 0:
            # Show "No units" when there are no timeline entries
            no_entries_text = "No active units"
            for i, char in enumerate(no_entries_text):
                if x_offset + 1 + i < len(grid[0]) and y_offset + 1 < len(grid):
                    grid[y_offset + 1][x_offset + 1 + i] = char
                    colors[y_offset + 1][x_offset + 1 + i] = self.terminal_codes["text_normal"]
    
    def _get_timeline_icon(self, entry) -> str:
        """Determine timeline icon based on entry data."""
        # If renderer-specific icon is provided, use it
        if entry.icon:
            return entry.icon
        
        # Otherwise, decide based on entry data
        if entry.entity_type == "unit":
            # Determine by action first
            action_lower = entry.action_description.lower()
            if "attack" in action_lower:
                return "⚔"
            elif "move" in action_lower:
                return "🏃"
            elif "prepare" in action_lower or "ready" in action_lower:
                return "🛡"
            elif "acted" in action_lower:
                return "✓"
            else:
                return "⚔"
        elif entry.entity_type == "hazard":
            return "🔥"
        else:
            return "⏳"
    
    def _render_battlefield_panel(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                                x_offset: int, y_offset: int, width: int, height: int) -> None:
        """Render the battlefield panel (similar to the current map viewport)."""
        # This is essentially the same as the current map rendering but positioned in the center panel
        render_items = defaultdict(list)
        
        if context.tiles:
            render_items[LayerType.TERRAIN].extend(context.tiles)
        if context.overlays:
            render_items[LayerType.OVERLAY].extend(context.overlays)
        if context.attack_targets:
            render_items[LayerType.OVERLAY].extend(context.attack_targets)
        if context.units:
            render_items[LayerType.UNITS].extend(context.units)
        if context.cursor:
            render_items[LayerType.UI].append(context.cursor)
        
        # Render battlefield elements
        for layer in [LayerType.TERRAIN, LayerType.OVERLAY, LayerType.UNITS, LayerType.UI]:
            for item in render_items[layer]:
                self._render_battlefield_item(item, grid, colors, context, width, height, x_offset, y_offset)
    
    def _render_battlefield_item(self, item, grid, colors, context, max_width, max_height, x_offset=0, y_offset=0):
        """Render a single item in the battlefield panel."""
        vx = context.viewport_x
        vy = context.viewport_y
        
        screen_x = item.position.x - vx + x_offset
        screen_y = item.position.y - vy + y_offset
        
        if 0 <= screen_x - x_offset < max_width and 0 <= screen_y - y_offset < max_height:
            if isinstance(item, TileRenderData):
                symbol = self.terrain_symbols.get(item.terrain_type, "?")
                if screen_y < len(grid) and screen_x < len(grid[0]):
                    grid[screen_y][screen_x] = symbol
                    if item.highlight:
                        colors[screen_y][screen_x] = self.ui_colors.get(item.highlight, "")
                    else:
                        color = self.terrain_colors.get(item.terrain_type, "")
                        if color:
                            colors[screen_y][screen_x] = color
            
            elif isinstance(item, OverlayTileRenderData):
                # Enhanced overlay rendering with new tactical overlays
                symbol = item.symbol_override or self.ui_symbols.get(f"{item.overlay_type}_overlay", "?")
                
                # Special symbols for new overlay types
                if item.overlay_type == "charge_path" and item.direction:
                    if item.direction == "north":
                        symbol = "↑"
                    elif item.direction == "south":
                        symbol = "↓"
                    elif item.direction == "east":
                        symbol = "→"
                    elif item.direction == "west":
                        symbol = "←"
                elif item.overlay_type == "interrupt_arc":
                    symbol = "◊"  # Diamond for interrupt zones
                elif item.overlay_type == "aoe_preview":
                    symbol = "◯"  # Circle for AoE preview
                
                if screen_y < len(grid) and screen_x < len(grid[0]):
                    grid[screen_y][screen_x] = symbol
                    color = item.color_hint or self.ui_colors.get(item.overlay_type, "")
                    if color:
                        colors[screen_y][screen_x] = color
            
            elif isinstance(item, UnitRenderData):
                symbol = self.unit_symbols.get(item.unit_type.lower(), "?")
                if screen_y < len(grid) and screen_x < len(grid[0]):
                    grid[screen_y][screen_x] = symbol
                    
                    # Preserve background colors from overlays/attack targets
                    current_color = colors[screen_y][screen_x] or ""
                    unit_color = self.team_colors.get(item.team, "")
                    
                    # Check if this position has attack target background
                    has_attack_background = (self.attack_colors["range_subtle"] in current_color or 
                                           self.attack_colors["aoe_red"] in current_color)
                    
                    if has_attack_background:
                        # Preserve attack target background, set unit foreground color
                        if self.attack_colors["aoe_red"] in current_color:
                            colors[screen_y][screen_x] = self.attack_colors["aoe_red"] + self.attack_colors["text_white"]
                        else:
                            colors[screen_y][screen_x] = self.attack_colors["range_subtle"] + unit_color
                    else:
                        # No background overlay, use normal unit color
                        colors[screen_y][screen_x] = unit_color
                    
                    # Track cursor position for highlighting
                    if hasattr(context, 'cursor_x') and hasattr(context, 'cursor_y'):
                        if item.position.x == context.cursor_x and item.position.y == context.cursor_y:
                            self._cursor_position = (screen_x, screen_y)
            
            elif isinstance(item, CursorRenderData):
                # Render cursor in battlefield
                if screen_y < len(grid) and screen_x < len(grid[0]):
                    # Store cursor position for later highlighting
                    self._cursor_position = (screen_x, screen_y)
            
            elif hasattr(item, 'target_type'):  # AttackTargetRenderData
                # Handle AOE and attack target overlays
                if screen_y < len(grid) and screen_x < len(grid[0]):
                    # Store original color before modifying
                    original_color = colors[screen_y][screen_x]
                    
                    if item.target_type == "range":
                        # Subtle dark red background for attack range
                        colors[screen_y][screen_x] = self.attack_colors["range_subtle"] + original_color
                    elif item.target_type == "aoe":
                        # AOE tiles: blink between normal and red background with white symbol
                        if item.blink_phase:
                            colors[screen_y][screen_x] = self.attack_colors["aoe_red"] + self.attack_colors["text_white"]
                        else:
                            colors[screen_y][screen_x] = self.attack_colors["range_subtle"] + original_color
                    elif item.target_type == "selected":
                        # Selected tile: blink between normal and red background with black X
                        if item.blink_phase:
                            grid[screen_y][screen_x] = "X"
                            colors[screen_y][screen_x] = self.attack_colors["aoe_red"] + self.attack_colors["text_black"]
                        else:
                            colors[screen_y][screen_x] = self.attack_colors["range_subtle"] + original_color
                    elif item.target_type == "aoe_preview":
                        # AoE preview overlay
                        colors[screen_y][screen_x] = self.attack_colors["aoe_red"] + self.attack_colors["text_white"]
    
    def _render_unit_info_panel(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                              x_offset: int, y_offset: int, width: int, height: int) -> None:
        """Render the unit info panel for the 4-panel layout."""
        panel = context.unit_info_panel
        if not panel or height < 4:
            return
        
        lines = []
        
        # Check if this is tile info (HP = 0) or unit info  
        is_tile_info = (panel.hp_max == 0)
        
        if is_tile_info:
            # Tile information display
            lines.append(f"{panel.unit_name}")  # "Tile Info"
            lines.append(f"{panel.unit_class}")  # Terrain name
            
            # Show tile properties (stored in status_effects)
            if panel.status_effects:
                for prop in panel.status_effects:
                    lines.append(prop)
        else:
            # Unit information display  
            lines.append(f"{panel.unit_name} — {panel.unit_class}")
            
            # HP and mana
            hp_line = panel.get_hp_display()
            if panel.has_mana:
                mana_line = panel.get_mana_display()
                lines.append(f"{hp_line}     {mana_line}")
            else:
                lines.append(hp_line)
            
            # Status effects
            if panel.status_effects:
                lines.append(f"Status: {', '.join(panel.status_effects)}")
            
            # Wounds
            if panel.wounds:
                lines.append(f"Wounds: {', '.join(panel.wounds)}")
            
            # Next action
            lines.append(panel.get_next_action_display())
        
        # Render lines
        for i, line in enumerate(lines[:height-1]):  # Leave space for borders
            if y_offset + i < len(grid):
                display_line = line[:width-2]  # Leave space for borders
                for j, char in enumerate(display_line):
                    if x_offset + 1 + j < len(grid[0]):
                        grid[y_offset + i][x_offset + 1 + j] = char
                        colors[y_offset + i][x_offset + 1 + j] = self.terminal_codes["text_normal"]
    
    def _render_action_menu_panel(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                                x_offset: int, y_offset: int, width: int, height: int) -> None:
        """Render the action menu panel for the 4-panel layout."""
        panel = context.action_menu_panel
        if not panel or height < 3:
            return
        
        # Title (compact, inline with first item if needed for space)
        title = "Actions"
        title_line = f"{title}:"
        if y_offset < len(grid):
            for i, char in enumerate(title_line):
                if x_offset + 1 + i < len(grid[0]):
                    grid[y_offset][x_offset + 1 + i] = char
                    colors[y_offset][x_offset + 1 + i] = self.terminal_codes["text_dim"]
        
        # Action items - use all available height minus title line
        display_lines = panel.get_display_lines()
        available_lines = height - 1  # Only reserve 1 line for title
        
        for i, line in enumerate(display_lines[:available_lines]):
            if y_offset + 1 + i < len(grid):
                # Reduce indentation - only 2 spaces from edge
                indent = 2
                # Trim line to fit width
                max_line_width = width - indent - 1
                display_line = line[:max_line_width]
                
                # Clear the line first to remove old content
                for x in range(x_offset, min(x_offset + width, len(grid[0]))):
                    grid[y_offset + 1 + i][x] = ' '
                
                # Write the action text
                for j, char in enumerate(display_line):
                    if x_offset + indent + j < len(grid[0]):
                        grid[y_offset + 1 + i][x_offset + indent + j] = char
                        # Highlight selected item
                        if i == panel.selected_index:
                            colors[y_offset + 1 + i][x_offset + indent + j] = self.terminal_codes["text_success"]
                        else:
                            colors[y_offset + 1 + i][x_offset + indent + j] = self.terminal_codes["text_normal"]
    
    def _render_log_panel(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]],
                         x_offset: int, y_offset: int, width: int, height: int) -> None:
        """Render the message log panel."""
        if not context.log_panel or width <= 2 or height <= 2:
            return
        
        panel = context.log_panel
        
        # Bounds checking
        if x_offset < 0 or y_offset < 0 or x_offset >= len(grid[0]) or y_offset >= len(grid):
            return
        
        # Adjust dimensions to fit within grid
        max_width = min(width, len(grid[0]) - x_offset)
        max_height = min(height, len(grid) - y_offset)
        
        if max_width <= 2 or max_height <= 2:
            return
        
        # Draw panel border using adjusted dimensions
        for y in range(max_height):
            for x in range(max_width):
                grid_y = y_offset + y
                grid_x = x_offset + x
                
                if grid_y >= len(grid) or grid_x >= len(grid[0]):
                    continue
                
                # Top and bottom borders
                if y == 0 or y == max_height - 1:
                    grid[grid_y][grid_x] = '─'
                    colors[grid_y][grid_x] = self.terminal_codes["text_dim"]
                # Left and right borders
                elif x == 0 or x == max_width - 1:
                    grid[grid_y][grid_x] = '│'
                    colors[grid_y][grid_x] = self.terminal_codes["text_dim"]
        
        # Corners
        if y_offset < len(grid) and x_offset < len(grid[0]):
            grid[y_offset][x_offset] = '╭'
            colors[y_offset][x_offset] = self.terminal_codes["text_dim"]
        if y_offset < len(grid) and x_offset + max_width - 1 < len(grid[0]):
            grid[y_offset][x_offset + max_width - 1] = '╮'
            colors[y_offset][x_offset + max_width - 1] = self.terminal_codes["text_dim"]
        if y_offset + max_height - 1 < len(grid) and x_offset < len(grid[0]):
            grid[y_offset + max_height - 1][x_offset] = '╰'
            colors[y_offset + max_height - 1][x_offset] = self.terminal_codes["text_dim"]
        if y_offset + max_height - 1 < len(grid) and x_offset + max_width - 1 < len(grid[0]):
            grid[y_offset + max_height - 1][x_offset + max_width - 1] = '╯'
            colors[y_offset + max_height - 1][x_offset + max_width - 1] = self.terminal_codes["text_dim"]
        
        # Render title
        title = f" {panel.title} "
        title_x = x_offset + 2
        for i, char in enumerate(title):
            if title_x + i < x_offset + max_width - 2 and title_x + i < len(grid[0]):
                grid[y_offset][title_x + i] = char
                colors[y_offset][title_x + i] = self.terminal_codes["text_bright"]
        
        # Add scroll indicators if needed
        if panel.can_scroll_up() and max_width > 5:
            scroll_up = " ▲ "
            scroll_x = x_offset + max_width - 5
            for i, char in enumerate(scroll_up):
                if scroll_x + i < x_offset + max_width - 1 and scroll_x + i < len(grid[0]):
                    grid[y_offset][scroll_x + i] = char
                    colors[y_offset][scroll_x + i] = self.terminal_codes["text_yellow"]
        
        if panel.can_scroll_down() and max_width > 5:
            scroll_down = " ▼ "
            scroll_x = x_offset + max_width - 5
            for i, char in enumerate(scroll_down):
                if scroll_x + i < x_offset + max_width - 1 and scroll_x + i < len(grid[0]):
                    grid[y_offset + max_height - 1][scroll_x + i] = char
                    colors[y_offset + max_height - 1][scroll_x + i] = self.terminal_codes["text_yellow"]
        
        # Render messages
        messages = panel.get_visible_messages()
        content_start_y = y_offset + 1
        content_width = max_width - 2  # Account for borders
        
        # Category color mapping
        category_colors = {
            "[SYS]": self.terminal_codes["text_normal"],
            "[BTL]": self.terminal_codes["text_red"],
            "[MOV]": self.terminal_codes["text_cyan"],
            "[AI]": self.terminal_codes["text_magenta"],
            "[TML]": self.terminal_codes["text_blue"],
            "[INP]": self.terminal_codes["text_green"],
            "[DBG]": self.terminal_codes["text_dim"],
            "[WRN]": self.terminal_codes["text_yellow"],
            "[ERR]": self.terminal_codes["text_bright_red"],
            "[OBJ]": self.terminal_codes["text_bright_green"],
            "[INT]": self.terminal_codes["text_bright_cyan"],
            "[SCN]": self.terminal_codes["text_bright_blue"],
            "[UI]": self.terminal_codes["text_white"],
        }
        
        for i, message in enumerate(messages):
            message_y = content_start_y + i
            if message_y >= y_offset + max_height - 1:
                break  # Don't overwrite bottom border
            
            # Truncate message if too long
            if len(message) > content_width and content_width > 3:
                message = message[:content_width - 3] + "..."
            
            # Find category tag color
            message_color = self.terminal_codes["text_normal"]
            for tag, color in category_colors.items():
                if message.startswith(tag):
                    message_color = color
                    break
            
            # Render the message
            for j, char in enumerate(message):
                message_x = x_offset + 1 + j
                if message_x < x_offset + max_width - 1 and message_x < len(grid[0]) and message_y < len(grid):
                    grid[message_y][message_x] = char
                    colors[message_y][message_x] = message_color
    
