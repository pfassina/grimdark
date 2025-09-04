"""
Input handling system for processing user interactions.

This module manages all user input events and translates them into
appropriate game actions, maintaining separation from game logic execution.
"""
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from .map import GameMap
    from .unit import Unit
    from ..core.game_state import GameState
    from ..core.renderer import Renderer

from ..core.game_enums import Team
from ..core.game_state import BattlePhase
from ..core.input import InputEvent, InputType, Key
from ..core.data_structures import Vector2


class InputHandler:
    """Handles all user input events and translates them to game actions."""
    
    def __init__(
        self,
        game_map: "GameMap",
        game_state: "GameState", 
        renderer: "Renderer",
        combat_manager=None,
        ui_manager=None,
        scenario_menu=None
    ):
        self.game_map = game_map
        self.state = game_state
        self.renderer = renderer
        self.combat_manager = combat_manager
        self.ui_manager = ui_manager
        self.scenario_menu = scenario_menu
        
        # Callbacks that will be set by the main Game class
        self.on_quit: Optional[Callable] = None
        self.on_end_unit_turn: Optional[Callable] = None
        self.on_load_selected_scenario: Optional[Callable] = None
        self.on_movement_preview_update: Optional[Callable] = None
        
    def handle_input_events(self, events: list[InputEvent]) -> None:
        """Process a list of input events."""
        for event in events:
            if event.event_type == InputType.QUIT:
                if self.on_quit:
                    self.on_quit()
            elif event.event_type == InputType.KEY_PRESS:
                self.handle_key_press(event)
    
    def handle_key_press(self, event: InputEvent) -> None:
        """Route key press events to appropriate handlers based on current state."""
        # Handle modal overlays (objectives, help, minimap)
        if self.state.is_overlay_open():
            self.handle_overlay_input(event)
        # Handle confirmation dialogs
        elif self.state.is_dialog_open():
            self.handle_dialog_input(event)
        # Handle battle forecast during targeting
        elif self.state.is_forecast_active():
            self.handle_forecast_input(event)
        # Handle existing modals
        elif self.state.is_action_menu_open():
            self.handle_action_menu_input(event)
        elif self.state.is_menu_open():
            self.handle_menu_input(event)
        else:
            self.handle_map_input(event)
    
    def handle_map_input(self, event: InputEvent) -> None:
        """Handle input when navigating the main game map."""
        if event.key == Key.Q:
            if self.on_quit:
                self.on_quit()
            return
        
        # During non-player turns, only allow limited actions
        if self.state.current_team != 0:  # 0 = Player team
            # Only allow overlay keys during enemy/AI turns
            if event.key == Key.O:
                self.handle_objectives_key()
            elif event.key == Key.HELP:
                self.handle_help_key()
            elif event.key == Key.M:
                self.handle_minimap_key()
            # Ignore all other input during enemy turns
            return
        
        # Handle TAB key for cycling
        if event.key == Key.TAB:
            self.handle_tab_cycling()
            return
        
        if event.is_movement_key():
            self.handle_movement_input(event)
        elif event.is_confirm_key():
            self.handle_confirm()
        elif event.is_cancel_key():
            self.handle_cancel()
        # Strategic action keys
        elif event.key == Key.O:
            self.handle_objectives_key()
        elif event.key == Key.HELP:
            self.handle_help_key()
        elif event.key == Key.M:
            self.handle_minimap_key()
        elif event.key == Key.E:
            self.handle_end_turn_key()
        elif event.key == Key.A:
            self.handle_attack_key()
        elif event.key == Key.W:
            self.handle_wait_key()
    
    def handle_movement_input(self, event: InputEvent) -> None:
        """Handle directional movement input."""
        dx, dy = 0, 0
        if event.key == Key.UP:
            dy = -1
        elif event.key in {Key.DOWN, Key.S}:
            dy = 1
        elif event.key == Key.LEFT:
            dx = -1
        elif event.key in {Key.RIGHT, Key.D}:
            dx = 1
        
        self.state.move_cursor(dx, dy, self.game_map.width, self.game_map.height)
        
        # Update selected target and AOE tiles if in attack targeting mode
        if (
            self.state.battle_phase == BattlePhase.UNIT_ACTING
            and self.state.attack_range
            and self.combat_manager
        ):
            self.combat_manager.update_attack_targeting()
        elif self.state.selected_unit_id and self.on_movement_preview_update:
            self.on_movement_preview_update()
    
    def handle_confirm(self) -> None:
        """Handle confirmation input based on current battle phase."""
        cursor_position = self.state.cursor_position
        
        if self.state.battle_phase == BattlePhase.UNIT_SELECTION:
            self._handle_unit_selection_confirm(cursor_position)
        elif self.state.battle_phase == BattlePhase.UNIT_MOVING:
            self._handle_unit_movement_confirm(cursor_position)
        elif self.state.battle_phase == BattlePhase.ACTION_MENU:
            self._handle_action_menu_confirm()
        elif self.state.battle_phase == BattlePhase.UNIT_ACTING:
            self._handle_unit_acting_confirm()
    
    def _handle_unit_selection_confirm(self, cursor_position: Vector2) -> None:
        """Handle confirmation during unit selection phase."""
        unit = self.game_map.get_unit_at(cursor_position)
        if unit and unit.team == Team.PLAYER and unit.can_move and unit.can_act:
            self.state.selected_unit_id = unit.unit_id
            # Store original position for potential cancellation
            self.state.original_unit_position = unit.position
            self.state.battle_phase = BattlePhase.UNIT_MOVING
            movement_range = self.game_map.calculate_movement_range(unit)
            self.state.set_movement_range(list(movement_range))
    
    def _handle_unit_movement_confirm(self, cursor_position: Vector2) -> None:
        """Handle confirmation during unit movement phase."""
        if self.state.is_in_movement_range(cursor_position):
            if self.state.selected_unit_id:
                unit = self.game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    if self.game_map.move_unit(unit.unit_id, cursor_position):
                        # TODO: Emit unit moved event - will be handled by main Game class
                        pass
                    unit.has_moved = True
                    
                    # Clear movement range and transition to action menu
                    self.state.movement_range.clear()
                    self.state.battle_phase = BattlePhase.ACTION_MENU
                    self._build_action_menu_for_unit(unit)
    
    def _handle_action_menu_confirm(self) -> None:
        """Handle confirmation in action menu phase."""
        selected_action = self.state.get_selected_action()
        if selected_action:
            self._handle_action_selection(selected_action)
    
    def _handle_unit_acting_confirm(self) -> None:
        """Handle confirmation during unit acting phase (attack execution)."""
        if self.combat_manager:
            success = self.combat_manager.execute_attack_at_cursor()
            if success and self.on_end_unit_turn:
                self.on_end_unit_turn()
    
    def handle_cancel(self) -> None:
        """Handle cancel input based on current battle phase."""
        if self.state.battle_phase == BattlePhase.UNIT_MOVING:
            self._handle_movement_cancel()
        elif self.state.battle_phase == BattlePhase.ACTION_MENU:
            self._handle_action_menu_cancel()
        elif self.state.battle_phase == BattlePhase.TARGETING:
            self._handle_targeting_cancel()
        elif self.state.battle_phase == BattlePhase.UNIT_ACTING:
            self._handle_unit_acting_cancel()
    
    def _handle_movement_cancel(self) -> None:
        """Handle cancel during movement phase."""
        self.state.reset_selection()
        self.state.battle_phase = BattlePhase.UNIT_SELECTION
    
    def _handle_action_menu_cancel(self) -> None:
        """Handle cancel during action menu phase."""
        if self.state.selected_unit_id:
            unit = self.game_map.get_unit(self.state.selected_unit_id)
            if unit and not unit.has_moved:
                self.state.close_action_menu()
                self.state.battle_phase = BattlePhase.UNIT_MOVING
                movement_range = self.game_map.calculate_movement_range(unit)
                self.state.set_movement_range(list(movement_range))
            else:
                # Unit has already moved - restore to original position
                self._restore_unit_to_original_position(unit)
    
    def _handle_targeting_cancel(self) -> None:
        """Handle cancel during targeting phase."""
        self.state.attack_range.clear()
        self.state.selected_target = None
        self.state.aoe_tiles.clear()
        self.state.battle_phase = BattlePhase.ACTION_MENU
        if self.state.selected_unit_id:
            unit = self.game_map.get_unit(self.state.selected_unit_id)
            if unit:
                self._build_action_menu_for_unit(unit)
    
    def _handle_unit_acting_cancel(self) -> None:
        """Handle cancel during unit acting phase."""
        if self.combat_manager:
            self.combat_manager.clear_attack_state()
        self.state.battle_phase = BattlePhase.ACTION_MENU
        if self.state.selected_unit_id:
            unit = self.game_map.get_unit(self.state.selected_unit_id)
            if unit:
                self._build_action_menu_for_unit(unit)
    
    def _restore_unit_to_original_position(self, unit: Optional["Unit"]) -> None:
        """Restore unit to its original position if possible."""
        if unit and self.state.original_unit_position is not None:
            # Restore unit to original position
            if self.game_map.move_unit(unit.unit_id, self.state.original_unit_position):
                # TODO: Emit unit moved event for restoration
                pass
            unit.has_moved = False
            
            # Go back to movement phase to allow re-positioning
            self.state.close_action_menu()
            self.state.battle_phase = BattlePhase.UNIT_MOVING
            movement_range = self.game_map.calculate_movement_range(unit)
            self.state.set_movement_range(list(movement_range))
            
            # Position cursor on the restored unit
            self.state.cursor_position = unit.position
        else:
            # Fallback: deselect and refresh
            self.state.reset_selection()
            self.state.battle_phase = BattlePhase.UNIT_SELECTION
    
    def handle_tab_cycling(self) -> None:
        """Handle TAB key cycling for different phases."""
        if self.state.battle_phase == BattlePhase.UNIT_SELECTION:
            self._cycle_selectable_units()
        elif self.state.battle_phase == BattlePhase.UNIT_ACTING and self.combat_manager:
            self.combat_manager.cycle_targetable_enemies()
    
    def _cycle_selectable_units(self) -> None:
        """Cycle through selectable player units."""
        # Get all selectable units if not already set
        if not self.state.selectable_units:
            self._refresh_selectable_units()
        
        # Cycle to next unit
        next_unit_id = self.state.cycle_selectable_units()
        if next_unit_id:
            unit = self.game_map.get_unit(next_unit_id)
            if unit:
                self.state.cursor_position = unit.position
    
    def _refresh_selectable_units(self) -> None:
        """Update the list of selectable player units."""
        player_units = self.game_map.get_units_by_team(Team.PLAYER)
        selectable_ids = [
            unit.unit_id for unit in player_units if unit.can_move or unit.can_act
        ]
        self.state.set_selectable_units(selectable_ids)
    
    def handle_action_menu_input(self, event: InputEvent) -> None:
        """Handle input while action menu is open."""
        if event.key == Key.UP or event.key == Key.W:
            self.state.move_action_menu_selection(-1)
        elif event.key == Key.DOWN or event.key == Key.S:
            self.state.move_action_menu_selection(1)
        elif event.is_confirm_key():
            self.handle_confirm()
        elif event.is_cancel_key():
            self.handle_cancel()
        # Add keyboard shortcuts
        elif event.key == Key.A and "Attack" in self.state.action_menu_items:
            self.state.action_menu_selection = self.state.action_menu_items.index("Attack")
            self.handle_confirm()
        elif event.key == Key.W and "Wait" in self.state.action_menu_items:
            self.state.action_menu_selection = self.state.action_menu_items.index("Wait")
            self.handle_confirm()
        elif event.key == Key.M and "Move" in self.state.action_menu_items:
            self.state.action_menu_selection = self.state.action_menu_items.index("Move")
            self.handle_confirm()
    
    def handle_main_menu_input(self, event: InputEvent) -> None:
        """Handle input while in main menu phase."""
        if self.scenario_menu:
            action = self.scenario_menu.handle_input(event)
            
            if action == "load" and self.on_load_selected_scenario:
                self.on_load_selected_scenario()
            elif action == "quit" and self.on_quit:
                self.on_quit()
    
    def handle_menu_input(self, event: InputEvent) -> None:
        """Handle input events when a menu is open (placeholder for future implementation)."""
        _ = event  # Placeholder implementation
    
    # Strategic TUI input handlers
    def handle_overlay_input(self, event: InputEvent) -> None:
        """Handle input while overlay (objectives/help/minimap) is open."""
        if event.event_type == InputType.KEY_PRESS and self.ui_manager:
            self.ui_manager.close_overlay()
    
    def handle_dialog_input(self, event: InputEvent) -> None:
        """Handle input while confirmation dialog is open."""
        if event.key in {Key.LEFT, Key.RIGHT}:
            self.state.move_dialog_selection(1 if event.key == Key.RIGHT else -1)
        elif event.is_confirm_key():
            self._handle_dialog_confirmation()
        elif event.is_cancel_key():
            self.state.close_dialog()
    
    def _handle_dialog_confirmation(self) -> None:
        """Handle dialog confirmation based on dialog type."""
        if self.state.active_dialog == "confirm_end_turn":
            if self.state.get_dialog_selection() == 0:  # Yes
                if self.on_end_unit_turn:
                    self.on_end_unit_turn()
        elif self.state.active_dialog == "confirm_friendly_fire":
            if (
                self.state.get_dialog_selection() == 0  # Yes - proceed with attack
                and self.combat_manager
            ):
                success = self.combat_manager.execute_confirmed_attack()
                if success and self.on_end_unit_turn:
                    self.on_end_unit_turn()
        self.state.close_dialog()
    
    def handle_forecast_input(self, event: InputEvent) -> None:
        """Handle input while battle forecast is active."""
        if event.event_type == InputType.KEY_PRESS:
            self.state.stop_forecast()
    
    # Direct action key handlers
    def handle_objectives_key(self) -> None:
        """Handle O key press to show objectives."""
        if self.ui_manager:
            self.ui_manager.show_objectives()
    
    def handle_help_key(self) -> None:
        """Handle ? key press to show help."""
        if self.ui_manager:
            self.ui_manager.show_help()
    
    def handle_minimap_key(self) -> None:
        """Handle M key press to show minimap."""
        if self.ui_manager:
            self.ui_manager.show_minimap()
    
    def handle_end_turn_key(self) -> None:
        """Handle E key press to end turn (with confirmation)."""
        self.state.open_dialog("confirm_end_turn")
    
    def handle_attack_key(self) -> None:
        """Handle A key press for direct attack."""
        # Only allow during player turn and when a unit is selected
        if self.state.current_team != 0 or not self.state.selected_unit_id:
            return
        
        unit = self.game_map.get_unit(self.state.selected_unit_id)
        if not unit or not unit.can_act or not self.combat_manager:
            return
        
        # Handle quick attack based on current phase
        if self.state.battle_phase == BattlePhase.UNIT_SELECTION:
            # Unit just selected, transition to attack directly
            self.state.battle_phase = BattlePhase.UNIT_ACTING
            self.combat_manager.setup_attack_targeting(unit)
        elif self.state.battle_phase == BattlePhase.UNIT_MOVING:
            # Unit is in movement, skip to attack
            self.state.movement_range.clear()
            self.state.battle_phase = BattlePhase.UNIT_ACTING
            self.combat_manager.setup_attack_targeting(unit)
        elif self.state.battle_phase == BattlePhase.ACTION_MENU:
            # Use normal action selection
            self._handle_action_selection("Attack")
    
    def handle_wait_key(self) -> None:
        """Handle W key press for direct wait."""
        # Only allow during player turn and when a unit is selected
        if self.state.current_team != 0 or not self.state.selected_unit_id:
            return
        
        unit = self.game_map.get_unit(self.state.selected_unit_id)
        if not unit:
            return
        
        # When waiting, unit should not be able to move or act anymore
        unit.has_moved = True  # Prevent further movement
        unit.has_acted = True  # Prevent further actions
        if self.on_end_unit_turn:
            self.on_end_unit_turn()
    
    # Action handling
    def _handle_action_selection(self, action: str) -> None:
        """Handle the selected action from the action menu."""
        if action == "Move":
            # Go back to movement targeting
            if self.state.selected_unit_id:
                unit = self.game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    self.state.close_action_menu()
                    self.state.battle_phase = BattlePhase.UNIT_MOVING
                    movement_range = self.game_map.calculate_movement_range(unit)
                    self.state.set_movement_range(list(movement_range))
        
        elif action == "Attack":
            # Go to attack targeting
            if self.state.selected_unit_id and self.combat_manager:
                unit = self.game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    self.state.close_action_menu()
                    self.state.battle_phase = BattlePhase.UNIT_ACTING
                    self.combat_manager.setup_attack_targeting(unit)
        
        elif action == "Wait":
            # End unit's turn
            if self.state.selected_unit_id:
                unit = self.game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    # When waiting, unit should not be able to move or act anymore
                    unit.has_moved = True  # Prevent further movement
                    unit.has_acted = True  # Prevent further actions
                    self.state.close_action_menu()
                    if self.on_end_unit_turn:
                        self.on_end_unit_turn()
    
    def _build_action_menu_for_unit(self, unit: "Unit") -> None:
        """Build action menu items based on unit's current capabilities."""
        actions = []
        
        # Move action - available if unit hasn't moved yet
        if not unit.has_moved and unit.can_move:
            actions.append("Move")
        
        # Attack action - always show (availability checked in selection)
        if unit.can_act:
            actions.append("Attack")
        
        # Wait action - always available
        actions.append("Wait")
        
        self.state.open_action_menu(actions)
        
        # Auto-select the most appropriate action
        self._auto_select_action_menu_item(unit)
    
    def _auto_select_action_menu_item(self, unit: "Unit") -> None:
        """Automatically select the most appropriate action in the menu."""
        if not unit.can_act:
            # Unit can't act, select Wait
            if "Wait" in self.state.action_menu_items:
                self.state.action_menu_selection = self.state.action_menu_items.index("Wait")
            return
        
        # Check if there are ENEMY targets in attack range (not friendlies)
        attack_range = self.game_map.calculate_attack_range(unit)
        has_enemy_targets = False
        
        for position in attack_range:
            target_unit = self.game_map.get_unit_at(position)
            if (
                target_unit
                and target_unit.unit_id != unit.unit_id
                and target_unit.team != unit.team
            ):
                has_enemy_targets = True
                break
        
        # Select Attack only if there are enemy targets, otherwise Wait
        if has_enemy_targets and "Attack" in self.state.action_menu_items:
            self.state.action_menu_selection = self.state.action_menu_items.index("Attack")
        elif "Wait" in self.state.action_menu_items:
            self.state.action_menu_selection = self.state.action_menu_items.index("Wait")