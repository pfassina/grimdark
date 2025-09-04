"""
Main game orchestration class.

This module coordinates all game systems and managers, maintaining the core
game loop and high-level state management while delegating specific concerns
to specialized manager classes.
"""
import time
from typing import Optional

from ..core.events import UnitMoved
from ..core.game_enums import Team
from ..core.game_state import BattlePhase, GamePhase, GameState
from ..core.game_view import GameView
from ..core.input import InputType
from ..core.renderer import Renderer
from .combat_manager import CombatManager
from .input_handler import InputHandler
from .map import GameMap
from .render_builder import RenderBuilder
from .scenario import Scenario
from .scenario_loader import ScenarioLoader
from .scenario_menu import ScenarioMenu
from .turn_manager import TurnManager
from .ui_manager import UIManager


class Game:
    """Main game orchestrator that coordinates all game systems."""
    
    def __init__(
        self,
        game_map: Optional[GameMap],
        renderer: Renderer,
        scenario: Optional[Scenario] = None,
    ):
        self.renderer = renderer
        self.state = GameState(phase=GamePhase.MAIN_MENU)
        self.game_map = game_map
        self.scenario = scenario
        
        # Core systems
        self.scenario_menu = ScenarioMenu()
        self.running = False
        self.fps = 30
        self.frame_time = 1.0 / self.fps
        
        # Managers - will be initialized in initialize()
        self.ui_manager: Optional[UIManager] = None
        self.combat_manager: Optional[CombatManager] = None
        self.input_handler: Optional[InputHandler] = None
        self.turn_manager: Optional[TurnManager] = None
        self.render_builder: Optional[RenderBuilder] = None
    
    def _ensure_game_map(self) -> GameMap:
        """Ensure game_map is initialized, raise error if not."""
        if self.game_map is None:
            raise RuntimeError("Game map not initialized. Call initialize() first.")
        return self.game_map
    
    def initialize(self) -> None:
        """Initialize the game and all manager systems."""
        self.renderer.start()
        
        # Load default scenario if needed
        if self.state.phase != GamePhase.MAIN_MENU and self.game_map is None:
            self._load_default_scenario()
        
        # Initialize managers
        self._initialize_managers()
        
        # Wire up manager callbacks
        self._setup_manager_callbacks()
        
        self.running = True
    
    def _initialize_managers(self) -> None:
        """Initialize all manager systems."""
        game_map = self._ensure_game_map() if self.game_map else None
        
        # UI Manager - can work without a game map initially
        self.ui_manager = UIManager(
            game_map=game_map or GameMap(1, 1),  # Dummy map for initialization
            game_state=self.state,
            renderer=self.renderer,
            scenario=self.scenario
        )
        
        # Update with real map if available
        if game_map:
            self.ui_manager.game_map = game_map
        
        # Combat Manager
        if game_map:
            self.combat_manager = CombatManager(
                game_map=game_map,
                game_state=self.state,
                event_emitter=self._emit_event
            )
        
        # Turn Manager
        if game_map:
            self.turn_manager = TurnManager(
                game_map=game_map,
                game_state=self.state,
                event_emitter=self._emit_event,
                ui_manager=self.ui_manager
            )
        
        # Input Handler
        self.input_handler = InputHandler(
            game_map=game_map or GameMap(1, 1),  # Dummy map for initialization
            game_state=self.state,
            renderer=self.renderer,
            combat_manager=self.combat_manager,
            ui_manager=self.ui_manager,
            scenario_menu=self.scenario_menu
        )
        
        # Update with real map if available
        if game_map:
            self.input_handler.game_map = game_map
        
        # Render Builder
        self.render_builder = RenderBuilder(
            game_map=game_map or GameMap(1, 1),  # Dummy map for initialization
            game_state=self.state,
            renderer=self.renderer,
            scenario_menu=self.scenario_menu,
            ui_manager=self.ui_manager
        )
        
        # Update with real map if available
        if game_map:
            self.render_builder.game_map = game_map
    
    def _setup_manager_callbacks(self) -> None:
        """Wire up callbacks between managers and main game."""
        if self.input_handler:
            self.input_handler.on_quit = self._handle_quit
            self.input_handler.on_end_unit_turn = self._handle_end_unit_turn
            self.input_handler.on_load_selected_scenario = self.load_selected_scenario
            self.input_handler.on_movement_preview_update = self.update_movement_preview
        
        if self.turn_manager:
            self.turn_manager.on_refresh_selectable_units = self._refresh_selectable_units
            self.turn_manager.on_position_cursor_on_next_unit = self._position_cursor_on_next_player_unit
            self.turn_manager.on_check_objectives = self.check_objectives
    
    def _load_default_scenario(self) -> None:
        """Load the default test scenario if no map/scenario provided."""
        scenario_path = "assets/scenarios/default_test.yaml"
        try:
            self.scenario = ScenarioLoader.load_from_file(scenario_path)
            self.game_map = ScenarioLoader.create_game_map(self.scenario)
            ScenarioLoader.place_units(self.scenario, self.game_map)
            
            # Initialize event-driven objective system
            self._initialize_objective_system()
            
            # Position cursor on first player unit
            self._position_cursor_on_first_player_unit()
            
            # Initialize selectable units if in battle phase
            if self.state.phase == GamePhase.BATTLE:
                self._refresh_selectable_units()
                # Show initial phase banner
                if self.ui_manager:
                    self.ui_manager.show_banner("PLAYER PHASE")
        
        except FileNotFoundError:
            raise RuntimeError(
                f"Default scenario not found at {scenario_path}. Please provide a map or scenario."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load default scenario: {e}")
    
    def run(self) -> None:
        """Main game loop."""
        self.initialize()
        
        last_frame = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                delta_time = current_time - last_frame
                
                if delta_time >= self.frame_time:
                    self.update()
                    self.render()
                    last_frame = current_time
                else:
                    time.sleep(0.001)
        finally:
            self.cleanup()
    
    def update(self) -> None:
        """Update game state and process input."""
        # Update banner timing
        if self.ui_manager:
            self.ui_manager.update_banner_timing()
        
        # Handle enemy turn processing
        if self.turn_manager:
            self.turn_manager.update_enemy_turn_timing()
        
        # Handle game over state
        if self.state.phase == GamePhase.GAME_OVER:
            events = self.renderer.get_input_events()
            for event in events:
                if (
                    event.event_type == InputType.QUIT
                    or event.event_type == InputType.KEY_PRESS
                ):
                    self.running = False
            return
        
        # Handle main menu phase
        if self.state.phase == GamePhase.MAIN_MENU:
            events = self.renderer.get_input_events()
            if self.input_handler:
                for event in events:
                    if event.event_type == InputType.QUIT:
                        self.running = False
                    elif event.event_type == InputType.KEY_PRESS:
                        self.input_handler.handle_main_menu_input(event)
            return
        
        # Handle regular game input
        events = self.renderer.get_input_events()
        if self.input_handler:
            self.input_handler.handle_input_events(events)
    
    def render(self) -> None:
        """Render the current frame."""
        if self.render_builder:
            context = self.render_builder.build_render_context()
            self.renderer.clear()
            self.renderer.render_frame(context)
            self.renderer.present()
    
    def load_selected_scenario(self) -> None:
        """Load the scenario selected from the menu."""
        scenario = self.scenario_menu.load_selected_scenario()
        if scenario:
            try:
                self.scenario = scenario
                self.game_map = ScenarioLoader.create_game_map(scenario)
                ScenarioLoader.place_units(scenario, self.game_map)
                
                # Re-initialize managers with new map
                self._reinitialize_managers_for_new_scenario()
                
                # Initialize event-driven objective system
                self._initialize_objective_system()
                
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
    
    def _reinitialize_managers_for_new_scenario(self) -> None:
        """Re-initialize managers when a new scenario is loaded."""
        if self.ui_manager and self.scenario:
            self.ui_manager.set_scenario(self.scenario)
        
        game_map = self._ensure_game_map()
        
        # Re-create managers that depend on the map
        self.combat_manager = CombatManager(
            game_map=game_map,
            game_state=self.state,
            event_emitter=self._emit_event
        )
        
        self.turn_manager = TurnManager(
            game_map=game_map,
            game_state=self.state,
            event_emitter=self._emit_event,
            ui_manager=self.ui_manager
        )
        
        # Update input handler with new managers
        if self.input_handler:
            self.input_handler.game_map = game_map
            self.input_handler.combat_manager = self.combat_manager
        
        # Update render builder
        if self.render_builder:
            self.render_builder.game_map = game_map
        
        # Re-setup callbacks
        self._setup_manager_callbacks()
    
    def check_objectives(self) -> None:
        """Check victory and defeat conditions."""
        if not self.scenario:
            return
        
        # Check victory conditions
        if self.scenario.check_victory():
            self.handle_victory()
            return
        
        # Check defeat conditions
        if self.scenario.check_defeat():
            self.handle_defeat()
    
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
    
    def update_movement_preview(self) -> None:
        """Update movement preview (placeholder for future implementation)."""
        pass
    
    # Callback handlers for managers
    def _handle_quit(self) -> None:
        """Handle quit request from input handler."""
        self.running = False
    
    def _handle_end_unit_turn(self) -> None:
        """Handle end of unit turn from input handler."""
        if self.turn_manager:
            self.turn_manager.end_unit_turn()
    
    # Unit management helpers
    def _refresh_selectable_units(self) -> None:
        """Update the list of selectable player units."""
        if not self.game_map:
            return
        
        player_units = self.game_map.get_units_by_team(Team.PLAYER)
        selectable_ids = [
            unit.unit_id for unit in player_units if unit.can_move or unit.can_act
        ]
        self.state.set_selectable_units(selectable_ids)
    
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
        if not self.game_map:
            return
        
        if not self.state.selectable_units:
            # No selectable units, try to position on any player unit
            player_units = self.game_map.get_units_by_team(Team.PLAYER)
            if player_units:
                # Position on first available player unit
                next_unit = player_units[0]
                self.state.cursor_x = next_unit.x
                self.state.cursor_y = next_unit.y
            return
        
        # Find a different unit than the one currently at cursor position
        current_unit_at_cursor = self.game_map.get_unit_at(
            self.state.cursor_x, self.state.cursor_y
        )
        current_unit_id = (
            current_unit_at_cursor.unit_id if current_unit_at_cursor else None
        )
        
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
            next_unit = self.game_map.get_unit(next_unit_id)
            if next_unit:
                self.state.cursor_x = next_unit.x
                self.state.cursor_y = next_unit.y
    
    def _initialize_objective_system(self) -> None:
        """Initialize the event-driven objective system for the current scenario."""
        if not self.scenario or not self.game_map:
            return
        
        # Create GameView adapter
        game_view = GameView(self.game_map)
        
        # Initialize scenario's ObjectiveManager
        self.scenario.initialize_objective_manager(game_view)
    
    def _emit_event(self, event) -> None:
        """Emit a game event to the objective system."""
        # Forward to scenario's objective manager
        if self.scenario:
            self.scenario.on_event(event)
    
    def _emit_unit_moved(
        self,
        unit_name: str,
        team: Team,
        from_pos: tuple[int, int],
        to_pos: tuple[int, int],
    ) -> None:
        """Emit a unit moved event."""
        event = UnitMoved(
            turn=self.state.current_turn,
            unit_name=unit_name,
            team=team,
            from_position=from_pos,
            to_position=to_pos,
        )
        self._emit_event(event)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.renderer.stop()