"""Main Scenario class for orchestrating game scenarios.

This module contains the core Scenario class that ties together objectives,
structures, and game state management.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from .objectives import Objective
from .scenario_structures import (
    ActorPlacement,
    ScenarioMarker,
    ScenarioObject,
    ScenarioRegion,
    ScenarioSettings,
    ScenarioTrigger,
    UnitData,
)

if TYPE_CHECKING:
    from ..core.game_view import GameView
    from .objective_manager import ObjectiveManager
    from ..core.event_manager import EventManager


@dataclass
class Scenario:
    """Container for all scenario data."""

    name: str
    description: str
    author: str = "Unknown"

    # Map file reference
    map_file: Optional[str] = None  # Path to external map file

    # Placement system
    markers: dict[str, ScenarioMarker] = field(default_factory=dict)
    regions: dict[str, ScenarioRegion] = field(default_factory=dict)
    placements: list[ActorPlacement] = field(default_factory=list)

    # Units to place (definitions only, no positions)
    units: list[UnitData] = field(default_factory=list)

    # Objects and triggers
    objects: list[ScenarioObject] = field(default_factory=list)
    triggers: list[ScenarioTrigger] = field(default_factory=list)

    # Objectives
    victory_objectives: list[Objective] = field(default_factory=list)
    defeat_objectives: list[Objective] = field(default_factory=list)

    # Settings
    settings: ScenarioSettings = field(default_factory=ScenarioSettings)

    # Map overrides for environmental variants
    map_overrides: dict[str, Any] = field(default_factory=dict)

    # Event-driven objective system
    objective_manager: Optional["ObjectiveManager"] = field(default=None, init=False)

    def initialize_objective_manager(self, game_view: "GameView", event_manager: Optional["EventManager"] = None) -> None:
        """Initialize the event-driven objective manager.

        Args:
            game_view: GameView adapter for objective queries
            event_manager: Event manager for logging (optional)
        """
        from .objective_manager import ObjectiveManager

        self.objective_manager = ObjectiveManager(game_view, event_manager)
        self.objective_manager.register_objectives(
            victory_objectives=self.victory_objectives,
            defeat_objectives=self.defeat_objectives,
        )

    def on_event(self, event) -> None:
        """Forward game events to the objective manager.

        Args:
            event: GameEvent to forward to objectives
        """
        if self.objective_manager:
            self.objective_manager.on_event(event)

    def check_victory(self) -> bool:
        """Check if all victory objectives are completed.

        Returns:
            True if all victory objectives are completed
        """
        if not self.victory_objectives:
            return False

        if not self.objective_manager:
            raise ValueError(
                "ObjectiveManager must be initialized before checking objectives"
            )

        return self.objective_manager.check_victory()

    def check_defeat(self) -> bool:
        """Check if any defeat objective has failed.

        Returns:
            True if any defeat objective has failed
        """
        if not self.objective_manager:
            raise ValueError(
                "ObjectiveManager must be initialized before checking objectives"
            )

        return self.objective_manager.check_defeat()

    def get_active_objectives(self) -> list[Objective]:
        """Get all objectives that are still in progress.

        Returns:
            List of objectives with IN_PROGRESS status
        """
        if not self.objective_manager:
            raise ValueError(
                "ObjectiveManager must be initialized before checking objectives"
            )

        return self.objective_manager.get_active_objectives()