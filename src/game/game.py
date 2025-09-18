"""
Main game orchestration class.

This module coordinates all game systems and managers, maintaining the core
game loop and high-level state management while delegating specific concerns
to specialized manager classes.
"""

import time
from typing import Optional, TypeVar

from ..core.events.event_manager import EventManager
from ..core.events.events import GameEnded, GameStarted, LogMessage, ScenarioLoaded
from ..core.engine.game_state import BattlePhase, GamePhase, GameState
from ..core.input import InputType
from ..core.renderer import Renderer
from .input_handler import InputHandler
from .map import GameMap
from .render_builder import RenderBuilder
from .managers.combat_manager import CombatManager
from .managers.log_manager import LogManager
from .managers.phase_manager import PhaseManager
from .managers.scenario_manager import ScenarioManager
from .managers.selection_manager import SelectionManager
from .managers.timeline_manager import TimelineManager
from .managers.ui_manager import UIManager
from .scenarios.scenario import Scenario
from .scenarios.scenario_menu import ScenarioMenu


TManager = TypeVar("TManager")


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

        # Event system
        self.event_manager = EventManager(enable_debug_logging=False)

        # Managers - will be initialized in initialize()
        # Using private variables with properties for fail-fast validation
        self._log_manager: Optional[LogManager] = None
        self._phase_manager: Optional[PhaseManager] = None
        self._ui_manager: Optional[UIManager] = None
        self._combat_manager: Optional[CombatManager] = None
        self._input_handler: Optional[InputHandler] = None
        self._timeline_manager: Optional[TimelineManager] = None
        self._render_builder: Optional[RenderBuilder] = None
        self._scenario_manager: Optional[ScenarioManager] = None
        self._selection_manager: Optional[SelectionManager] = None

    # Properties for managers with fail-fast validation
    def _require_manager(self, manager: Optional[TManager], name: str) -> TManager:
        """Return the manager if initialized, otherwise raise a helpful error."""

        if manager is None:
            raise RuntimeError(f"{name} not initialized. Call initialize() first.")
        return manager

    @property
    def log_manager(self) -> LogManager:
        return self._require_manager(self._log_manager, "LogManager")

    @property
    def phase_manager(self) -> PhaseManager:
        return self._require_manager(self._phase_manager, "PhaseManager")

    @property
    def ui_manager(self) -> UIManager:
        return self._require_manager(self._ui_manager, "UIManager")

    @property
    def combat_manager(self) -> CombatManager:
        return self._require_manager(self._combat_manager, "CombatManager")

    @property
    def timeline_manager(self) -> TimelineManager:
        return self._require_manager(self._timeline_manager, "TimelineManager")

    @property
    def render_builder(self) -> RenderBuilder:
        return self._require_manager(self._render_builder, "RenderBuilder")

    @property
    def input_handler(self) -> InputHandler:
        return self._require_manager(self._input_handler, "InputHandler")

    @property
    def scenario_manager(self) -> ScenarioManager:
        return self._require_manager(self._scenario_manager, "ScenarioManager")

    @property
    def selection_manager(self) -> SelectionManager:
        return self._require_manager(self._selection_manager, "SelectionManager")

    # Keep the _ensure_game_map for now since game_map is not a manager
    def _ensure_game_map(self) -> GameMap:
        """Ensure game_map is initialized, raise error if not."""
        if self.game_map is None:
            raise RuntimeError("Game map not initialized. Call initialize() first.")
        return self.game_map

    def initialize(self) -> None:
        """Initialize the game and all manager systems."""
        self.renderer.start()

        # Set up event system
        self._setup_event_system()

        # Determine if we should start a battle immediately or stay in main menu
        if self.scenario and self.game_map:
            # We have a scenario and map - emit scenario loaded event to trigger phase transition
            self._emit_log(f"Direct battle start with scenario: {self.scenario.name}")

            # Emit scenario loaded event (PhaseManager will handle the phase transition)
            self.event_manager.publish(
                ScenarioLoaded(
                    turn=0,
                    scenario_name=self.scenario.name,
                    scenario_path=getattr(self.scenario, "filepath", "unknown"),
                ),
                source="Game",
            )

            # Process events immediately to trigger phase transition
            self.event_manager.process_events()
        elif self.state.phase != GamePhase.MAIN_MENU and self.game_map is None:
            # This should never happen - being in a game phase without a map is a bug
            raise RuntimeError(
                f"Invalid state: In {self.state.phase} phase but no game_map exists. "
                "Game map must be loaded before entering any phase other than MAIN_MENU."
            )

        # Initialize managers
        self._initialize_managers()

        # Wire up manager callbacks
        self._setup_manager_callbacks()

        # Initialize timeline if in battle phase
        if self.state.phase == GamePhase.BATTLE:
            self._emit_log("Post-manager initialization: Starting timeline system")
            self.timeline_manager.initialize_battle_timeline()

        # Emit game started event
        self.event_manager.publish(
            GameStarted(
                turn=0, scenario_name=self.scenario.name if self.scenario else None
            ),
            source="Game",
        )

        self.running = True

    def _setup_event_system(self) -> None:
        """Set up the event system and subscriptions."""
        # Update log manager with event manager for event-driven logging
        self._log_manager = LogManager(
            event_manager=self.event_manager, game_state=self.state
        )

        # Set debug callback for event logging
        self.event_manager.set_debug_callback(self.log_manager.debug)

        # Initialize phase manager (needs to be early to handle phase transitions)
        self._phase_manager = PhaseManager(
            game_state=self.state, event_manager=self.event_manager
        )

    def _initialize_managers(self) -> None:
        """Initialize manager systems based on what's available."""

        # Input Handler - needed immediately for menu navigation
        self._input_handler = InputHandler(
            game_state=self.state,
            renderer=self.renderer,
            event_manager=self.event_manager,
            scenario_menu=self.scenario_menu,
        )

        # Render Builder - needed immediately for menu rendering
        self._render_builder = RenderBuilder(
            game_state=self.state,
            renderer=self.renderer,
            log_manager=self.log_manager,
            scenario_menu=self.scenario_menu,
        )

        # Scenario Manager - needed for menu scenario loading
        self._scenario_manager = ScenarioManager(
            game_state=self.state,
            event_manager=self.event_manager,
            scenario_menu=self.scenario_menu,
        )

        # Initialize map-dependent managers only if we have a map
        if self.game_map:
            self._initialize_map_dependent_managers()
            self._configure_battle_managers()

    def _initialize_map_dependent_managers(self) -> None:
        """Initialize managers that require a game map."""
        game_map = self._ensure_game_map()

        # Create ALL map-dependent managers unconditionally

        # UI Manager
        self._ui_manager = UIManager(
            game_map=game_map,
            game_state=self.state,
            renderer=self.renderer,
            event_manager=self.event_manager,
            scenario=self.scenario,
        )

        # Selection Manager
        self._selection_manager = SelectionManager(
            game_map=game_map,
            game_state=self.state,
            event_manager=self.event_manager,
        )

        # Combat Manager
        self._combat_manager = CombatManager(
            game_map=game_map,
            game_state=self.state,
            event_manager=self.event_manager,
        )

        # Timeline Manager
        self._timeline_manager = TimelineManager(
            game_map=game_map,
            game_state=self.state,
            event_manager=self.event_manager,
        )

        # Inject dependencies into existing managers using setter methods

    def _configure_battle_managers(self) -> None:
        """Configure cross-manager dependencies for active battles."""

        game_map = self._ensure_game_map()

        self.render_builder.configure_battle_dependencies(
            game_map=game_map,
            ui_manager=self.ui_manager,
        )

        self.input_handler.configure_battle_dependencies(
            game_map=game_map,
            combat_manager=self.combat_manager,
            ui_manager=self.ui_manager,
            timeline_manager=self.timeline_manager,
        )

        if self.scenario:
            self.ui_manager.set_scenario(self.scenario)

    def _setup_manager_callbacks(self) -> None:
        """Wire up callbacks between managers and main game.

        This is called after _initialize_immediate_managers, so we only
        set up callbacks for managers that are guaranteed to exist at this point.
        Map-dependent manager callbacks are set up elsewhere.
        """

        self.input_handler.on_quit = self._handle_quit
        self.input_handler.on_load_selected_scenario = self.load_selected_scenario

    def _emit_log(
        self, message: str, category: str = "SYSTEM", level: str = "INFO"
    ) -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=self.state.battle.current_turn,
                message=message,
                category=category,
                level=level,
                source="Game",
            ),
            source="Game",
        )

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
        # Process queued events first
        self.event_manager.process_events()

        # Update UI timing during battle
        if self.state.phase == GamePhase.BATTLE:
            self.ui_manager.update_banner_timing()

            # Process timeline if in timeline processing phase
            if self.state.battle.phase == BattlePhase.TIMELINE_PROCESSING:
                self.timeline_manager.process_timeline()

        events = self.renderer.get_input_events()

        # Handle different game phases for input routing
        if self.state.phase == GamePhase.GAME_OVER:
            self.input_handler.handle_input_events(events)
            return

        if self.state.phase == GamePhase.MAIN_MENU:
            for event in events:
                if event.event_type == InputType.QUIT:
                    self.running = False
                elif event.event_type == InputType.KEY_PRESS:
                    self.input_handler.handle_main_menu_input(event)
            return

        # Handle battle phase input
        self.input_handler.handle_input_events(events)

        # Process high-priority events immediately after input handling
        if self.event_manager.has_high_priority_events():
            self.event_manager.process_events()

    def render(self) -> None:
        """Render the current frame."""
        context = self.render_builder.build_render_context()
        self.renderer.clear()
        self.renderer.render_frame(context)
        self.renderer.present()

    def load_selected_scenario(self) -> None:
        """Load the scenario selected from the menu."""
        # Load scenario through ScenarioManager
        scenario, game_map = self.scenario_manager.load_selected_scenario_from_menu()

        # Update game references
        self.scenario = scenario
        self.game_map = game_map

        # Initialize map-dependent managers now that we have a game map
        self._initialize_map_dependent_managers()

        # Update all managers with new scenario and map
        self._configure_battle_managers()

        # Process events immediately to trigger phase transition
        self.event_manager.process_events()

        # Initialize objective system and timeline
        self.scenario_manager.initialize_objective_system()
        self.timeline_manager.initialize_battle_timeline()

    # Callback handlers for managers
    def _handle_quit(self) -> None:
        """Handle quit request from input handler."""
        self.running = False

    def cleanup(self) -> None:
        """Clean up resources."""
        # Emit game ended event
        self.event_manager.publish(
            GameEnded(turn=0, result="quit", reason="cleanup"), source="Game"
        )

        # Process final events
        self.event_manager.process_events()

        # Shutdown event system
        self.event_manager.shutdown()

        self.renderer.stop()
