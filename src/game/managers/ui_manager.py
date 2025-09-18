"""
UI management system for overlays, dialogs, banners, and modal interfaces.

This module handles all modal UI elements including objectives overlay,
help screens, minimap, confirmation dialogs, and ephemeral banners.
"""

import time
from typing import TYPE_CHECKING, Optional

from ...core.data.data_structures import Vector2
from ...core.events.events import BattlePhaseChanged, GameEvent, GamePhaseChanged

if TYPE_CHECKING:
    from ...core.events.event_manager import EventManager
    from ...core.engine.game_state import GameState
    from ...core.entities.renderable import (
        BannerRenderData,
        BattleForecastRenderData,
        DialogRenderData,
        OverlayRenderData,
    )
    from ...core.renderer import Renderer
    from ..map import GameMap
    from ..scenarios.scenario import Scenario

from ...core.events.events import (
    LogMessage,
    ManagerInitialized,
    UIStateChanged,
    UnitTurnEnded,
)
from ...core.entities.renderable import (
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
        event_manager: "EventManager",
        scenario: Optional["Scenario"] = None,
    ):
        self.game_map = game_map
        self.state = game_state
        self.renderer = renderer
        self.event_manager = event_manager
        self.scenario = scenario

        # Banner timing system
        self.game_start_time = time.time()
        self.active_banner: Optional[str] = None
        self.banner_start_time = 0
        self.banner_duration_ms = 2000  # Default banner duration

        # Subscribe to phase change events to manage UI automatically
        from ...core.events.events import EventType

        self.event_manager.subscribe(
            EventType.BATTLE_PHASE_CHANGED,
            self._handle_battle_phase_changed,
            subscriber_name="UIManager.battle_phase_changed",
        )
        self.event_manager.subscribe(
            EventType.GAME_PHASE_CHANGED,
            self._handle_game_phase_changed,
            subscriber_name="UIManager.game_phase_changed",
        )
        self.event_manager.subscribe(
            EventType.UNIT_TURN_ENDED,
            self._handle_unit_turn_ended,
            subscriber_name="UIManager.unit_turn_ended",
        )

        # Emit initialization event
        self.event_manager.publish(
            ManagerInitialized(turn=0, manager_name="UIManager"), source="UIManager"
        )

    def _handle_battle_phase_changed(self, event: GameEvent) -> None:
        """Handle battle phase changes to automatically manage UI elements."""
        assert isinstance(event, BattlePhaseChanged), f"Expected BattlePhaseChanged, got {type(event)}"

        # Debug logging

        # Convert string phase back to enum for comparison
        new_phase_name = event.new_phase

        if new_phase_name == "UNIT_ACTION_SELECTION":
            # Open action menu when entering action selection phase
            if event.unit_id:
                unit = self.game_map.get_unit(event.unit_id)
                if unit:
                    # Build action menu for the unit
                    from ...core.engine.actions import get_available_actions

                    actions = get_available_actions(unit)
                    action_names = []
                    for action in actions:
                        if not any(
                            keyword in action.name for keyword in ["Move", "Quick Move"]
                        ):
                            action_names.append(action.name)

                    if "Wait" not in action_names:
                        action_names.append("Wait")

                    # Open the action menu
                    self.state.ui.open_action_menu(action_names)

        elif new_phase_name in ["TIMELINE_PROCESSING", "UNIT_MOVING"]:
            # Close action menu when leaving action selection phase
            if self.state.ui.is_action_menu_open():
                self.state.ui.close_action_menu()

    def _handle_game_phase_changed(self, event: GameEvent) -> None:
        """Handle game phase changes to show Game Over dialog when appropriate."""
        assert isinstance(event, GamePhaseChanged), f"Expected GamePhaseChanged, got {type(event)}"
        
        # Early return if not transitioning to GAME_OVER
        if event.new_phase != "GAME_OVER":
            return
            
        # Show Game Over dialog immediately
        game_result = self.state.state_data.get("game_result", "unknown")
        game_over_message = self.state.state_data.get("game_over_message", "Game Over")
        self.show_game_over_dialog(game_result, game_over_message)

    def _handle_unit_turn_ended(self, event: GameEvent) -> None:
        """Handle unit turn ended to close action menu."""
        assert isinstance(event, UnitTurnEnded), f"Expected UnitTurnEnded, got {type(event)}"
        
        # Close action menu when unit turn ends
        self.state.ui.close_action_menu()

    def _emit_log(
        self, message: str, category: str = "UI", level: str = "DEBUG"
    ) -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=0,  # TODO: Get actual turn from game state
                message=message,
                category=category,
                level=level,
                source="UIManager",
            ),
            source="UIManager",
        )

    def set_scenario(self, scenario: "Scenario") -> None:
        """Update the scenario reference."""
        self.scenario = scenario

    # Overlay management
    def show_objectives(self) -> None:
        """Show the objectives overlay."""
        self.state.ui.open_overlay("objectives")

    def show_help(self) -> None:
        """Show the help overlay."""
        self.state.ui.open_overlay("help")

    def show_minimap(self) -> None:
        """Show the minimap overlay."""
        self.state.ui.open_overlay("minimap")

    def show_expanded_log(self) -> None:
        """Show the expanded log overlay."""
        self.state.ui.open_expanded_log()

    def close_overlay(self) -> None:
        """Close the currently active overlay."""
        self.state.ui.close_overlay()
        self.state.ui.close_expanded_log()

    def show_game_over_dialog(self, result: str, message: str) -> None:
        """Show the game over dialog with victory/defeat status."""
        # Store game result and message in state for dialog building
        self.state.state_data["game_result"] = result
        self.state.state_data["game_over_message"] = message
        
        # Open the game over dialog
        self.state.ui.open_dialog("game_over")
        
        # Emit UI state change event
        self.event_manager.publish(
            UIStateChanged(
                turn=self.state.battle.current_turn if self.state.battle else 0,
                state_type="dialog_opened",
                new_value="game_over",
            ),
            source="UIManager",
        )

    # Banner management
    def show_banner(self, text: str, duration_ms: int = 2000) -> None:
        """Show an ephemeral banner with the given text."""
        self.active_banner = text
        self.banner_start_time = time.time()
        self.banner_duration_ms = duration_ms

        # Emit UI state change event
        self.event_manager.publish(
            UIStateChanged(
                turn=0,  # TODO: Get actual turn
                state_type="banner_shown",
                new_value=text,
            ),
            source="UIManager",
        )

    def update_banner_timing(self) -> None:
        """Update banner timing and clear expired banners."""
        if self.active_banner:
            elapsed_ms = (time.time() - self.banner_start_time) * 1000
            duration = getattr(self, "banner_duration_ms", 2000)  # Default if not set
            if elapsed_ms >= duration:
                self.active_banner = None

    def show_inspection_at_position(self, position: Vector2) -> None:
        """Build and display inspection panel for a given map position."""
        # Save current overlays before showing inspection panel
        self.state.ui.inspection_mode = True
        self.state.ui.inspection_position = position
        
        # Build comprehensive inspection information
        info_lines = self._build_inspection_content(position)
        
        # Show the inspection overlay with the built content
        overlay_data = {
            "title": "Inspection", 
            "content": "\n".join(info_lines), 
            "type": "inspection",
            "position": position
        }
        self.state.ui.show_overlay("inspection", overlay_data)
    
    def _build_two_column_inspection_layout(self, position: Vector2, overlay_width: int) -> list[str]:
        """Build two-column layout for inspection content."""
        if not position:
            return ["No position data available"]
        
        # Get data
        tile = self.game_map.get_tile(position)
        unit = self.game_map.get_unit_at(position)
        
        # Calculate column widths (roughly 50/50 split)
        left_width = (overlay_width - 6) // 2  # -6 for borders and separator
        right_width = overlay_width - 6 - left_width
        
        # Build left column (terrain info)
        left_content = self._build_terrain_column(tile, position, left_width)
        
        # Build right column (unit info)
        right_content = self._build_unit_column(unit, right_width) if unit else []
        
        # Combine columns side by side
        max_lines = max(len(left_content), len(right_content))
        combined_lines = []
        
        for i in range(max_lines):
            left_line = left_content[i] if i < len(left_content) else ""
            right_line = right_content[i] if i < len(right_content) else ""
            
            # Pad left column to exact width
            left_padded = left_line.ljust(left_width)
            
            # Combine with separator
            combined_line = f"{left_padded} │ {right_line}"
            combined_lines.append(combined_line)
        
        return combined_lines
    
    def _build_terrain_column(self, tile, position: Vector2, width: int) -> list[str]:
        """Build terrain information column."""
        lines = []
        lines.append("═══ TERRAIN INFO ═══".ljust(width))
        lines.append(f"Position: ({position.x}, {position.y})".ljust(width))
        lines.append(f"Terrain: {tile.terrain_type.name}".ljust(width))
        lines.append(f"Move Cost: {tile.move_cost}".ljust(width))
        lines.append(f"Defense Bonus: +{tile.defense_bonus}".ljust(width))
        lines.append(f"Type: {tile.name}".ljust(width))
        lines.append("".ljust(width))  # Spacing
        
        # Add more terrain details if available
        if hasattr(tile, 'elevation'):
            lines.append(f"Elevation: {tile.elevation}".ljust(width))
        
        return lines
    
    def _build_unit_column(self, unit, width: int) -> list[str]:
        """Build unit information column."""
        lines = []
        lines.append("═══ UNIT INFO ═══".ljust(width))
        lines.append(f"Name: {unit.name}".ljust(width))
        lines.append(f"Class: {unit.actor.unit_class.name}".ljust(width))
        lines.append(f"Team: {unit.team.name}".ljust(width))
        lines.append(f"HP: {unit.hp_current}/{unit.health.hp_max}".ljust(width))
        lines.append(f"Str/Mov/Spd: {unit.combat.strength}/{unit.movement.movement_points}/{unit.status.speed}".ljust(width))
        lines.append(f"Status: {'Can Move' if unit.can_move else 'No Move'}, {'Can Act' if unit.can_act else 'No Act'}".ljust(width))
        lines.append("".ljust(width))  # Spacing
        
        # Timeline info (compact)
        timeline_info = self._get_unit_timeline_info(unit)
        if timeline_info:
            lines.append("─── Timeline ───".ljust(width))
            # Only show the most important timeline info
            for info_line in timeline_info[:2]:  # Limit to 2 most important lines
                lines.append(info_line.ljust(width))
            lines.append("".ljust(width))
        
        # Available actions for player units (compact)
        if unit.team.value == 0:  # Player team
            lines.append("─── Actions ───".ljust(width))
            from ...core.engine.actions import get_available_actions
            available_actions = get_available_actions(unit)
            # Show actions in a more compact format
            action_names = [action.name for action in available_actions[:2]]  # First 2 only
            action_names.append("Wait")
            lines.append(", ".join(action_names).ljust(width))
            lines.append("".ljust(width))
        
        # Wounds (if any)
        from ..entities.components import WoundComponent
        wound_comp = unit.entity.get_component("Wound")
        if isinstance(wound_comp, WoundComponent) and wound_comp.active_wounds:
            lines.append(f"─── Wounds ({len(wound_comp.active_wounds)}) ───".ljust(width))
            # Show first wound only
            wound_line = f"1. {str(wound_comp.active_wounds[0])[:width-3]}"
            lines.append(wound_line.ljust(width))
            if len(wound_comp.active_wounds) > 1:
                lines.append(f"... and {len(wound_comp.active_wounds)-1} more".ljust(width))
        
        return lines
    
    def _build_inspection_content(self, position: Vector2) -> list[str]:
        """Build detailed inspection content for a position."""
        info_lines = []
        
        # Tile information
        tile = self.game_map.get_tile(position)
        info_lines.append("=== Tile Information ===")
        info_lines.append(f"Position: ({position.x}, {position.y})")
        info_lines.append(f"Terrain: {tile.terrain_type.name}")
        info_lines.append(f"Move Cost: {tile.move_cost}")
        info_lines.append(f"Defense Bonus: +{tile.defense_bonus}")
        info_lines.append(f"Type: {tile.name}")
        
        # Unit information if present
        unit = self.game_map.get_unit_at(position)
        if unit:
            info_lines.append("")
            info_lines.append("=== Unit Information ===")
            info_lines.append(f"Name: {unit.name}")
            info_lines.append(f"Class: {unit.actor.unit_class.name}")
            info_lines.append(f"Team: {unit.team.name}")
            info_lines.append(f"HP: {unit.hp_current}/{unit.health.hp_max}")
            info_lines.append(f"Strength: {unit.combat.strength}")
            info_lines.append(f"Movement: {unit.movement.movement_points}")
            info_lines.append(f"Speed: {unit.status.speed}")
            info_lines.append(f"Can Move: {unit.can_move}")
            info_lines.append(f"Can Act: {unit.can_act}")
            
            # Timeline position
            timeline_info = self._get_unit_timeline_info(unit)
            if timeline_info:
                info_lines.append("")
                info_lines.append("=== Timeline ===")
                info_lines.extend(timeline_info)
            
            # Available actions for player units
            if unit.team.value == 0:  # Player team
                info_lines.append("")
                info_lines.append("=== Available Actions ===")
                from ...core.engine.actions import get_available_actions
                available_actions = get_available_actions(unit)
                for action in available_actions:
                    info_lines.append(f"  • {action.name} (Weight: {action.weight})")
                info_lines.append("  • Wait (Weight: 50)")
            
            # Wounds
            from ..entities.components import WoundComponent
            wound_comp = unit.entity.get_component("Wound")
            if isinstance(wound_comp, WoundComponent) and wound_comp.active_wounds:
                info_lines.append("")
                info_lines.append(f"=== Wounds ({len(wound_comp.active_wounds)}) ===")
                for i, wound in enumerate(wound_comp.active_wounds, 1):
                    info_lines.append(f"  {i}. {wound}")
        
        return info_lines
    
    def _get_unit_timeline_info(self, unit) -> list[str]:
        """Get timeline information for a unit."""
        if not hasattr(self.state.battle, 'timeline') or not self.state.battle.timeline:
            return []
        
        timeline = self.state.battle.timeline
        info = []
        
        # Find unit in timeline
        for idx, entry in enumerate(timeline.get_preview(20)):
            if entry.entity_type == "unit" and entry.entity_id == unit.unit_id:
                info.append(f"Queue Position: #{idx + 1}")
                ticks = entry.execution_time - timeline.current_time
                if ticks <= 0:
                    info.append("Status: Acting Now!")
                else:
                    info.append(f"Next Turn In: {ticks} ticks")
                info.append(f"Next Action: {entry.action_description or 'Unknown'}")
                return info
        
        return ["Queue Position: Not scheduled"]

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
            content.append(f"Current Turn: {self.state.battle.current_turn}")

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

    def build_inspection_overlay(self) -> OverlayRenderData:
        """Build fullscreen inspection overlay with two-column layout."""
        if not self.state.ui.overlay_data:
            return OverlayRenderData(
                overlay_type="inspection",
                width=60,
                height=15,
                title="Inspection",
                content=["No inspection data available"],
            )
        
        data = self.state.ui.overlay_data
        position = data["position"]  # This must exist and be Vector2 if we got here
        
        # Get screen dimensions for fullscreen overlay
        screen_width, screen_height = self.renderer.get_screen_size()
        overlay_width = min(screen_width - 4, 120)  # Leave some margin
        overlay_height = min(screen_height - 4, 30)  # Leave some margin
        
        # Build two-column layout
        content_lines = self._build_two_column_inspection_layout(position, overlay_width)
        
        # Add controls at bottom
        content_lines.append("")
        content_lines.append("" + "═" * (overlay_width - 4))  # Separator line
        content_lines.append("Controls: [Enter] Close [X] Cancel")
        
        return OverlayRenderData(
            overlay_type="inspection",
            width=overlay_width,
            height=overlay_height,
            title="Detailed Inspection",
            content=content_lines,
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
        for unit in self.game_map.units:
            if unit is not None and unit.is_alive:
                unit_map[(unit.position.x, unit.position.y)] = unit.team.value

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
                camera_left = self.state.cursor.camera_position.x
                camera_right = (
                    self.state.cursor.camera_position.x + screen_width - 28
                )  # Account for sidebar
                camera_top = self.state.cursor.camera_position.y
                camera_bottom = (
                    self.state.cursor.camera_position.y + screen_height - 3
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

    def build_expanded_log_overlay(self) -> OverlayRenderData:
        """Build expanded log overlay content from game state."""
        # Get log data from game state (populated by log manager through events)
        log_data = self.state.state_data.get("log_data")
        if not log_data:
            return OverlayRenderData(
                overlay_type="expanded_log",
                width=60,
                height=15,
                title="Message Log",
                content=["No log data available"],
            )

        # Get screen dimensions for full-screen overlay
        screen_width, screen_height = self.renderer.get_screen_size()

        # Use most of the screen for the log
        overlay_width = min(screen_width - 4, 120)  # Leave some margin
        overlay_height = min(screen_height - 4, 30)  # Leave some margin

        # Get all messages from game state
        messages = log_data.get("messages", [])
        debug_enabled = log_data.get("debug_enabled", False)

        # Calculate scrolling with available space
        max_lines = (
            overlay_height - 8
        )  # Account for title, borders, controls (more conservative)
        total_messages = len(messages)

        content = []
        if not messages:
            content.append("No messages yet...")
            # Initialize variables for empty case
            scroll_offset = 0
            start_idx = 0
            end_idx = 0
        else:
            # Get current scroll position
            scroll_offset = self.state.ui.expanded_log_scroll

            # Calculate which messages to show based on scroll
            if scroll_offset == 0:
                # At bottom - show most recent messages
                start_idx = max(0, total_messages - max_lines)
                end_idx = total_messages
                recent_messages = messages[start_idx:end_idx]
            else:
                # Scrolled up - show older messages
                end_idx = total_messages - scroll_offset
                start_idx = max(0, end_idx - max_lines)
                # Ensure we don't scroll past the top
                if start_idx == 0:
                    scroll_offset = total_messages - max_lines
                    if scroll_offset < 0:
                        scroll_offset = 0
                    self.state.ui.expanded_log_scroll = scroll_offset
                    end_idx = total_messages - scroll_offset
                recent_messages = messages[start_idx:end_idx]

            for msg in recent_messages:
                # Format message - assume messages are already formatted strings
                formatted = str(msg)

                # Wrap long messages with proper indentation
                max_line_width = overlay_width - 4  # Account for borders
                if len(formatted) <= max_line_width:
                    content.append(formatted)
                else:
                    # Find the end of the category tag (e.g., "[BTL] ")
                    category_end = 0
                    if formatted.startswith("[") and "] " in formatted:
                        category_end = formatted.index("] ") + 2

                    # Extract category prefix and message text
                    category_prefix = formatted[:category_end]
                    message_text = formatted[category_end:]

                    # Calculate indentation for wrapped lines
                    indent = " " * category_end

                    # First line: category + as much message text as fits
                    first_line_space = max_line_width - len(category_prefix)
                    if first_line_space > 0:
                        first_line = category_prefix + message_text[:first_line_space]
                        content.append(first_line)
                        remaining_text = message_text[first_line_space:]
                    else:
                        # Category is too long, just truncate
                        content.append(formatted[:max_line_width])
                        continue

                    # Wrapped lines: indent + remaining text
                    wrap_width = max_line_width - len(indent)
                    while remaining_text and wrap_width > 0:
                        line_text = remaining_text[:wrap_width]
                        content.append(indent + line_text)
                        remaining_text = remaining_text[wrap_width:]

        content.append("")

        # Add scroll indicator if there are more messages
        if total_messages > max_lines:
            if scroll_offset == 0:
                content.append("[Showing latest messages - UP to scroll to older]")
            else:
                showing_range = f"[Showing {start_idx + 1}-{end_idx} of {total_messages} - UP/DOWN to scroll]"
                content.append(showing_range)

        content.append("")
        content.append("Controls:")

        # Show debug toggle status from game state
        debug_status = "ON" if debug_enabled else "OFF"
        content.append(f"  D - Toggle debug messages (currently {debug_status})")
        content.append("  S - Save log to file")
        if total_messages > max_lines:
            content.append("  UP/DOWN - Scroll through messages")
        content.append("  Q - Close the log")

        return OverlayRenderData(
            overlay_type="expanded_log",
            width=overlay_width,
            height=overlay_height,
            title="Message Log (Full)",
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
        position = Vector2(y, x)
        if self.game_map.is_valid_position(position):
            tile = self.game_map.get_tile(position)
            if tile.terrain_type in ["mountain", "wall"]:
                return "▲"  # Mountain/wall
            elif tile.terrain_type == "water":
                return "≈"  # Water
            elif tile.terrain_type == "forest":
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
                selected_option=self.state.ui.get_dialog_selection(),
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
                selected_option=self.state.ui.get_dialog_selection(),
            )
        elif dialog_type == "confirm_save_log":
            return DialogRenderData(
                x=20,
                y=3,  # Position higher on screen to show over expanded log
                width=32,
                height=6,
                title="Save Log",
                message="Save message log to file?",
                options=["Yes", "No"],
                selected_option=self.state.ui.get_dialog_selection(),
            )
        elif dialog_type == "confirm_wait":
            return DialogRenderData(
                x=20,
                y=10,
                width=45,
                height=6,
                title="Confirm Wait",
                message="Unit can still act. Wait and end turn?",
                options=["Yes", "No"],
                selected_option=self.state.ui.get_dialog_selection(),
            )
        elif dialog_type == "game_over":
            # Get game result from state
            game_result = self.state.state_data.get("game_result", "unknown")
            game_over_message = self.state.state_data.get("game_over_message", "Game Over")
            
            # Determine title and message based on result
            if game_result == "victory":
                title = "Victory!"
                message = game_over_message
            elif game_result == "defeat":
                title = "Defeat"
                message = game_over_message
            else:
                title = "Game Over"
                message = game_over_message
            
            # Calculate appropriate width based on message length
            min_width = max(len(message) + 6, len(title) + 6, 30)
            dialog_width = min(min_width, 60)  # Cap at 60 chars
            
            return DialogRenderData(
                x=20,
                y=10,  # Will be centered by renderer
                width=dialog_width,
                height=8,
                title=title,
                message=message,
                options=["View Log", "Quit Game"],
                selected_option=self.state.ui.get_dialog_selection(),
            )
        elif dialog_type == "confirm_quit":
            message = "Are you sure you want to quit?"
            # Calculate appropriate width
            dialog_width = max(len(message) + 6, 36)
            
            return DialogRenderData(
                x=20,
                y=10,  # Will be centered by renderer
                width=dialog_width,
                height=6,
                title="Quit Game",
                message=message,
                options=["Yes", "No"],
                selected_option=self.state.ui.get_dialog_selection(),
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
            selected_option=self.state.ui.get_dialog_selection(),
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

    # ============== New 4-Panel UI Coordination Methods ==============

    def get_panel_visibility_state(self) -> dict[str, bool]:
        """Get visibility state for all UI panels."""
        return {
            "timeline": hasattr(self.state.battle, "timeline")
            and self.state.battle.timeline is not None,
            "unit_info": True,  # Always visible when unit is selected/cursor is on unit
            "action_menu": self.state.ui.is_action_menu_open(),
            "battlefield": True,  # Always visible in battle
        }

    def should_show_unit_info_panel(self) -> bool:
        """Determine if the unit info panel should be displayed."""
        # Show if there's a selected unit or cursor is on a unit
        if (
            hasattr(self.state.battle, "selected_unit_id")
            and self.state.battle.selected_unit_id
        ):
            return True

        # Check if cursor is on a unit
        for unit in self.game_map.units:
            if unit and unit.is_alive and unit.position == self.state.cursor.position:
                return True

        return False

    def get_active_panel_count(self) -> int:
        """Get the number of currently active UI panels."""
        visibility = self.get_panel_visibility_state()
        return sum(1 for visible in visibility.values() if visible)

    def coordinate_panel_layouts(
        self, screen_width: int, screen_height: int
    ) -> dict[str, dict[str, int]]:
        """Calculate coordinated panel layouts for optimal space usage."""
        # This follows the ui.md specification for panel dimensions
        timeline_height = max(2, int(screen_height * 0.12))  # 10-15% -> use 12%
        bottom_panel_height = max(4, int(screen_height * 0.20))  # 20% height
        battlefield_height = screen_height - timeline_height - bottom_panel_height

        # Bottom panel widths
        unit_info_width = max(20, int(screen_width * 0.20))  # 20% width
        action_menu_width = max(25, int(screen_width * 0.25))  # 25% width

        return {
            "timeline": {
                "x": 0,
                "y": 0,
                "width": screen_width,
                "height": timeline_height,
            },
            "battlefield": {
                "x": 0,
                "y": timeline_height,
                "width": screen_width,
                "height": battlefield_height,
            },
            "unit_info": {
                "x": 0,
                "y": screen_height - bottom_panel_height,
                "width": unit_info_width,
                "height": bottom_panel_height,
            },
            "action_menu": {
                "x": screen_width - action_menu_width,
                "y": screen_height - bottom_panel_height,
                "width": action_menu_width,
                "height": bottom_panel_height,
            },
        }

    def handle_panel_interactions(self, input_event) -> bool:
        """Handle input events that affect panel coordination."""
        # This could be expanded to handle panel-specific interactions
        # For now, it's a placeholder for future panel interaction logic
        return False

    def get_panel_focus_state(self) -> str:
        """Determine which panel currently has focus."""
        # Priority: action_menu > unit_info > battlefield > timeline
        if self.state.ui.is_action_menu_open():
            return "action_menu"
        elif self.should_show_unit_info_panel():
            return "unit_info"
        else:
            return "battlefield"
