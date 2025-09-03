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
    OverlayRenderData, AttackTargetRenderData, LayerType
)
from ..core.input import InputEvent, Key
from ..core.tileset_loader import get_tileset_config


class TerminalRenderer(Renderer):
    
    def __init__(self, config: Optional[RendererConfig] = None):
        super().__init__(config)
        self._old_settings = None
        self._buffer = []
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
            "text_success": "\033[92m",     # Green
            "text_warning": "\033[93m",     # Yellow
            "text_error": "\033[91m"        # Red
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
        
        # Check if we have battle-specific content (world dimensions indicate battle phase)
        is_battle_phase = context.world_width > 0 and context.world_height > 0
        
        if is_battle_phase:
            # Battle phase: render with 3-panel layout
            self._render_battle_layout(context, grid, colors, screen_width, screen_height)
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
            
        # Calculate viewport dimensions
        map_viewport_width = screen_width - self.sidebar_width
        map_viewport_height = screen_height - self.bottom_strip_height
        
        # Render map viewport (left side)
        self._render_map_viewport(context, grid, colors, map_viewport_width, map_viewport_height)
        
        # Draw vertical separator between map and sidebar
        for y in range(map_viewport_height):
            grid[y][map_viewport_width] = '│'
            colors[y][map_viewport_width] = self.terminal_codes["text_dim"]
        
        # Render sidebar panels (right side)
        self._render_sidebar(context, grid, colors, map_viewport_width + 1, 0, 
                           self.sidebar_width - 1, map_viewport_height)
        
        # Draw horizontal separator above bottom strip
        for x in range(screen_width):
            grid[map_viewport_height][x] = '─'
            colors[map_viewport_height][x] = self.terminal_codes["text_dim"]
        
        # Render bottom message strip
        self._render_message_strip(context, grid, colors, 0, map_viewport_height + 1, 
                                 screen_width, self.bottom_strip_height - 1)
        
        # Apply cursor effect AFTER panels are rendered (only to map area)
        if hasattr(self, '_cursor_position') and self._cursor_position:
            cx, cy = self._cursor_position
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
        if context.dialog:
            self._render_dialog_on_grid(context.dialog, grid, colors)
        
        if context.overlay:
            self._render_overlay_on_grid(context.overlay, grid, colors)
    
    def _render_map_viewport(self, context: RenderContext, grid: list[list[str]], colors: list[list[str]], 
                           width: int, height: int) -> None:
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
                self._render_item(item, grid, colors, context, width, height)
    
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
            if tile.x == cursor_x and tile.y == cursor_y:
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
        panel_height = 9 if compact else 11  # Reduced when compact
        
        # Draw panel border
        self._draw_box(grid, colors, x_offset, y_offset, width, panel_height, "Unit")
        
        # Find unit at cursor position (always available)
        cursor_x, cursor_y = context.cursor_x, context.cursor_y
        unit = None
        
        for u in context.units:
            if u.x == cursor_x and u.y == cursor_y:
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
        self._draw_text(grid, f"Phase: {current_team_name}", x_offset + 2, y_offset + 3, width - 4, "", colors)
        
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
    
    def _draw_text(self, grid: list[list[str]], text: str, x: int, y: int, max_width: int, color: str = "", colors: list[list[str]] = None) -> None:
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
    
    def _render_item(self, item, grid, colors, context, max_width=None, max_height=None):
        vx = context.viewport_x
        vy = context.viewport_y
        vw = max_width if max_width else self.config.width
        vh = max_height if max_height else self.config.height - 3
        
        screen_x = item.x - vx
        screen_y = item.y - vy
        
        if 0 <= screen_x < vw and 0 <= screen_y < vh:
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
                # Store original symbol and color before modifying
                original_symbol = grid[screen_y][screen_x]
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
        forecast_lines.append('│ Battle Forecast    │')
        forecast_lines.append('├' + '─' * (forecast.width - 2) + '┤')
        forecast_lines.append(f'│ {forecast.attacker_name} ▶ {forecast.defender_name}   │'[:forecast.width-2].ljust(forecast.width-2) + '│')
        forecast_lines.append(f'│ Dmg {forecast.damage}  Hit {forecast.hit_chance}%   │'[:forecast.width-2].ljust(forecast.width-2) + '│')
        forecast_lines.append(f'│ Crit {forecast.crit_chance}%  Cntr {"Yes" if forecast.can_counter else "No"} │'[:forecast.width-2].ljust(forecast.width-2) + '│')
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
                colors[y][x] = "\033[44;37m"  # Blue background, white text
        
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
                events.append(InputEvent.quit_event())
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
            elif key == '?':
                events.append(InputEvent.key_press(Key.HELP))  # Help
            # Movement keys (only s and d now, since a and w are handled above)
            elif key in 'sdSD':
                direction_map = {
                    's': Key.DOWN, 'S': Key.DOWN,
                    'd': Key.RIGHT, 'D': Key.RIGHT,
                }
                events.append(InputEvent.key_press(direction_map[key]))
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
    
