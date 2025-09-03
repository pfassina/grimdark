import time
from typing import Optional

from ..core.renderer import Renderer
from ..core.renderable import (
    RenderContext, TileRenderData, UnitRenderData,
    CursorRenderData, OverlayTileRenderData, TextRenderData
)
from ..core.input import InputEvent, InputType, Key
from ..core.game_state import GameState, BattlePhase, GamePhase
from ..core.data_structures import DataConverter
from ..core.game_enums import Team

from .map import GameMap
from .unit import Unit
from .scenario import Scenario
from .scenario_loader import ScenarioLoader
from .scenario_menu import ScenarioMenu


class Game:
    
    def __init__(self, game_map: Optional[GameMap], renderer: Renderer, scenario: Optional[Scenario] = None):
        self.renderer = renderer
        self.state = GameState(phase=GamePhase.MAIN_MENU)
        self.game_map = game_map
        self.scenario = scenario
        self.scenario_menu = ScenarioMenu()
        self.running = False
        self.fps = 30
        self.frame_time = 1.0 / self.fps
        
        # Banner timing system
        self.game_start_time = time.time()
        self.active_banner = None
        self.banner_start_time = 0
        
        # Cursor blinking system (2Hz = blink every 0.5 seconds)
        self.cursor_blink_interval = 0.5
        
        # Enemy turn processing
        self.enemy_turn_start_time = 0
        self.enemy_turn_duration = 2.0  # 2 seconds per enemy turn
    
    def _ensure_game_map(self) -> GameMap:
        """Ensure game_map is initialized, raise error if not."""
        if self.game_map is None:
            raise RuntimeError("Game map not initialized. Call initialize() first.")
        return self.game_map
        
    def initialize(self) -> None:
        self.renderer.start()
        if self.state.phase != GamePhase.MAIN_MENU and self.game_map is None:
            self._load_default_scenario()
        self.running = True
    
    def _load_default_scenario(self) -> None:
        """Load the default test scenario if no map/scenario provided."""
        import os
        try:
            scenario_path = "assets/scenarios/default_test.yaml"
            self.scenario = ScenarioLoader.load_from_file(scenario_path)
            self.game_map = ScenarioLoader.create_game_map(self.scenario)
            ScenarioLoader.place_units(self.scenario, self.game_map)
            
            # Position cursor on first player unit
            self._position_cursor_on_first_player_unit()
            
            # Initialize selectable units if in battle phase
            if self.state.phase == GamePhase.BATTLE:
                self._refresh_selectable_units()
                # Show initial phase banner
                self.show_banner("PLAYER PHASE")
                
        except FileNotFoundError:
            raise RuntimeError(f"Default scenario not found at {scenario_path}. Please provide a map or scenario.")
        except Exception as e:
            raise RuntimeError(f"Failed to load default scenario: {e}")
    
    def run(self) -> None:
        self.initialize()
        
        last_frame = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                delta_time = current_time - last_frame
                
                if delta_time >= self.frame_time:
                    self.update(delta_time)
                    self.render()
                    last_frame = current_time
                else:
                    time.sleep(0.001)
        finally:
            self.cleanup()
    
    def update(self, delta_time: float) -> None:
        # Update banner timing
        self.update_banner_timing()
        
        # Handle enemy turn processing
        self.update_enemy_turn()
        
        # Check if game is over
        if self.state.phase == GamePhase.GAME_OVER:
            events = self.renderer.get_input_events()
            for event in events:
                if event.event_type == InputType.QUIT or event.event_type == InputType.KEY_PRESS:
                    self.running = False
            return
        
        # Handle main menu phase
        if self.state.phase == GamePhase.MAIN_MENU:
            events = self.renderer.get_input_events()
            for event in events:
                if event.event_type == InputType.QUIT:
                    self.running = False
                elif event.event_type == InputType.KEY_PRESS:
                    self.handle_main_menu_input(event)
            return
        
        events = self.renderer.get_input_events()
        
        for event in events:
            if event.event_type == InputType.QUIT:
                self.running = False
            elif event.event_type == InputType.KEY_PRESS:
                self.handle_key_press(event)
    
    def handle_key_press(self, event: InputEvent) -> None:
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
        if event.key == Key.Q:
            self.running = False
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
            dx, dy = 0, 0
            if event.key == Key.UP:
                dy = -1
            elif event.key in {Key.DOWN, Key.S}:
                dy = 1
            elif event.key == Key.LEFT:
                dx = -1
            elif event.key in {Key.RIGHT, Key.D}:
                dx = 1
            
            game_map = self._ensure_game_map()
            self.state.move_cursor(dx, dy, game_map.width, game_map.height)
            
            # Update selected target and AOE tiles if in attack targeting mode
            if self.state.battle_phase == BattlePhase.UNIT_ACTING and self.state.attack_range:
                self._update_attack_targeting()
            elif self.state.selected_unit_id:
                self.update_movement_preview()
        
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
    
    def handle_main_menu_input(self, event: InputEvent) -> None:
        """Handle input while in main menu phase."""
        action = self.scenario_menu.handle_input(event)
        
        if action == 'load':
            self.load_selected_scenario()
        elif action == 'quit':
            self.running = False
    
    def load_selected_scenario(self) -> None:
        """Load the scenario selected from the menu."""
        scenario = self.scenario_menu.load_selected_scenario()
        if scenario:
            try:
                self.scenario = scenario
                self.game_map = ScenarioLoader.create_game_map(scenario)
                ScenarioLoader.place_units(scenario, self.game_map)
                
                # Position cursor on first player unit
                self._position_cursor_on_first_player_unit()
                
                # Transition to battle phase
                self.state.phase = GamePhase.BATTLE
                self.state.battle_phase = BattlePhase.UNIT_SELECTION
                
                # Initialize selectable units
                self._refresh_selectable_units()
                
            except Exception as e:
                print(f"Failed to load scenario: {e}")
                # Stay in main menu on error
    
    def handle_menu_input(self, event: InputEvent) -> None:
        pass
    
    def handle_confirm(self) -> None:
        cursor_x = self.state.cursor_x
        cursor_y = self.state.cursor_y
        
        if self.state.battle_phase == BattlePhase.UNIT_SELECTION:
            game_map = self._ensure_game_map()
            unit = game_map.get_unit_at(cursor_x, cursor_y)
            if unit and unit.team == Team.PLAYER and unit.can_move and unit.can_act:
                self.state.selected_unit_id = unit.unit_id
                # Store original position for potential cancellation
                self.state.original_unit_x = unit.x
                self.state.original_unit_y = unit.y
                self.state.battle_phase = BattlePhase.UNIT_MOVING
                movement_range = game_map.calculate_movement_range(unit)
                self.state.set_movement_range(list(movement_range))
        
        elif self.state.battle_phase == BattlePhase.UNIT_MOVING:
            if self.state.is_in_movement_range(cursor_x, cursor_y):
                if self.state.selected_unit_id:
                    game_map = self._ensure_game_map()
                    unit = game_map.get_unit(self.state.selected_unit_id)
                    if unit:
                        game_map.move_unit(unit.unit_id, cursor_x, cursor_y)
                        unit.has_moved = True
                        
                        # Clear movement range and transition to action menu
                        self.state.movement_range.clear()
                        self.state.battle_phase = BattlePhase.ACTION_MENU
                        self._build_action_menu_for_unit(unit)
        
        elif self.state.battle_phase == BattlePhase.ACTION_MENU:
            # Handle action menu selection
            selected_action = self.state.get_selected_action()
            if selected_action:
                self._handle_action_selection(selected_action)
        
        elif self.state.battle_phase == BattlePhase.UNIT_ACTING:
            # Handle attack execution
            self._execute_attack()
    
    def handle_tab_cycling(self) -> None:
        """Handle TAB key cycling for different phases."""
        if self.state.battle_phase == BattlePhase.UNIT_SELECTION:
            self._cycle_selectable_units()
        elif self.state.battle_phase == BattlePhase.UNIT_ACTING:
            self._cycle_targetable_enemies()
    
    def _cycle_selectable_units(self) -> None:
        """Cycle through selectable player units."""
        game_map = self._ensure_game_map()
        
        # Get all selectable units if not already set
        if not self.state.selectable_units:
            self._refresh_selectable_units()
        
        # Cycle to next unit
        next_unit_id = self.state.cycle_selectable_units()
        if next_unit_id:
            unit = game_map.get_unit(next_unit_id)
            if unit:
                self.state.cursor_x = unit.x
                self.state.cursor_y = unit.y
    
    def _cycle_targetable_enemies(self) -> None:
        """Cycle through targetable enemy units (for tab cycling - excludes friendlies)."""
        game_map = self._ensure_game_map()
        
        # Get current unit
        if not self.state.selected_unit_id:
            return
            
        unit = game_map.get_unit(self.state.selected_unit_id)
        if not unit:
            return
        
        # Get all targetable enemy units if not already set
        if not self.state.targetable_enemies:
            self._refresh_targetable_enemies(unit)
        
        # Cycle to next target
        next_target_id = self.state.cycle_targetable_enemies()
        if next_target_id:
            target_unit = game_map.get_unit(next_target_id)
            if target_unit:
                self.state.cursor_x = target_unit.x
                self.state.cursor_y = target_unit.y
    
    def _refresh_selectable_units(self) -> None:
        """Update the list of selectable player units."""
        game_map = self._ensure_game_map()
        player_units = game_map.get_units_by_team(Team.PLAYER)
        selectable_ids = [unit.unit_id for unit in player_units if unit.can_move or unit.can_act]
        self.state.set_selectable_units(selectable_ids)
    
    def _refresh_targetable_enemies(self, attacking_unit) -> None:
        """Update the list of targetable enemy units (for tab cycling - only enemies)."""
        game_map = self._ensure_game_map()
        attack_range = game_map.calculate_attack_range(attacking_unit)
        
        targetable_ids = []
        for x, y in attack_range:
            target_unit = game_map.get_unit_at(x, y)
            # Only include enemy units for tab cycling, not friendlies
            if target_unit and target_unit.unit_id != attacking_unit.unit_id and target_unit.team != attacking_unit.team:
                targetable_ids.append(target_unit.unit_id)
        
        self.state.set_targetable_enemies(targetable_ids)
    
    def _position_cursor_on_first_player_unit(self) -> None:
        """Position the cursor on the first available player unit."""
        if not self.game_map:
            # Fallback to default position
            self.state.cursor_x = 2
            self.state.cursor_y = 2
            return
            
        player_units = self.game_map.get_units_by_team(Team.PLAYER)
        if player_units:
            # Position cursor on first player unit
            first_unit = player_units[0]
            self.state.cursor_x = first_unit.x
            self.state.cursor_y = first_unit.y
        else:
            # Fallback to default position if no player units found
            self.state.cursor_x = 2
            self.state.cursor_y = 2
    
    def _position_cursor_on_next_player_unit(self) -> None:
        """Position cursor on the next available player unit after completing an action."""
        game_map = self._ensure_game_map()
        
        if not self.state.selectable_units:
            # No selectable units, try to position on any player unit
            player_units = game_map.get_units_by_team(Team.PLAYER)
            if player_units:
                # Position on first available player unit
                next_unit = player_units[0]
                self.state.cursor_x = next_unit.x
                self.state.cursor_y = next_unit.y
            return
        
        # Find a different unit than the one currently at cursor position
        current_unit_at_cursor = game_map.get_unit_at(self.state.cursor_x, self.state.cursor_y)
        current_unit_id = current_unit_at_cursor.unit_id if current_unit_at_cursor else None
        
        # Look for the next selectable unit that's different from current
        next_unit_id = None
        attempts = 0
        max_attempts = len(self.state.selectable_units)
        
        while attempts < max_attempts:
            candidate_id = self.state.get_current_selectable_unit()
            if not candidate_id:
                candidate_id = self.state.cycle_selectable_units()
            
            # If this unit is different from current, use it
            if candidate_id and candidate_id != current_unit_id:
                next_unit_id = candidate_id
                break
            
            # Otherwise cycle to next unit
            self.state.cycle_selectable_units()
            attempts += 1
        
        # If we couldn't find a different unit, just use current selectable unit
        if not next_unit_id:
            next_unit_id = self.state.get_current_selectable_unit()
        
        # Position cursor on the selected unit
        if next_unit_id:
            next_unit = game_map.get_unit(next_unit_id)
            if next_unit:
                self.state.cursor_x = next_unit.x
                self.state.cursor_y = next_unit.y
    
    def _position_cursor_on_closest_target(self, attacking_unit) -> None:
        """Position cursor on the closest targetable enemy unit."""
        if not self.state.targetable_enemies:
            return
            
        game_map = self._ensure_game_map()
        closest_target = None
        closest_distance = float('inf')
        
        # Find the closest targetable enemy unit
        for target_id in self.state.targetable_enemies:
            target_unit = game_map.get_unit(target_id)
            if target_unit:
                # Calculate Manhattan distance
                distance = abs(attacking_unit.x - target_unit.x) + abs(attacking_unit.y - target_unit.y)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_target = target_unit
        
        # Position cursor on closest target
        if closest_target:
            self.state.cursor_x = closest_target.x
            self.state.cursor_y = closest_target.y
            
            # Update the target index to match the cursor position
            try:
                target_index = self.state.targetable_enemies.index(closest_target.unit_id)
                self.state.current_target_index = target_index
            except ValueError:
                pass  # Target not in list, keep current index
    
    def _execute_attack(self) -> None:
        """Execute AOE attack centered on cursor position."""
        cursor_x = self.state.cursor_x
        cursor_y = self.state.cursor_y
        
        if not self.state.is_in_attack_range(cursor_x, cursor_y):
            return
        
        if not self.state.selected_unit_id:
            return
            
        game_map = self._ensure_game_map()
        attacker = game_map.get_unit(self.state.selected_unit_id)
        
        if not attacker:
            return
        
        # Calculate AOE tiles based on cursor position
        aoe_tiles = game_map.calculate_aoe_tiles((cursor_x, cursor_y), attacker.combat.aoe_pattern)
        
        # Find all targets in AOE area (both enemy and friendly)
        targets_hit = []
        friendly_targets = []
        for tile_x, tile_y in aoe_tiles:
            target = game_map.get_unit_at(tile_x, tile_y)
            if target and target.unit_id != attacker.unit_id:  # Can hit any unit except the attacker
                targets_hit.append(target)
                # Check if target is on the same team as attacker (friendly fire)
                if target.team == attacker.team:
                    friendly_targets.append(target)
        
        # Must have at least one valid target to attack
        if not targets_hit:
            return
        
        # If there are friendly units that will be hit, show confirmation dialog
        if friendly_targets:
            friendly_names = [target.name for target in friendly_targets]
            if len(friendly_names) == 1:
                self.state.state_data["friendly_fire_message"] = f"This attack will hit your ally {friendly_names[0]}!"
            else:
                self.state.state_data["friendly_fire_message"] = f"This attack will hit your allies: {', '.join(friendly_names)}!"
            
            # Store the attack data for later execution
            self.state.state_data["pending_attack"] = {
                "cursor_x": cursor_x,
                "cursor_y": cursor_y,
                "targets_hit": targets_hit
            }
            
            self.state.open_dialog("confirm_friendly_fire")
            return  # Wait for user confirmation
        
        # No friendly fire, execute attack immediately
        self._perform_attack_damage(attacker, targets_hit)
    
    def _perform_attack_damage(self, attacker, targets_hit) -> None:
        """Apply damage to targets and handle attack resolution."""
        game_map = self._ensure_game_map()
        
        # Apply damage to all targets in AOE
        defeated_targets = []
        for target in targets_hit:
            # Calculate damage (simple calculation)
            damage = max(1, attacker.combat.strength - target.combat.defense // 2)
            
            # Apply damage
            target.hp_current = max(0, target.hp_current - damage)
            
            # Check if target is defeated
            if target.hp_current <= 0:
                game_map.remove_unit(target.unit_id)
                defeated_targets.append(target.name)
                print(f"{attacker.name} defeats {target.name}!")
            else:
                print(f"{attacker.name} attacks {target.name} for {damage} damage!")
        
        # Show summary if multiple targets
        if len(targets_hit) > 1:
            print(f"{attacker.name}'s {attacker.combat.aoe_pattern} attack hits {len(targets_hit)} targets!")
        
        # Mark attacker as having acted and moved (can't do anything else)
        attacker.has_moved = True  # Prevent further movement after attacking
        attacker.has_acted = True  # Prevent further actions
        
        # End unit's turn
        self.end_unit_turn()
    
    def _execute_confirmed_attack(self) -> None:
        """Execute an attack that was confirmed by the player after friendly fire warning."""
        if not self.state.selected_unit_id:
            return
            
        game_map = self._ensure_game_map()
        attacker = game_map.get_unit(self.state.selected_unit_id)
        
        if not attacker:
            return
            
        # Get the stored attack data
        pending_attack = self.state.state_data.get("pending_attack")
        if not pending_attack:
            return
            
        targets_hit = pending_attack["targets_hit"]
        
        # Clear the stored attack data
        del self.state.state_data["pending_attack"]
        if "friendly_fire_message" in self.state.state_data:
            del self.state.state_data["friendly_fire_message"]
        
        # Execute the attack
        self._perform_attack_damage(attacker, targets_hit)

    def handle_cancel(self) -> None:
        if self.state.battle_phase == BattlePhase.UNIT_MOVING:
            self.state.reset_selection()
            self.state.battle_phase = BattlePhase.UNIT_SELECTION
        elif self.state.battle_phase == BattlePhase.ACTION_MENU:
            # Cancel action menu - go back to movement if unit hasn't moved yet
            if self.state.selected_unit_id:
                game_map = self._ensure_game_map()
                unit = game_map.get_unit(self.state.selected_unit_id)
                if unit and not unit.has_moved:
                    self.state.close_action_menu()
                    self.state.battle_phase = BattlePhase.UNIT_MOVING
                    movement_range = game_map.calculate_movement_range(unit)
                    self.state.set_movement_range(list(movement_range))
                else:
                    # Unit has already moved - restore to original position and allow re-movement
                    if (unit and self.state.original_unit_x is not None and 
                        self.state.original_unit_y is not None):
                        # Restore unit to original position
                        game_map.move_unit(unit.unit_id, self.state.original_unit_x, self.state.original_unit_y)
                        unit.has_moved = False
                        
                        # Go back to movement phase to allow re-positioning
                        self.state.close_action_menu()
                        self.state.battle_phase = BattlePhase.UNIT_MOVING
                        movement_range = game_map.calculate_movement_range(unit)
                        self.state.set_movement_range(list(movement_range))
                        
                        # Position cursor on the restored unit
                        self.state.cursor_x = unit.x
                        self.state.cursor_y = unit.y
                    else:
                        # Fallback: deselect and refresh (if restoration fails)
                        self.state.reset_selection()
                        self.state.battle_phase = BattlePhase.UNIT_SELECTION
                        self._refresh_selectable_units()
        elif self.state.battle_phase == BattlePhase.TARGETING:
            # Cancel targeting - clear attack targeting data and return to action menu
            self.state.attack_range.clear()
            self.state.selected_target = None
            self.state.aoe_tiles.clear()
            self.state.battle_phase = BattlePhase.ACTION_MENU
            if self.state.selected_unit_id:
                game_map = self._ensure_game_map()
                unit = game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    self._build_action_menu_for_unit(unit)
        elif self.state.battle_phase == BattlePhase.UNIT_ACTING:
            self.state.attack_range.clear()
            self.state.aoe_tiles.clear()
            self.state.targetable_enemies.clear()
            self.state.current_target_index = 0
            self.state.battle_phase = BattlePhase.ACTION_MENU
            if self.state.selected_unit_id:
                game_map = self._ensure_game_map()
                unit = game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    self._build_action_menu_for_unit(unit)
    
    def update_movement_preview(self) -> None:
        pass
    
    def end_unit_turn(self) -> None:
        self.state.reset_selection()
        self.state.battle_phase = BattlePhase.UNIT_SELECTION
        
        # Refresh selectable units list
        self._refresh_selectable_units()
        
        # Position cursor on next available player unit
        self._position_cursor_on_next_player_unit()
        
        game_map = self._ensure_game_map()
        player_units = game_map.get_units_by_team(Team.PLAYER)
        if all(not unit.can_move and not unit.can_act for unit in player_units):
            # All player units have finished their actions - start enemy turn
            # Note: Do NOT call unit.end_turn() here, flags should stay set until next turn starts
            self.state.start_enemy_turn()
            self.simple_enemy_turn()
            
        # Check objectives after each action
        self.check_objectives()
    
    def _build_action_menu_for_unit(self, unit) -> None:
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
        
        # Future actions can be added here:
        # if unit.has_skills(): actions.append("Skill")
        # if unit.has_items(): actions.append("Item")
        
        self.state.open_action_menu(actions)
        
        # Auto-select the most appropriate action
        self._auto_select_action_menu_item(unit)
    
    def _auto_select_action_menu_item(self, unit) -> None:
        """Automatically select the most appropriate action in the menu."""
        if not unit.can_act:
            # Unit can't act, select Wait
            if "Wait" in self.state.action_menu_items:
                self.state.action_menu_selection = self.state.action_menu_items.index("Wait")
            return
        
        # Check if there are ENEMY targets in attack range (not friendlies)
        game_map = self._ensure_game_map()
        attack_range = game_map.calculate_attack_range(unit)
        has_enemy_targets = False
        
        for x, y in attack_range:
            target_unit = game_map.get_unit_at(x, y)
            if target_unit and target_unit.unit_id != unit.unit_id and target_unit.team != unit.team:
                has_enemy_targets = True
                break
        
        # Select Attack only if there are enemy targets, otherwise Wait
        if has_enemy_targets and "Attack" in self.state.action_menu_items:
            self.state.action_menu_selection = self.state.action_menu_items.index("Attack")
        elif "Wait" in self.state.action_menu_items:
            self.state.action_menu_selection = self.state.action_menu_items.index("Wait")
    
    def _setup_attack_targeting(self, unit) -> None:
        """Set up attack targeting for a unit."""
        game_map = self._ensure_game_map()
        
        # Clear movement range and set attack range
        self.state.movement_range.clear()
        attack_range = game_map.calculate_attack_range(unit)
        self.state.set_attack_range(list(attack_range))
        
        # Set up targetable enemies for cycling
        self._refresh_targetable_enemies(unit)
        
        # Position cursor on closest target
        self._position_cursor_on_closest_target(unit)
        
        # Update targeting and AOE
        self._update_attack_targeting()
    
    def _update_attack_targeting(self) -> None:
        """Update attack targeting based on cursor position."""
        if not self.state.attack_range:
            return
            
        cursor_pos = (self.state.cursor_x, self.state.cursor_y)
        
        # Check if cursor is over a valid attack target
        if cursor_pos in self.state.attack_range:
            self.state.selected_target = cursor_pos
            
            # Calculate AOE tiles if we have a selected unit
            if self.state.selected_unit_id:
                game_map = self._ensure_game_map()
                unit = game_map.get_unit(self.state.selected_unit_id)
                if unit and hasattr(unit.combat, 'aoe_pattern'):
                    aoe_pattern = unit.combat.aoe_pattern
                    self.state.aoe_tiles = game_map.calculate_aoe_tiles(cursor_pos, aoe_pattern)
                else:
                    self.state.aoe_tiles = [cursor_pos]
        else:
            self.state.selected_target = None
            self.state.aoe_tiles.clear()
    
    def _handle_action_selection(self, action: str) -> None:
        """Handle the selected action from the action menu."""
        if action == "Move":
            # Go back to movement targeting
            if self.state.selected_unit_id:
                game_map = self._ensure_game_map()
                unit = game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    self.state.close_action_menu()
                    self.state.battle_phase = BattlePhase.UNIT_MOVING
                    movement_range = game_map.calculate_movement_range(unit)
                    self.state.set_movement_range(list(movement_range))
        
        elif action == "Attack":
            # Go to attack targeting
            if self.state.selected_unit_id:
                game_map = self._ensure_game_map()
                unit = game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    self.state.close_action_menu()
                    self.state.battle_phase = BattlePhase.UNIT_ACTING
                    self._setup_attack_targeting(unit)
        
        elif action == "Wait":
            # End unit's turn
            if self.state.selected_unit_id:
                game_map = self._ensure_game_map()
                unit = game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    # When waiting, unit should not be able to move or act anymore
                    unit.has_moved = True  # Prevent further movement
                    unit.has_acted = True  # Prevent further actions
                    self.state.close_action_menu()
                    self.end_unit_turn()
    
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
    
    def simple_enemy_turn(self) -> None:
        game_map = self._ensure_game_map()
        for unit in game_map.get_units_by_team(Team.ENEMY):
            unit.end_turn()
        
        for unit in game_map.get_units_by_team(Team.PLAYER):
            unit.start_turn()
        
        self.state.battle_phase = BattlePhase.UNIT_SELECTION
        
        # Refresh selectable units for new turn
        self._refresh_selectable_units()
        
        # Position cursor on first available player unit for new turn
        self._position_cursor_on_next_player_unit()
        
        # Check objectives at end of turn
        self.check_objectives()
    
    def check_objectives(self) -> None:
        """Check victory and defeat conditions."""
        if not self.scenario:
            return
        
        game_map = self._ensure_game_map()
        turn = self.state.current_turn
        
        # Check victory conditions
        if self.scenario.check_victory(game_map, turn):
            self.handle_victory()
            return
        
        # Check defeat conditions
        if self.scenario.check_defeat(game_map, turn):
            self.handle_defeat()
            return
    
    def handle_victory(self) -> None:
        """Handle victory condition."""
        self.state.phase = GamePhase.GAME_OVER
        self.state.state_data["game_over_message"] = "Victory!"
        print("\n=== VICTORY! ===")
        if self.scenario:
            print(f"Scenario '{self.scenario.name}' completed!")
    
    def handle_defeat(self) -> None:
        """Handle defeat condition."""
        self.state.phase = GamePhase.GAME_OVER
        self.state.state_data["game_over_message"] = "Defeat!"
        print("\n=== DEFEAT ===")
        if self.scenario:
            print(f"Failed scenario: {self.scenario.name}")
    
    def render(self) -> None:
        context = self.build_render_context()
        self.renderer.clear()
        self.renderer.render_frame(context)
        self.renderer.present()
    
    def build_render_context(self) -> RenderContext:
        context = RenderContext()
        
        screen_width, screen_height = self.renderer.get_screen_size()
        viewport_height = screen_height - 3
        
        # Handle main menu rendering
        if self.state.phase == GamePhase.MAIN_MENU:
            return self._build_main_menu_context(screen_width, screen_height)
        
        self.state.update_camera_to_cursor(screen_width, viewport_height)
        
        context.viewport_x = self.state.camera_x
        context.viewport_y = self.state.camera_y
        context.viewport_width = screen_width
        context.viewport_height = viewport_height
        
        game_map = self._ensure_game_map()
        context.world_width = game_map.width
        context.world_height = game_map.height
        
        # Add game state information
        context.current_turn = self.state.current_turn
        context.current_team = self.state.current_team
        
        # Set timing for animations (convert to milliseconds)
        context.current_time_ms = int((time.time() - self.game_start_time) * 1000)
        for y in range(game_map.height):
            for x in range(game_map.width):
                tile = game_map.get_tile(x, y)
                if tile:
                    context.tiles.append(TileRenderData(
                        x=x,
                        y=y,
                        terrain_type=tile.terrain_type.name.lower(),
                        elevation=tile.elevation
                    ))
        
        for pos in self.state.movement_range:
            context.overlays.append(OverlayTileRenderData(
                x=pos[0],
                y=pos[1],
                overlay_type="movement",
                opacity=0.5
            ))
        
        # Use new AttackTargetRenderData for attack targeting
        from ..core.renderable import AttackTargetRenderData
        
        # Calculate blink phase for animation (500ms cycle)
        blink_phase = (context.current_time_ms // 500) % 2 == 1
        
        # Add all attack range tiles first
        for pos in self.state.attack_range:
            # Skip if this position will be handled as AOE or selected
            if pos not in self.state.aoe_tiles and pos != self.state.selected_target:
                context.attack_targets.append(AttackTargetRenderData(
                    x=pos[0],
                    y=pos[1],
                    target_type="range",
                    blink_phase=blink_phase
                ))
        
        # Add AOE tiles (including those outside attack range)
        for pos in self.state.aoe_tiles:
            if pos == self.state.selected_target:
                # Selected tile gets special treatment
                context.attack_targets.append(AttackTargetRenderData(
                    x=pos[0],
                    y=pos[1],
                    target_type="selected",
                    blink_phase=blink_phase
                ))
            else:
                # Other AOE tiles
                context.attack_targets.append(AttackTargetRenderData(
                    x=pos[0],
                    y=pos[1],
                    target_type="aoe",
                    blink_phase=blink_phase
                ))
        
        # Use centralized converter for unit render data with highlighting
        def highlight_units(unit):
            """Determine highlight type for units."""
            if (self.state.battle_phase == BattlePhase.UNIT_ACTING and 
                self.state.targetable_enemies and 
                unit.unit_id in self.state.targetable_enemies):
                return "target"
            return None
        
        context.units.extend(DataConverter.units_to_render_data_list(game_map.units, highlight_units))
        
        # Always set cursor position (for panels to read)
        context.cursor_x = self.state.cursor_x
        context.cursor_y = self.state.cursor_y
        
        # Add cursor with blinking effect (only visible when blinking on)
        if self.is_cursor_visible():
            context.cursor = CursorRenderData(
                x=self.state.cursor_x,
                y=self.state.cursor_y,
                cursor_type="default"
            )
        
        # Add action menu if active
        if self.state.is_action_menu_open():
            from ..core.renderable import MenuRenderData
            
            # Position the action menu in the sidebar area
            sidebar_width = 28 if screen_width >= 90 else 24
            menu_x = screen_width - sidebar_width + 1
            
            # Position will be handled by sidebar renderer - just provide the menu data
            # The sidebar renderer will calculate proper positioning based on actual panel heights
            menu_width = sidebar_width - 2
            menu_height = len(self.state.action_menu_items) + 3  # +3 for title and borders
            
            # Set a placeholder position - sidebar renderer will reposition it properly
            menu_y = 0
            
            context.menus.append(MenuRenderData(
                x=menu_x,
                y=menu_y,
                width=menu_width,
                height=menu_height,
                title="Actions",
                items=self.state.action_menu_items,
                selected_index=self.state.action_menu_selection
            ))
        
        status_text = f"Turn {self.state.current_turn} | "
        status_text += f"Phase: {self.state.battle_phase.name} | "
        status_text += f"Cursor: ({self.state.cursor_x}, {self.state.cursor_y}) | "
        status_text += "[Q]uit [Z]Confirm [X]Cancel"
        
        context.texts.append(TextRenderData(
            x=0,
            y=screen_height - 1,
            text=status_text
        ))
        
        # Add strategic TUI overlays if active
        if self.state.is_overlay_open():
            if self.state.active_overlay == "objectives":
                context.overlay = self._build_objectives_overlay()
            elif self.state.active_overlay == "help":
                context.overlay = self._build_help_overlay()
            elif self.state.active_overlay == "minimap":
                context.overlay = self._build_minimap_overlay()
        
        # Add dialog if active
        if self.state.is_dialog_open():
            context.dialog = self._build_dialog(self.state.active_dialog)
        
        # Add battle forecast if active
        if self.state.is_forecast_active():
            context.battle_forecast = self._build_battle_forecast()
        
        # Add banner if active
        banner = self._build_banner()
        if banner:
            context.banner = banner
        
        return context
    
    def _build_main_menu_context(self, screen_width: int, screen_height: int) -> RenderContext:
        """Build render context for the main menu."""
        from ..core.renderable import MenuRenderData
        
        context = RenderContext()
        context.viewport_width = screen_width
        context.viewport_height = screen_height
        
        # Create menu data - allow wider menus for better formatting
        menu_width = min(90, screen_width - 4)
        self.scenario_menu.update_display_items(menu_width)
        menu_items = self.scenario_menu.display_items
        menu_height = min(len(menu_items) + 4, screen_height - 6)
        
        menu_x = (screen_width - menu_width) // 2
        menu_y = (screen_height - menu_height) // 2
        
        context.menus.append(MenuRenderData(
            x=menu_x,
            y=menu_y, 
            width=menu_width,
            height=menu_height,
            title="Select Scenario",
            items=menu_items,
            selected_index=self.scenario_menu.selected_display_line
        ))
        
        # Add instructions
        instructions = "[↑↓/WS] Navigate [Enter/Z] Select [Q] Quit"
        context.texts.append(TextRenderData(
            x=0,
            y=screen_height - 1,
            text=instructions[:screen_width]
        ))
        
        return context
    
    # Strategic TUI input handlers
    def handle_overlay_input(self, event: InputEvent) -> None:
        """Handle input while overlay (objectives/help/minimap) is open."""
        # Close overlay on any key press for now (to be enhanced later)
        if event.event_type == InputType.KEY_PRESS:
            self.state.close_overlay()
    
    def handle_dialog_input(self, event: InputEvent) -> None:
        """Handle input while confirmation dialog is open."""
        if event.key in {Key.LEFT, Key.RIGHT}:
            self.state.move_dialog_selection(1 if event.key == Key.RIGHT else -1)
        elif event.is_confirm_key():
            # Handle dialog confirmation
            if self.state.active_dialog == "confirm_end_turn":
                if self.state.get_dialog_selection() == 0:  # Yes
                    self.end_player_turn()
            elif self.state.active_dialog == "confirm_friendly_fire":
                if self.state.get_dialog_selection() == 0:  # Yes - proceed with attack
                    self._execute_confirmed_attack()
                # If No (selection == 1), just close dialog and cancel attack
            self.state.close_dialog()
        elif event.is_cancel_key():
            self.state.close_dialog()
    
    def handle_forecast_input(self, event: InputEvent) -> None:
        """Handle input while battle forecast is active."""
        # For now, any key closes forecast (to be enhanced later)
        if event.event_type == InputType.KEY_PRESS:
            self.state.stop_forecast()
    
    def handle_objectives_key(self) -> None:
        """Handle O key press to show objectives."""
        self.state.open_overlay("objectives")
    
    def handle_help_key(self) -> None:
        """Handle ? key press to show help."""
        self.state.open_overlay("help")
    
    def handle_minimap_key(self) -> None:
        """Handle M key press to show minimap."""
        self.state.open_overlay("minimap")
    
    def handle_end_turn_key(self) -> None:
        """Handle E key press to end turn (with confirmation)."""
        self.state.open_dialog("confirm_end_turn")
    
    def handle_attack_key(self) -> None:
        """Handle A key press for direct attack."""
        # Only allow during player turn and when a unit is selected
        if self.state.current_team != 0 or not self.state.selected_unit_id:
            return
            
        game_map = self._ensure_game_map()
        unit = game_map.get_unit(self.state.selected_unit_id)
        if not unit or not unit.can_act:
            return
            
        # Handle quick attack based on current phase
        if self.state.battle_phase == BattlePhase.UNIT_SELECTION:
            # Unit just selected, transition to attack directly
            self.state.battle_phase = BattlePhase.UNIT_ACTING
            self._setup_attack_targeting(unit)
        elif self.state.battle_phase == BattlePhase.UNIT_MOVING:
            # Unit is in movement, skip to attack
            self.state.movement_range.clear()
            self.state.battle_phase = BattlePhase.UNIT_ACTING
            self._setup_attack_targeting(unit)
        elif self.state.battle_phase == BattlePhase.ACTION_MENU:
            # Use normal action selection
            self._handle_action_selection("Attack")
    
    def handle_wait_key(self) -> None:
        """Handle W key press for direct wait."""
        # Only allow during player turn and when a unit is selected
        if self.state.current_team != 0 or not self.state.selected_unit_id:
            return
            
        game_map = self._ensure_game_map()
        unit = game_map.get_unit(self.state.selected_unit_id)
        if not unit:
            return
            
        # When waiting, unit should not be able to move or act anymore
        unit.has_moved = True  # Prevent further movement
        unit.has_acted = True  # Prevent further actions
        self.end_unit_turn()
    
    def end_player_turn(self) -> None:
        """End the current player turn."""
        # Placeholder - proper turn management implementation  
        old_team = self.state.current_team
        self.state.current_team = (self.state.current_team + 1) % 4
        if self.state.current_team == 0:
            self.state.current_turn += 1
            
        # When changing teams, reset unit statuses for the new team
        if self.state.current_team != old_team:
            self._reset_team_unit_statuses(self.state.current_team)
            
            # Show phase banner when changing teams
            team_names = {0: "PLAYER PHASE", 1: "ENEMY PHASE", 2: "ALLY PHASE", 3: "NEUTRAL PHASE"}
            phase_name = team_names.get(self.state.current_team, "UNKNOWN PHASE")
            self.show_banner(phase_name)
            
            # Start enemy turn timer if switching to non-player team
            if self.state.current_team != 0:
                self.enemy_turn_start_time = time.time()
    
    def _reset_team_unit_statuses(self, team: int) -> None:
        """Reset all unit statuses for the specified team at the start of their turn."""
        from ..core.game_enums import Team
        
        game_map = self._ensure_game_map()
        team_enum = Team(team)
        
        for unit in game_map.units.values():
            if unit.team == team_enum and unit.is_alive:
                unit.start_turn()  # Reset has_moved and has_acted flags
    
    def _build_objectives_overlay(self) -> "OverlayRenderData":
        """Build objectives overlay content."""
        from ..core.renderable import OverlayRenderData
        
        if not self.scenario:
            return OverlayRenderData(
                overlay_type="objectives",
                width=60,
                height=15,
                title="Mission Objectives",
                content=["No scenario loaded"]
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
            content=content
        )
    
    def _build_help_overlay(self) -> "OverlayRenderData":
        """Build comprehensive help overlay with key bindings."""
        from ..core.renderable import OverlayRenderData
        
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
            "Press any key to continue..."
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
            content=content
        )
    
    def _build_minimap_overlay(self) -> "OverlayRenderData":
        """Build minimap overlay with compressed world view."""
        from ..core.renderable import OverlayRenderData
        
        game_map = self._ensure_game_map()
        
        # Calculate minimap dimensions (2×1 compression)
        minimap_width = (game_map.width + 1) // 2  # Round up for odd widths
        minimap_height = game_map.height
        
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
        for unit in game_map.units.values():
            if unit.is_alive:
                unit_map[(unit.x, unit.y)] = unit.team.value
        
        # Build minimap content
        content = [
            "BATTLEFIELD MINIMAP",
            "",
            "Legend: P=Player E=Enemy A=Ally N=Neutral",
            "        □=Camera View",
            ""
        ]
        
        # Generate minimap lines
        for map_y in range(0, game_map.height, scale_y):
            line = ""
            for map_x in range(0, game_map.width, scale_x * 2):
                # Sample a 2×scale_y area and determine what to show
                char = self._get_minimap_char(
                    game_map, unit_map, map_x, map_y, scale_x, scale_y
                )
                
                # Check if this position is in the camera view
                camera_left = self.state.camera_x
                camera_right = self.state.camera_x + self.renderer.get_screen_size()[0] - 28  # Account for sidebar
                camera_top = self.state.camera_y
                camera_bottom = self.state.camera_y + self.renderer.get_screen_size()[1] - 3  # Account for status
                
                if (camera_left <= map_x < camera_right and 
                    camera_top <= map_y < camera_bottom):
                    char = '□'  # Camera view indicator
                
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
            content=content
        )
    
    def _get_minimap_char(self, game_map, unit_map: dict, x: int, y: int, scale_x: int, scale_y: int) -> str:
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
                        return 'P'
                    elif team == 1:
                        return 'E'
                    elif team == 2:
                        return 'A'
                    else:
                        return 'N'
        
        # No units found, show terrain
        if x < game_map.width and y < game_map.height:
            tile = game_map.get_tile(x, y)
            if tile and tile.terrain_type in ['mountain', 'wall']:
                return '▲'  # Mountain/wall
            elif tile and tile.terrain_type == 'water':
                return '≈'  # Water
            elif tile and tile.terrain_type == 'forest':
                return '♣'  # Forest
            else:
                return '·'  # Open ground
        
        return ' '  # Empty space
    
    def show_banner(self, text: str, duration_ms: int = 2000) -> None:
        """Show an ephemeral banner with the given text."""
        self.active_banner = text
        self.banner_start_time = time.time()
        
    def update_banner_timing(self) -> None:
        """Update banner timing and clear expired banners."""
        if self.active_banner:
            elapsed_ms = (time.time() - self.banner_start_time) * 1000
            if elapsed_ms >= 2000:  # Banner duration
                self.active_banner = None
    
    def is_cursor_visible(self) -> bool:
        """Check if cursor should be visible (2Hz blinking)."""
        elapsed_time = time.time() - self.game_start_time
        # Calculate which blink cycle we're in
        cycle_position = elapsed_time % (self.cursor_blink_interval * 2)
        # Cursor is visible during the first half of each cycle
        return cycle_position < self.cursor_blink_interval
    
    def update_enemy_turn(self) -> None:
        """Handle automatic enemy turn progression."""
        # Only process if it's not the player's turn and we have a start time
        if self.state.current_team != 0 and self.enemy_turn_start_time > 0:
            elapsed_time = time.time() - self.enemy_turn_start_time
            
            # After enemy turn duration, automatically end the enemy turn
            if elapsed_time >= self.enemy_turn_duration:
                # Show end turn message
                team_names = {1: "Enemy", 2: "Ally", 3: "Neutral"}
                team_name = team_names.get(self.state.current_team, "Unknown")
                self.show_banner(f"{team_name} Turn Complete")
                
                # Reset timer
                self.enemy_turn_start_time = 0
                
                # End the enemy turn (will cycle to next team/player)
                self.end_player_turn()
    
    def _build_banner(self) -> Optional["BannerRenderData"]:
        """Build turn/phase banner if active."""
        from ..core.renderable import BannerRenderData
        
        if not self.active_banner:
            return None
            
        elapsed_ms = int((time.time() - self.banner_start_time) * 1000)
        
        # Position banner at top-center
        screen_width = self.renderer.get_screen_size()[0]
        banner_width = min(len(self.active_banner) + 6, 30)  # Add padding, but not too wide
        banner_x = (screen_width - banner_width) // 2
        
        return BannerRenderData(
            x=banner_x,
            y=2,  # Top of screen with some margin
            width=banner_width,
            text=self.active_banner,
            duration_ms=2000,
            elapsed_ms=elapsed_ms
        )
    
    def _build_dialog(self, dialog_type: str) -> "DialogRenderData":
        """Build confirmation dialog."""
        from ..core.renderable import DialogRenderData
        
        if dialog_type == "confirm_end_turn":
            return DialogRenderData(
                x=20, y=10,  # Will be centered by renderer
                width=24,
                height=6,
                title="Confirm",
                message="End Player Turn?",
                options=["Yes", "No"],
                selected_option=self.state.get_dialog_selection()
            )
        elif dialog_type == "confirm_friendly_fire":
            friendly_fire_message = self.state.state_data.get("friendly_fire_message", "This attack will hit friendly units!")
            # Calculate dialog width based on message length
            dialog_width = min(max(len(friendly_fire_message) + 4, 30), 60)
            return DialogRenderData(
                x=20, y=10,  # Will be centered by renderer
                width=dialog_width,
                height=7,
                title="Friendly Fire Warning",
                message=friendly_fire_message,
                options=["Attack Anyway", "Cancel"],
                selected_option=self.state.get_dialog_selection()
            )
        
        # Default dialog
        return DialogRenderData(
            x=20, y=10,
            width=24,
            height=6,
            title="Confirm",
            message="Are you sure?",
            options=["Yes", "No"],
            selected_option=self.state.get_dialog_selection()
        )
    
    def _build_battle_forecast(self) -> "BattleForecastRenderData":
        """Build battle forecast popup."""
        from ..core.renderable import BattleForecastRenderData
        
        # Placeholder implementation - will be enhanced when targeting is implemented
        return BattleForecastRenderData(
            x=10, y=5,  # Will be positioned by calculator
            attacker_name="Knight",
            defender_name="Archer",
            damage=15,
            hit_chance=85,
            crit_chance=12,
            can_counter=True,
            counter_damage=8
        )

    def cleanup(self) -> None:
        self.renderer.stop()