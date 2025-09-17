"""
Main game orchestration class.

This module coordinates all game systems and managers, maintaining the core
game loop and high-level state management while delegating specific concerns
to specialized manager classes.
"""

import time
from typing import Optional

from ..core.actions import ActionResult
from ..core.data_structures import Vector2
from ..core.event_manager import EventManager
from ..core.events import GameEnded, GameStarted, LogMessage, ScenarioLoaded, UnitMoved
from ..core.game_enums import Team
from ..core.game_state import BattlePhase, GamePhase, GameState
from ..core.game_view import GameView
from ..core.input import InputType
from ..core.renderer import Renderer
from .combat_manager import CombatManager
from .input_handler import InputHandler
from .log_manager import LogManager
from .map import GameMap
from .phase_manager import PhaseManager
from .render_builder import RenderBuilder
from .scenario import Scenario
from .scenario_loader import ScenarioLoader
from .scenario_menu import ScenarioMenu
from .timeline_manager import TimelineManager
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

        # Event system
        self.event_manager = EventManager(enable_debug_logging=False)

        # Managers - will be initialized in initialize()
        self.log_manager: Optional[LogManager] = (
            None  # Will be initialized with event manager in _setup_event_system()
        )
        self.phase_manager: Optional[PhaseManager] = (
            None  # Will be initialized with event manager
        )
        self.ui_manager: Optional[UIManager] = None
        self.combat_manager: Optional[CombatManager] = None
        self.input_handler: Optional[InputHandler] = None
        self.timeline_manager: Optional[TimelineManager] = None
        self.render_builder: Optional[RenderBuilder] = None

    def _ensure_game_map(self) -> GameMap:
        """Ensure game_map is initialized, raise error if not."""
        if self.game_map is None:
            raise RuntimeError("Game map not initialized. Call initialize() first.")
        return self.game_map
    
    def _ensure_ui_manager(self) -> "UIManager":
        """Ensure ui_manager is initialized, raise error if not."""
        if self.ui_manager is None:
            raise RuntimeError("UI manager not initialized. Call initialize() first.")
        return self.ui_manager
    
    def _ensure_combat_manager(self) -> "CombatManager":
        """Ensure combat_manager is initialized, raise error if not."""
        if self.combat_manager is None:
            raise RuntimeError("Combat manager not initialized. Call initialize() first.")
        return self.combat_manager
    
    def _ensure_timeline_manager(self) -> "TimelineManager":
        """Ensure timeline_manager is initialized, raise error if not."""  
        if self.timeline_manager is None:
            raise RuntimeError("Timeline manager not initialized. Call initialize() first.")
        return self.timeline_manager
    
    def _ensure_render_builder(self) -> "RenderBuilder":
        """Ensure render_builder is initialized, raise error if not."""
        if self.render_builder is None:
            raise RuntimeError("Render builder not initialized. Call initialize() first.")
        return self.render_builder
    
    def _ensure_input_handler(self) -> "InputHandler":
        """Ensure input_handler is initialized, raise error if not."""
        if self.input_handler is None:
            raise RuntimeError("Input handler not initialized. Call initialize() first.")
        return self.input_handler
    
    def _ensure_log_manager(self) -> "LogManager":
        """Ensure log_manager is initialized, raise error if not."""
        if self.log_manager is None:
            raise RuntimeError("Log manager not initialized. Call initialize() first.")
        return self.log_manager


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
            # Load default scenario if we're not in main menu but have no map
            self._emit_log("Loading default scenario...")
            self._load_default_scenario()

        # Initialize managers
        self._initialize_managers()

        # Wire up manager callbacks
        self._setup_manager_callbacks()

        # Initialize timeline if in battle phase
        if self.state.phase == GamePhase.BATTLE and self.timeline_manager:
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
        self.log_manager = LogManager(
            event_manager=self.event_manager, game_state=self.state
        )
        
        # Set debug callback for event logging
        log_manager = self._ensure_log_manager()
        self.event_manager.set_debug_callback(log_manager.debug)

        # Initialize phase manager (needs to be early to handle phase transitions)
        self.phase_manager = PhaseManager(
            game_state=self.state, event_manager=self.event_manager
        )

        # Subscribe to system events
        from ..core.events import EventType

        self.event_manager.subscribe(
            EventType.UNIT_DEFEATED,
            self._handle_unit_defeated_event,
            subscriber_name="Game.unit_defeated",
        )
        # REMOVED: UnitAttacked events should be handled by CombatManager, not Game class
        # This avoids duplicate/conflicting combat processing
        self.event_manager.subscribe(
            EventType.UNIT_DAMAGED,
            self._handle_unit_damaged_event,
            subscriber_name="Game.unit_damaged",
        )
        self.event_manager.subscribe(
            EventType.OBJECTIVES_CHECK_REQUESTED,
            self._handle_objectives_check_requested,
            subscriber_name="Game.objectives_check",
        )
        self.event_manager.subscribe(
            EventType.UNIT_SPAWNED,
            self._handle_unit_spawned_event,
            subscriber_name="Game.unit_spawned",
        )

    def _initialize_managers(self) -> None:
        """Initialize manager systems based on what's available."""
        # Always initialize managers that don't need a map
        self._initialize_immediate_managers()

        # Initialize map-dependent managers only if we have a map
        if self.game_map:
            self._initialize_map_dependent_managers()

    def _initialize_immediate_managers(self) -> None:
        """Initialize managers that work without a map (for menu support)."""
        # Input Handler - needed immediately for menu navigation
        self.input_handler = InputHandler(
            game_map=self.game_map,  # Can be None initially
            game_state=self.state,
            renderer=self.renderer,
            event_manager=self.event_manager,
            combat_manager=None,  # Will be updated later
            ui_manager=None,  # Will be updated later
            scenario_menu=self.scenario_menu,
            timeline_manager=None,  # Will be updated later
        )

        # Render Builder - needed immediately for menu rendering
        self.render_builder = RenderBuilder(
            game_map=self.game_map,  # Can be None initially for menu
            game_state=self.state,
            renderer=self.renderer,
            scenario_menu=self.scenario_menu,
            ui_manager=None,  # Will be updated later
            log_manager=self.log_manager,
        )

    def _initialize_map_dependent_managers(self) -> None:
        """Initialize managers that require a game map."""
        game_map = self._ensure_game_map()

        # UI Manager - only create if it doesn't exist
        if not self.ui_manager:
            self._emit_log("Creating UIManager", category="SYSTEM")
            self.ui_manager = UIManager(
                game_map=game_map,
                game_state=self.state,
                renderer=self.renderer,
                event_manager=self.event_manager,
                scenario=self.scenario,
            )
            self._emit_log(
                "UIManager created and subscribed to events", category="SYSTEM"
            )
        else:
            # Update existing UIManager with new game map and scenario
            self._emit_log("Updating existing UIManager", category="SYSTEM")
            self.ui_manager.game_map = game_map
            if self.scenario:
                self.ui_manager.set_scenario(self.scenario)

        # Update Render Builder with the game map and UI manager
        render_builder = self._ensure_render_builder()
        render_builder.game_map = game_map
        render_builder.ui_manager = self._ensure_ui_manager()

        # Game-specific managers are created during scenario loading
        # This avoids duplicate instances and ensures they're properly initialized with the correct scenario

        # Update InputHandler with map-dependent managers
        input_handler = self._ensure_input_handler()
        input_handler.ui_manager = self._ensure_ui_manager()
        # Note: combat_manager and timeline_manager are updated separately after scenario loading

    def _initialize_additional_managers(self, game_map: "GameMap") -> None:
        """Initialize the additional managers that were migrated to EventManager."""
        from .escalation_manager import EscalationManager
        from .morale_manager import MoraleManager

        # Morale Manager
        self.morale_manager = MoraleManager(
            game_state=self.state,
            game_map=game_map,
            event_manager=self.event_manager,
        )

        # Escalation Manager (if we have a scenario)
        if self.scenario:
            self.escalation_manager = EscalationManager(
                game_state=self.state,
                game_map=game_map,
                scenario=self.scenario,
                event_manager=self.event_manager,
            )

        # TODO: Initialize Hazard Manager when hazard system is complete
        # The hazard system is WIP - not initializing until fully implemented
        # self.hazard_manager = HazardManager(
        #     game_state=self.state,
        #     game_map=game_map,
        #     event_manager=self.event_manager,
        # )
        # self.state.hazard_manager = self.hazard_manager

    def _setup_manager_callbacks(self) -> None:
        """Wire up callbacks between managers and main game."""
        if self.input_handler:
            self.input_handler.on_quit = self._handle_quit
            self.input_handler.on_end_unit_turn = self._handle_end_unit_turn
            self.input_handler.on_end_team_turn = self._handle_end_team_turn
            self.input_handler.on_load_selected_scenario = self.load_selected_scenario
            self.input_handler.on_movement_preview_update = self.update_movement_preview

        if self.timeline_manager:
            # TODO: Replace these callbacks with event subscriptions
            # self.timeline_manager.on_check_objectives = self.check_objectives
            # self.timeline_manager.on_ai_take_turn = self._handle_ai_turn
            pass

    # ==================== PHASE TRANSITION METHODS ====================

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

    def _load_default_scenario(self) -> None:
        """Load the default test scenario if no map/scenario provided."""
        scenario_path = "assets/scenarios/default_test.yaml"
        try:
            self.scenario = ScenarioLoader.load_from_file(scenario_path)
            self.game_map = ScenarioLoader.create_game_map(self.scenario)
            ScenarioLoader.place_units(self.scenario, self.game_map, self.event_manager)

            # Initialize event-driven objective system
            self._initialize_objective_system()

            # Initialize battle system if in battle phase
            if self.state.phase == GamePhase.BATTLE:
                self._emit_log("Initializing battle system...", level="SYSTEM")
                if self.timeline_manager:
                    self._emit_log("Using timeline manager", level="SYSTEM")
                    # Timeline system handles cursor positioning automatically
                    self.timeline_manager.initialize_battle_timeline()
                else:
                    self._emit_log(
                        "Timeline manager not available, using fallback", level="WARNING"
                    )
                    # Position cursor on first player unit for legacy system
                    self._position_cursor_on_first_player_unit()
                    # Fallback to old system
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
        # Process queued events first
        self.event_manager.process_events()

        # Update banner timing
        if self.ui_manager:
            self.ui_manager.update_banner_timing()

        # Handle timeline processing when in battle
        if self.state.phase == GamePhase.BATTLE and self.timeline_manager:
            # Debug: Log battle phase every frame when debugging is on
            log_manager = self._ensure_log_manager()
            if log_manager.is_debug_enabled():
                current_phase = self.state.battle.phase
                if (
                    not hasattr(self, "_last_logged_phase")
                    or self._last_logged_phase != current_phase
                ):
                    self._last_logged_phase = current_phase

                    if current_phase.name == "UNIT_MOVING":
                        movement_range_size = len(self.state.battle.movement_range)
                        selected_unit_id = self.state.battle.selected_unit_id
                        if movement_range_size == 0 and selected_unit_id:
                            # This is the bug! Unit is in UNIT_MOVING phase but has no movement range
                            self._emit_log("*** CRITICAL BUG DETECTED ***", level="ERROR")
                            self._emit_log(
                                f"Unit {selected_unit_id} is in UNIT_MOVING phase but has NO movement range!",
                                level="ERROR"
                            )

                            # Try to recover by forcing timeline processing
                            self._emit_log(
                                "Attempting recovery by forcing timeline processing...",
                                level="ERROR"
                            )
                            # Recovery: Let TimelineManager handle this transition properly
                            # TimelineManager should emit TimelineProcessed event

            # Process timeline if in timeline processing phase
            if self.state.battle.phase == BattlePhase.TIMELINE_PROCESSING:
                # Process next timeline entry

                # Check timeline state before processing
                if hasattr(self.timeline_manager.timeline, "is_empty") and hasattr(
                    self.timeline_manager.timeline, "_queue"
                ):
                    is_empty = self.timeline_manager.timeline.is_empty
                    queue_size = len(self.timeline_manager.timeline._queue)

                    if queue_size > 0 and not is_empty:
                        # Show next few entries for debugging
                        preview = self.timeline_manager.timeline.get_preview(2)
                        for entry in preview:
                            if entry.entity_type == "unit":
                                game_map = self._ensure_game_map()
                                unit = game_map.get_unit(entry.entity_id)
                                assert unit is not None, (
                                    f"Timeline entry references non-existent unit: {entry.entity_id}"
                                )

                self.timeline_manager.process_timeline()

        # Handle game over state
        if self.state.phase == GamePhase.GAME_OVER:
            events = self.renderer.get_input_events()
            if self.input_handler:
                self.input_handler.handle_input_events(events)
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
            
            # Process high-priority events immediately after input handling
            # This ensures phase transitions and critical user actions happen without delay
            if self.event_manager.has_high_priority_events():
                self.event_manager.process_events()

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
                ScenarioLoader.place_units(scenario, self.game_map, self.event_manager)

                # Emit scenario loaded event
                self.event_manager.publish(
                    ScenarioLoaded(
                        turn=0,
                        scenario_name=scenario.name,
                        scenario_path=getattr(scenario, "filepath", "unknown"),
                    ),
                    source="Game",
                )

                # Process events immediately to trigger phase transition
                self.event_manager.process_events()

                self._emit_log(f"Scenario loaded: {scenario.name}")

                # Re-initialize managers with new map
                self._reinitialize_managers_for_new_scenario()

                # Initialize event-driven objective system
                self._initialize_objective_system()

                # Transition to battle phase (PhaseManager will handle this via ScenarioLoaded event)

                # Initialize timeline battle system
                if self.timeline_manager:
                    # Timeline system handles cursor positioning automatically
                    self.timeline_manager.initialize_battle_timeline()
                else:
                    # Legacy system - position cursor on first player unit
                    self._position_cursor_on_first_player_unit()
                    # This transition should now be handled by PhaseManager
                    # The TimelineManager should emit appropriate events for unit selection
                    self._refresh_selectable_units()

            except Exception as e:
                self._emit_log(f"Failed to load scenario: {e}", level="ERROR")
                # Stay in main menu on error

    def _reinitialize_managers_for_new_scenario(self) -> None:
        """Re-initialize managers when a new scenario is loaded."""
        # Initialize map-dependent managers (including UIManager if it doesn't exist)
        self._initialize_map_dependent_managers()

        game_map = self._ensure_game_map()

        # Re-create managers that depend on the map
        self.combat_manager = CombatManager(
            game_map=game_map, game_state=self.state, event_manager=self.event_manager
        )

        self.timeline_manager = TimelineManager(
            game_map=game_map,
            game_state=self.state,
            event_manager=self.event_manager,
        )

        # Update input handler with new managers
        if self.input_handler:
            self.input_handler.game_map = game_map
            self.input_handler.combat_manager = self.combat_manager
            self.input_handler.timeline_manager = self.timeline_manager

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
        # Emit game ended event - PhaseManager will handle transition to GAME_OVER
        self.event_manager.publish(
            GameEnded(
                turn=self.state.battle.current_turn if self.state.battle else 0,
                result="victory",
            ),
            source="Game",
        )
        
        # Create victory message
        if self.scenario:
            victory_message = f"Scenario '{self.scenario.name}' completed!"
        else:
            victory_message = "Mission accomplished!"
        
        # Show game over dialog through UI manager
        if self.ui_manager:
            self.ui_manager.show_game_over_dialog("victory", victory_message)
        
        self._emit_log("=== VICTORY! ===", level="SYSTEM")
        if self.scenario:
            self._emit_log(f"Scenario '{self.scenario.name}' completed!", level="SYSTEM")

    def handle_defeat(self) -> None:
        """Handle defeat condition."""
        # Emit game ended event - PhaseManager will handle transition to GAME_OVER
        self.event_manager.publish(
            GameEnded(
                turn=self.state.battle.current_turn if self.state.battle else 0,
                result="defeat",
            ),
            source="Game",
        )
        
        # Create defeat message
        if self.scenario:
            defeat_message = f"Failed: {self.scenario.name}"
        else:
            defeat_message = "Mission failed!"
        
        # Show game over dialog through UI manager
        if self.ui_manager:
            self.ui_manager.show_game_over_dialog("defeat", defeat_message)
        
        self._emit_log("=== DEFEAT ===", level="SYSTEM")
        if self.scenario:
            self._emit_log(f"Failed scenario: {self.scenario.name}", level="SYSTEM")

    def update_movement_preview(self) -> None:
        """Update movement preview (placeholder for future implementation)."""
        pass

    # Callback handlers for managers
    def _handle_quit(self) -> None:
        """Handle quit request from input handler."""
        self.running = False

    def _handle_end_unit_turn(self) -> None:
        """Handle end of unit turn from input handler."""
        # Timeline manager already handles unit scheduling with correct weights
        # Just clear the UI state and let timeline manager handle the rest
        if self.state.battle.current_acting_unit_id:
            self.state.battle.selected_unit_id = None
            self.state.battle.current_acting_unit_id = None
            self.state.ui.close_action_menu()

        # Check objectives after action
        self.check_objectives()

    def _handle_end_team_turn(self) -> None:
        """Handle end of team turn from input handler."""
        # In timeline system, there are no team turns - just individual unit actions
        pass

    def _handle_ai_turn(self, unit, ai_decision) -> None:
        """Handle AI unit taking its turn."""
        # Log the AI decision
        self._emit_log(
            f"AI {unit.name} executes {ai_decision.action_name}: {ai_decision.reasoning}",
            category="AI"
        )

        # CRITICAL: Actually execute the AI decision!
        if self.timeline_manager:
            result = self.timeline_manager.execute_unit_action(
                ai_decision.action_name, ai_decision.target
            )

            if result != ActionResult.SUCCESS:
                self._emit_log(f"AI action failed with result: {result}", level="ERROR")

            # AI action complete - TimelineManager should handle continuation
            # TimelineManager should emit TimelineProcessed when AI turn ends

    # Unit management helpers
    def _refresh_selectable_units(self) -> None:
        """Update the list of selectable player units."""
        if not self.game_map:
            return

        player_units = self.game_map.get_units_by_team(Team.PLAYER)
        selectable_ids = [
            unit.unit_id for unit in player_units if unit.can_move or unit.can_act
        ]
        self.state.battle.set_selectable_units(selectable_ids)

    def _position_cursor_on_first_player_unit(self) -> None:
        """Position the cursor on the first available player unit."""
        if not self.game_map:
            # Fallback to default position
            self.state.cursor.set_position(Vector2(2, 2))
            return

        player_units = self.game_map.get_units_by_team(Team.PLAYER)
        if player_units:
            # Position cursor on first player unit
            first_unit = player_units[0]
            self.state.cursor.set_position(first_unit.position)
        else:
            # Fallback to default position if no player units found
            self.state.cursor.set_position(Vector2(2, 2))

    def _position_cursor_on_next_player_unit(self) -> None:
        """Position cursor on the next available player unit after completing an action."""
        if not self.game_map:
            return

        if not self.state.battle.selectable_units:
            # No selectable units, try to position on any player unit
            player_units = self.game_map.get_units_by_team(Team.PLAYER)
            if player_units:
                # Position on first available player unit
                next_unit = player_units[0]
                self.state.cursor.set_position(next_unit.position)
            return

        # Find a different unit than the one currently at cursor position
        current_unit_at_cursor = self.game_map.get_unit_at(self.state.cursor.position)
        current_unit_id = (
            current_unit_at_cursor.unit_id if current_unit_at_cursor else None
        )

        # Look for the next selectable unit that's different from current
        next_unit_id = None
        attempts = 0
        max_attempts = len(self.state.battle.selectable_units)

        while attempts < max_attempts:
            candidate_id = self.state.battle.get_current_selectable_unit()
            if not candidate_id:
                candidate_id = self.state.battle.cycle_selectable_units()

            # If this unit is different from current, use it
            if candidate_id and candidate_id != current_unit_id:
                next_unit_id = candidate_id
                break

            # Otherwise cycle to next unit
            self.state.battle.cycle_selectable_units()
            attempts += 1

        # If we couldn't find a different unit, just use current selectable unit
        if not next_unit_id:
            next_unit_id = self.state.battle.get_current_selectable_unit()

        # Position cursor on the selected unit
        if next_unit_id:
            next_unit = self.game_map.get_unit(next_unit_id)
            if next_unit:
                self.state.cursor.set_position(next_unit.position)

    def _initialize_objective_system(self) -> None:
        """Initialize the event-driven objective system for the current scenario."""
        if not self.scenario or not self.game_map:
            return

        # Create GameView adapter
        game_view = GameView(self.game_map)

        # Initialize scenario's ObjectiveManager with event manager for logging
        self.scenario.initialize_objective_manager(game_view, self.event_manager)

    def _emit_event(self, event) -> None:
        """Emit a game event through the event manager."""
        # Publish through event manager (will handle all subscriptions)
        self.event_manager.publish(event, source="Game")

        # Note: Specific event types are forwarded to scenario in their dedicated handlers
        # to avoid duplicate processing (e.g., _handle_unit_defeated_event, _handle_unit_spawned_event)

    def _handle_system_events(self, event) -> None:
        """Handle events that affect internal game systems."""
        from ..core.events import UnitDamaged, UnitDefeated

        if isinstance(event, UnitDefeated):
            self._handle_unit_defeated_event(event)
        elif isinstance(event, UnitDamaged):
            self._handle_unit_damaged_event(event)

    def _handle_unit_defeated_event(self, event) -> None:
        """Handle unit defeat - clean up timeline entries and check objectives."""
        # Early return if no timeline manager
        if not self.timeline_manager:
            return

        # Clean up timeline when units are defeated
        removed_count = self.timeline_manager.timeline.remove_entry(event.unit_id)

        if self.log_manager and removed_count > 0:
            self.log_manager.timeline(
                f"Cleaned up {removed_count} timeline entries for defeated unit {event.unit_name}"
            )

        # Forward unit defeat event to scenario for objective checking
        if self.scenario:
            self.scenario.on_event(event)
        
        # Check objectives after unit defeat (critical for win/loss conditions)
        from ..core.events import ObjectivesCheckRequested
        self.event_manager.publish(
            ObjectivesCheckRequested(
                turn=self.state.battle.current_turn if self.state.battle else 0,
                trigger_reason="unit_defeated"
            ),
            source="Game"
        )

    # REMOVED: _handle_unit_attacked_event - redundant with CombatManager
    # All UnitAttacked events should be processed by CombatManager system

    def _handle_unit_damaged_event(self, event) -> None:
        """Handle non-combat damage (hazards, status effects, etc.)."""
        # TODO: Implement handling for environmental damage
        # This should also check for unit death and emit UnitDefeated events
        pass

    def _handle_objectives_check_requested(self, event) -> None:
        """Handle request to check objectives."""
        from ..core.events import ObjectivesCheckRequested
        
        if isinstance(event, ObjectivesCheckRequested):
            self.check_objectives()

    def _handle_unit_spawned_event(self, event) -> None:
        """Handle unit spawned event - forward to scenario for objective tracking."""
        from ..core.events import UnitSpawned
        
        if isinstance(event, UnitSpawned) and self.scenario:
            self.scenario.on_event(event)

    def _emit_unit_moved(
        self,
        unit_name: str,
        unit_id: str,
        team: Team,
        from_pos: tuple[int, int],
        to_pos: tuple[int, int],
    ) -> None:
        """Emit a unit moved event."""
        event = UnitMoved(
            turn=self.state.battle.current_turn,
            unit_name=unit_name,
            unit_id=unit_id,
            team=team,
            from_position=from_pos,
            to_position=to_pos,
        )
        self._emit_event(event)

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
