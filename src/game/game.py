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
        if self.state.is_action_menu_open():
            self.handle_action_menu_input(event)
        elif self.state.is_menu_open():
            self.handle_menu_input(event)
        else:
            self.handle_map_input(event)
    
    def handle_map_input(self, event: InputEvent) -> None:
        if event.key == Key.Q:
            self.running = False
            return
        
        # Handle TAB key for cycling
        if event.key == Key.TAB:
            self.handle_tab_cycling()
            return
        
        if event.is_movement_key():
            dx, dy = 0, 0
            if event.key in {Key.UP, Key.W}:
                dy = -1
            elif event.key in {Key.DOWN, Key.S}:
                dy = 1
            elif event.key in {Key.LEFT, Key.A}:
                dx = -1
            elif event.key in {Key.RIGHT, Key.D}:
                dx = 1
            
            game_map = self._ensure_game_map()
            self.state.move_cursor(dx, dy, game_map.width, game_map.height)
            
            if self.state.selected_unit_id:
                self.update_movement_preview()
        
        elif event.is_confirm_key():
            self.handle_confirm()
        
        elif event.is_cancel_key():
            self.handle_cancel()
    
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
        """Cycle through targetable enemy units."""
        game_map = self._ensure_game_map()
        
        # Get current unit
        if not self.state.selected_unit_id:
            return
            
        unit = game_map.get_unit(self.state.selected_unit_id)
        if not unit:
            return
        
        # Get all targetable enemies if not already set
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
        """Update the list of targetable enemy units."""
        game_map = self._ensure_game_map()
        attack_range = game_map.calculate_attack_range(attacking_unit)
        
        targetable_ids = []
        for x, y in attack_range:
            enemy_unit = game_map.get_unit_at(x, y)
            if enemy_unit and enemy_unit.team != attacking_unit.team:
                targetable_ids.append(enemy_unit.unit_id)
        
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
        """Position cursor on the closest targetable enemy."""
        if not self.state.targetable_enemies:
            return
            
        game_map = self._ensure_game_map()
        closest_target = None
        closest_distance = float('inf')
        
        # Find the closest targetable enemy
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
        """Execute attack on target at cursor position."""
        cursor_x = self.state.cursor_x
        cursor_y = self.state.cursor_y
        
        if not self.state.is_in_attack_range(cursor_x, cursor_y):
            return
        
        if not self.state.selected_unit_id:
            return
            
        game_map = self._ensure_game_map()
        attacker = game_map.get_unit(self.state.selected_unit_id)
        target = game_map.get_unit_at(cursor_x, cursor_y)
        
        if not attacker or not target or target.team == attacker.team:
            return
        
        # Calculate damage (simple calculation)
        damage = max(1, attacker.combat.strength - target.combat.defense // 2)
        
        # Apply damage
        target.hp_current = max(0, target.hp_current - damage)
        
        # Check if target is defeated
        if target.hp_current <= 0:
            game_map.remove_unit(target.unit_id)
            print(f"{attacker.name} defeats {target.name}!")
        else:
            print(f"{attacker.name} attacks {target.name} for {damage} damage!")
        
        # Mark attacker as having acted
        attacker.has_acted = True
        
        # End unit's turn
        self.end_unit_turn()

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
                    # Unit has already moved, can't go back
                    self.state.reset_selection()
                    self.state.battle_phase = BattlePhase.UNIT_SELECTION
        elif self.state.battle_phase == BattlePhase.UNIT_ACTING:
            self.state.attack_range.clear()
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
            for unit in player_units:
                unit.end_turn()
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
        
        # Check if there are enemies in attack range
        game_map = self._ensure_game_map()
        attack_range = game_map.calculate_attack_range(unit)
        has_targets = False
        
        for x, y in attack_range:
            enemy_unit = game_map.get_unit_at(x, y)
            if enemy_unit and enemy_unit.team != unit.team:
                has_targets = True
                break
        
        # Select Attack if there are targets, otherwise Wait
        if has_targets and "Attack" in self.state.action_menu_items:
            self.state.action_menu_selection = self.state.action_menu_items.index("Attack")
        elif "Wait" in self.state.action_menu_items:
            self.state.action_menu_selection = self.state.action_menu_items.index("Wait")
    
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
                    attack_range = game_map.calculate_attack_range(unit)
                    self.state.set_attack_range(list(attack_range))
                    
                    # Set up targetable enemies for cycling
                    self._refresh_targetable_enemies(unit)
                    
                    # Position cursor on closest target
                    self._position_cursor_on_closest_target(unit)
                    
                    self.state.close_action_menu()
                    self.state.battle_phase = BattlePhase.UNIT_ACTING
        
        elif action == "Wait":
            # End unit's turn
            if self.state.selected_unit_id:
                game_map = self._ensure_game_map()
                unit = game_map.get_unit(self.state.selected_unit_id)
                if unit:
                    unit.has_acted = True
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
        
        for pos in self.state.attack_range:
            context.overlays.append(OverlayTileRenderData(
                x=pos[0],
                y=pos[1],
                overlay_type="attack",
                opacity=0.5
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
            menu_y = 19  # Position below terrain and unit panels, accounting for borders
            menu_width = sidebar_width - 2
            menu_height = len(self.state.action_menu_items) + 3  # +3 for title and borders
            
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
    
    def cleanup(self) -> None:
        self.renderer.stop()