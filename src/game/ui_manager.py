"""
UI management system for overlays, dialogs, banners, and modal interfaces.

This module handles all modal UI elements including objectives overlay,
help screens, minimap, confirmation dialogs, and ephemeral banners.
"""
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .map import GameMap
    from .scenario import Scenario
    from ..core.game_state import GameState
    from ..core.renderer import Renderer
    from ..core.renderable import (
        BannerRenderData,
        BattleForecastRenderData,
        DialogRenderData,
        OverlayRenderData,
    )

from ..core.renderable import (
    BannerRenderData,
    BattleForecastRenderData, 
    DialogRenderData,
    OverlayRenderData,
)


class UIManager:
    """Manages all modal UI elements and overlays."""
    
    def __init__(
        self,
        game_map: "GameMap",
        game_state: "GameState",
        renderer: "Renderer",
        scenario: Optional["Scenario"] = None
    ):
        self.game_map = game_map
        self.state = game_state
        self.renderer = renderer
        self.scenario = scenario
        
        # Banner timing system
        self.game_start_time = time.time()
        self.active_banner: Optional[str] = None
        self.banner_start_time = 0
        self.banner_duration_ms = 2000  # Default banner duration
    
    def set_scenario(self, scenario: "Scenario") -> None:
        """Update the scenario reference."""
        self.scenario = scenario
    
    # Overlay management
    def show_objectives(self) -> None:
        """Show the objectives overlay."""
        self.state.open_overlay("objectives")
    
    def show_help(self) -> None:
        """Show the help overlay."""
        self.state.open_overlay("help")
    
    def show_minimap(self) -> None:
        """Show the minimap overlay."""
        self.state.open_overlay("minimap")
    
    def close_overlay(self) -> None:
        """Close the currently active overlay."""
        self.state.close_overlay()
    
    # Banner management
    def show_banner(self, text: str, duration_ms: int = 2000) -> None:
        """Show an ephemeral banner with the given text."""
        self.active_banner = text
        self.banner_start_time = time.time()
        self.banner_duration_ms = duration_ms
    
    def update_banner_timing(self) -> None:
        """Update banner timing and clear expired banners."""
        if self.active_banner:
            elapsed_ms = (time.time() - self.banner_start_time) * 1000
            duration = getattr(self, "banner_duration_ms", 2000)  # Default if not set
            if elapsed_ms >= duration:
                self.active_banner = None
    
    # UI builders for render context
    def build_objectives_overlay(self) -> OverlayRenderData:
        """Build objectives overlay content."""
        if not self.scenario:
            return OverlayRenderData(
                overlay_type="objectives",
                width=60,
                height=15,
                title="Mission Objectives",
                content=["No scenario loaded"],
            )
        
        content = []
        content.append("VICTORY CONDITIONS:")
        
        if self.scenario.victory_objectives:
            for i, obj in enumerate(self.scenario.victory_objectives, 1):
                status_symbol = "✓" if obj.status.name == "COMPLETED" else "◯"
                content.append(f"  {i}. {status_symbol} {obj.description}")
        else:
            content.append("  None defined")
        
        content.append("")
        content.append("DEFEAT CONDITIONS:")
        
        if self.scenario.defeat_objectives:
            for i, obj in enumerate(self.scenario.defeat_objectives, 1):
                status_symbol = "✗" if obj.status.name == "FAILED" else "◯"
                content.append(f"  {i}. {status_symbol} {obj.description}")
        else:
            content.append("  None defined")
        
        # Add scenario info
        if self.scenario.settings.turn_limit:
            content.append("")
            content.append(f"Turn Limit: {self.scenario.settings.turn_limit}")
            content.append(f"Current Turn: {self.state.current_turn}")
        
        content.append("")
        content.append("Press any key to continue...")
        
        # Calculate overlay size
        max_width = max(len(line) for line in content) + 4  # Padding
        overlay_width = min(max_width, 70)  # Don't exceed 70 chars
        overlay_height = min(len(content) + 4, 20)  # Don't exceed 20 lines
        
        return OverlayRenderData(
            overlay_type="objectives",
            width=overlay_width,
            height=overlay_height,
            title="Mission Objectives",
            content=content,
        )
    
    def build_help_overlay(self) -> OverlayRenderData:
        """Build comprehensive help overlay with key bindings."""
        content = [
            "GRIMDARK SRPG - CONTROLS REFERENCE",
            "",
            "═══ MOVEMENT & NAVIGATION ═══",
            "  Arrow Keys    - Move cursor",
            "  S, D          - Move cursor (down, right)",
            "  Enter/Space   - Confirm selection",
            "  Esc/X/Q       - Cancel/Back",
            "",
            "═══ COMBAT ACTIONS ═══",
            "  A             - Direct Attack",
            "  W             - Wait (end unit turn)",
            "  Tab           - Cycle through units",
            "",
            "═══ TURN MANAGEMENT ═══",
            "  E             - End Turn (with confirmation)",
            "",
            "═══ INFORMATION SCREENS ═══",
            "  O             - Mission Objectives",
            "  ?             - Help (this screen)",
            "  M             - Minimap",
            "",
            "═══ GAME FLOW ═══",
            "1. Select a unit (Enter on unit)",
            "2. Move unit or open Action Menu",
            "3. Choose action: Move, Attack, Item, Wait",
            "4. Confirm targeting if needed",
            "5. End turn when all units acted",
            "",
            "═══ TIPS ═══",
            "• Terrain affects movement cost & defense",
            "• High ground provides combat bonuses",
            "• Use Tab to quickly find available units",
            "• Check objectives (O) for victory conditions",
            "",
            "Press any key to continue...",
        ]
        
        # Calculate optimal overlay size
        max_width = max(len(line) for line in content) + 4
        overlay_width = min(max_width, 72)  # Leave room for screen edges
        overlay_height = min(len(content) + 4, 24)  # Leave room for screen edges
        
        return OverlayRenderData(
            overlay_type="help",
            width=overlay_width,
            height=overlay_height,
            title="Controls & Help",
            content=content,
        )
    
    def build_minimap_overlay(self) -> OverlayRenderData:
        """Build minimap overlay with compressed world view."""
        # Calculate minimap dimensions (2×1 compression)
        minimap_width = (self.game_map.width + 1) // 2  # Round up for odd widths
        minimap_height = self.game_map.height
        
        # Limit minimap size to fit in overlay
        max_minimap_width = 50  # Leave room for borders
        max_minimap_height = 15  # Leave room for other content
        
        scale_x = 1
        scale_y = 1
        
        if minimap_width > max_minimap_width:
            scale_x = (minimap_width + max_minimap_width - 1) // max_minimap_width
            minimap_width = max_minimap_width
        
        if minimap_height > max_minimap_height:
            scale_y = (minimap_height + max_minimap_height - 1) // max_minimap_height
            minimap_height = max_minimap_height
        
        # Build unit position map for quick lookup
        unit_map = {}
        for unit in self.game_map.units.values():
            if unit.is_alive:
                unit_map[(unit.x, unit.y)] = unit.team.value
        
        # Build minimap content
        content = [
            "BATTLEFIELD MINIMAP",
            "",
            "Legend: P=Player E=Enemy A=Ally N=Neutral",
            "        □=Camera View",
            "",
        ]
        
        # Generate minimap lines
        for map_y in range(0, self.game_map.height, scale_y):
            line = ""
            for map_x in range(0, self.game_map.width, scale_x * 2):
                # Sample a 2×scale_y area and determine what to show
                char = self._get_minimap_char(unit_map, map_x, map_y, scale_x, scale_y)
                
                # Check if this position is in the camera view
                screen_width, screen_height = self.renderer.get_screen_size()
                camera_left = self.state.camera_x
                camera_right = (
                    self.state.camera_x + screen_width - 28
                )  # Account for sidebar
                camera_top = self.state.camera_y
                camera_bottom = (
                    self.state.camera_y + screen_height - 3
                )  # Account for status
                
                if (
                    camera_left <= map_x < camera_right
                    and camera_top <= map_y < camera_bottom
                ):
                    char = "□"  # Camera view indicator
                
                line += char
            content.append(line)
        
        content.append("")
        content.append("Press any key to continue...")
        
        # Calculate overlay size
        overlay_width = max(len(line) for line in content) + 4
        overlay_height = len(content) + 4
        
        return OverlayRenderData(
            overlay_type="minimap",
            width=min(overlay_width, 60),
            height=min(overlay_height, 22),
            title="Minimap",
            content=content,
        )
    
    def _get_minimap_char(
        self, unit_map: dict, x: int, y: int, scale_x: int, scale_y: int
    ) -> str:
        """Get the character to display for a minimap cell."""
        # Check for units in the sampled area
        for dy in range(scale_y):
            for dx in range(scale_x * 2):  # 2×1 compression
                check_x = x + dx
                check_y = y + dy
                if (check_x, check_y) in unit_map:
                    team = unit_map[(check_x, check_y)]
                    # Return team indicator: 0=Player, 1=Enemy, 2=Ally, 3=Neutral
                    if team == 0:
                        return "P"
                    elif team == 1:
                        return "E"
                    elif team == 2:
                        return "A"
                    else:
                        return "N"
        
        # No units found, show terrain
        if x < self.game_map.width and y < self.game_map.height:
            tile = self.game_map.get_tile(x, y)
            if tile and tile.terrain_type in ["mountain", "wall"]:
                return "▲"  # Mountain/wall
            elif tile and tile.terrain_type == "water":
                return "≈"  # Water
            elif tile and tile.terrain_type == "forest":
                return "♣"  # Forest
            else:
                return "·"  # Open ground
        
        return " "  # Empty space
    
    def build_banner(self) -> Optional[BannerRenderData]:
        """Build turn/phase banner if active."""
        if not self.active_banner:
            return None
        
        elapsed_ms = int((time.time() - self.banner_start_time) * 1000)
        
        # Position banner at top-center
        screen_width = self.renderer.get_screen_size()[0]
        banner_width = min(
            len(self.active_banner) + 6, 30
        )  # Add padding, but not too wide
        banner_x = (screen_width - banner_width) // 2
        
        return BannerRenderData(
            x=banner_x,
            y=2,  # Top of screen with some margin
            width=banner_width,
            text=self.active_banner,
            duration_ms=2000,
            elapsed_ms=elapsed_ms,
        )
    
    def build_dialog(self, dialog_type: str) -> DialogRenderData:
        """Build confirmation dialog."""
        if dialog_type == "confirm_end_turn":
            return DialogRenderData(
                x=20,
                y=10,  # Will be centered by renderer
                width=24,
                height=6,
                title="Confirm",
                message="End Player Turn?",
                options=["Yes", "No"],
                selected_option=self.state.get_dialog_selection(),
            )
        elif dialog_type == "confirm_friendly_fire":
            friendly_fire_message = self.state.state_data.get(
                "friendly_fire_message", "This attack will hit friendly units!"
            )
            # Calculate dialog width based on message length
            dialog_width = min(max(len(friendly_fire_message) + 4, 30), 60)
            return DialogRenderData(
                x=20,
                y=10,  # Will be centered by renderer
                width=dialog_width,
                height=7,
                title="Friendly Fire Warning",
                message=friendly_fire_message,
                options=["Attack Anyway", "Cancel"],
                selected_option=self.state.get_dialog_selection(),
            )
        
        # Default dialog
        return DialogRenderData(
            x=20,
            y=10,
            width=24,
            height=6,
            title="Confirm",
            message="Are you sure?",
            options=["Yes", "No"],
            selected_option=self.state.get_dialog_selection(),
        )
    
    def build_battle_forecast(self) -> BattleForecastRenderData:
        """Build battle forecast popup."""
        # Placeholder implementation - will be enhanced when targeting is implemented
        return BattleForecastRenderData(
            x=10,
            y=5,  # Will be positioned by calculator
            attacker_name="Knight",
            defender_name="Archer",
            damage=15,
            hit_chance=85,
            crit_chance=12,
            can_counter=True,
            counter_damage=8,
        )