"""Scenario management system.

This module handles scenario loading, unloading, and manager reinitialization
that was previously scattered in game.py. It centralizes all scenario-related
operations and emits appropriate events for the game flow.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..core.event_manager import EventManager
    from ..core.game_state import GameState
    from .map import GameMap
    from .scenario import Scenario
    from .scenario_menu import ScenarioMenu

from ..core.events import (
    LogMessage,
    ManagerInitialized,
    ScenarioLoaded,
)
from ..core.game_view import GameView
from .scenario_loader import ScenarioLoader


class ScenarioManager:
    """Manages scenario loading and related manager reinitialization.
    
    Centralizes logic that was previously in game.py:
    - Loading scenarios from files or menu selections
    - Creating game maps from scenarios
    - Placing units and initializing game state
    - Reinitializing managers when scenarios change
    - Setting up objective systems
    """

    def __init__(
        self,
        game_state: "GameState",
        event_manager: "EventManager",
        scenario_menu: "ScenarioMenu",
    ):
        self.state = game_state
        self.event_manager = event_manager
        self.scenario_menu = scenario_menu
        
        # Private scenario and map (set when scenarios are loaded)
        self._current_scenario: Optional["Scenario"] = None
        self._current_game_map: Optional["GameMap"] = None

        # Emit initialization event
        self.event_manager.publish(
            ManagerInitialized(turn=0, manager_name="ScenarioManager"),
            source="ScenarioManager",
        )

    def _emit_log(
        self, message: str, category: str = "SCENARIO", level: str = "INFO"
    ) -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=self.state.battle.current_turn,
                message=message,
                category=category,
                level=level,
                source="ScenarioManager",
            ),
            source="ScenarioManager",
        )

    @property
    def current_scenario(self) -> "Scenario":
        """Get the currently loaded scenario."""
        assert self._current_scenario is not None, "No scenario loaded"
        return self._current_scenario

    @property
    def current_game_map(self) -> "GameMap":
        """Get the currently loaded game map."""
        assert self._current_game_map is not None, "No game map loaded"
        return self._current_game_map

    def load_selected_scenario_from_menu(self) -> tuple["Scenario", "GameMap"]:
        """Load the scenario selected from the menu."""
        scenario = self.scenario_menu.load_selected_scenario()
        assert scenario, "No scenario selected from menu"
        
        game_map = ScenarioLoader.create_game_map(scenario)
        ScenarioLoader.place_units(scenario, game_map, self.event_manager)
        
        self._current_scenario = scenario
        self._current_game_map = game_map
        
        self._emit_log(f"Loaded scenario from menu: {scenario.name}")
        
        # Emit scenario loaded event
        self.event_manager.publish(
            ScenarioLoaded(
                turn=0,
                scenario_name=scenario.name,
                scenario_path=getattr(scenario, "filepath", "unknown"),
            ),
            source="ScenarioManager",
        )
        
        return scenario, game_map

    def initialize_objective_system(self) -> None:
        """Initialize the event-driven objective system for the current scenario."""
        # Create GameView adapter
        game_view = GameView(self.current_game_map)

        # Initialize scenario's ObjectiveManager with event manager for logging
        self.current_scenario.initialize_objective_manager(game_view, self.event_manager)
        self._emit_log("Initialized objective system for scenario")


