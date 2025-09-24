"""Game objectives for victory and defeat conditions.

This module contains all objective implementations that define victory and defeat
conditions in scenarios. Objectives use an event-driven architecture to track
game state changes and determine when conditions are met.
"""

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ...core.events import EventType, ObjectiveContext
from ...core.events.events import UnitDefeated, UnitSpawned, UnitMoved
from ...core.data import ObjectiveStatus, ObjectiveType, Vector2
from ...core.data.game_enums import Team

if TYPE_CHECKING:
    from ...core.game_view import GameView


@dataclass
class Objective(ABC):
    """Base class for all objectives.

    Event-Driven Interface:
    - objectives subscribe to specific event types via 'interests' property
    - objectives receive events via 'on_event(context)' method
    - objectives can optionally implement 'recompute(view)' for initialization
    """

    objective_type: ObjectiveType
    description: str
    status: ObjectiveStatus = ObjectiveStatus.IN_PROGRESS

    @property
    def interests(self) -> tuple[EventType, ...]:
        """Return the event types this objective is interested in.

        Returns:
            Tuple of EventType values this objective wants to receive
        """
        return ()  # Default: no interests (subclasses should override)

    def on_event(self, context: ObjectiveContext) -> None:
        """Handle a game event and update objective status.

        Args:
            context: ObjectiveContext containing event and read-only game view
        """
        # Default implementation does nothing (subclasses should override)
        _ = context

    def recompute(self, view: "GameView") -> ObjectiveStatus:
        """Recompute objective status from current game state.

        This is called during objective initialization to align status
        with current game state. Optional for objectives to implement.

        Args:
            view: Read-only game view for querying current state

        Returns:
            The computed objective status
        """
        _ = view
        return self.status  # Default: keep current status


class DefeatAllEnemiesObjective(Objective):
    """Victory condition: defeat all enemy units."""

    def __init__(self, description: str = "Defeat all enemies"):
        super().__init__(ObjectiveType.DEFEAT_ALL_ENEMIES, description)
        self._enemy_count = 0  # Track enemy count for efficient updates

    @property
    def interests(self) -> tuple[EventType, ...]:
        """Subscribe to unit spawn/defeat events to track enemy count."""
        return (EventType.UNIT_SPAWNED, EventType.UNIT_DEFEATED)

    def on_event(self, context: ObjectiveContext) -> None:
        """Update enemy count and objective status based on events."""

        if isinstance(context.event, UnitSpawned):
            if context.event.unit.team == Team.ENEMY:
                self._enemy_count += 1
        elif isinstance(context.event, UnitDefeated):
            if context.event.unit.team == Team.ENEMY:
                self._enemy_count -= 1

        # Update status based on enemy count
        if self._enemy_count <= 0:
            self.status = ObjectiveStatus.COMPLETED
        else:
            self.status = ObjectiveStatus.IN_PROGRESS

    def recompute(self, view: "GameView") -> ObjectiveStatus:
        """Initialize enemy count from current game state."""

        self._enemy_count = view.count_units(Team.ENEMY, alive=True)

        if self._enemy_count <= 0:
            self.status = ObjectiveStatus.COMPLETED
        else:
            self.status = ObjectiveStatus.IN_PROGRESS

        return self.status




class ReachPositionObjective(Objective):
    """Victory condition: move a unit to a specific position."""

    def __init__(
        self,
        position: Vector2,
        unit_name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        desc = description or f"Move {unit_name or 'any unit'} to ({position.x}, {position.y})"
        super().__init__(ObjectiveType.REACH_POSITION, desc)
        self.unit_name = unit_name
        self.target_position = position

    @property
    def interests(self) -> tuple[EventType, ...]:
        """Subscribe to unit movement and defeat events."""
        return (EventType.UNIT_MOVED, EventType.UNIT_DEFEATED)

    def on_event(self, context: ObjectiveContext) -> None:
        """Check if unit reached target position or was defeated."""

        if isinstance(context.event, UnitMoved):
            # Check if a player unit reached the target position
            if context.event.unit.team == Team.PLAYER and context.event.unit.position == self.target_position:
                # If no specific unit required, or the right unit moved there
                if self.unit_name is None or context.event.unit.name == self.unit_name:
                    self.status = ObjectiveStatus.COMPLETED
                    return

        elif isinstance(context.event, UnitDefeated):
            # Check if the required unit was defeated
            if (
                self.unit_name
                and context.event.unit.name == self.unit_name
                and context.event.unit.team == Team.PLAYER
            ):
                self.status = ObjectiveStatus.FAILED
                return

        # Status remains IN_PROGRESS if no completion/failure conditions met

    def recompute(self, view: "GameView") -> ObjectiveStatus:
        """Check current game state for position occupancy and unit existence."""

        # Check if target position is occupied by appropriate unit
        unit_at_pos = view.get_unit_at(self.target_position)
        if unit_at_pos and unit_at_pos.team == Team.PLAYER:
            if self.unit_name is None or unit_at_pos.name == self.unit_name:
                self.status = ObjectiveStatus.COMPLETED
                return self.status

        # Check if required unit still exists
        if self.unit_name:
            required_unit = view.get_unit_by_name(self.unit_name)
            if not required_unit or required_unit.team != Team.PLAYER:
                self.status = ObjectiveStatus.FAILED
                return self.status

        self.status = ObjectiveStatus.IN_PROGRESS
        return self.status


class DefeatUnitObjective(Objective):
    """Victory condition: defeat a specific unit."""

    def __init__(self, unit_name: str, description: Optional[str] = None):
        desc = description or f"Defeat {unit_name}"
        super().__init__(ObjectiveType.DEFEAT_UNIT, desc)
        self.target_unit_name = unit_name

    @property
    def interests(self) -> tuple[EventType, ...]:
        """Subscribe to unit defeat events."""
        return (EventType.UNIT_DEFEATED,)

    def on_event(self, context: ObjectiveContext) -> None:
        """Check if target unit was defeated."""

        if isinstance(context.event, UnitDefeated):
            if context.event.unit.name == self.target_unit_name:
                self.status = ObjectiveStatus.COMPLETED

    def recompute(self, view: "GameView") -> ObjectiveStatus:
        """Check if target unit still exists."""
        target_unit = view.get_unit_by_name(self.target_unit_name)
        if target_unit and target_unit.is_alive:
            self.status = ObjectiveStatus.IN_PROGRESS
        else:
            # Unit not found or not alive, assume defeated
            self.status = ObjectiveStatus.COMPLETED
        return self.status


class ProtectUnitObjective(Objective):
    """Defeat condition: specific unit must survive."""

    def __init__(self, unit_name: str, description: Optional[str] = None):
        desc = description or f"Protect {unit_name}"
        super().__init__(ObjectiveType.PROTECT_UNIT, desc)
        self.protected_unit_name = unit_name

    @property
    def interests(self) -> tuple[EventType, ...]:
        """Subscribe to unit defeat events to detect protected unit death."""
        return (EventType.UNIT_DEFEATED,)

    def on_event(self, context: ObjectiveContext) -> None:
        """Check if protected unit was defeated."""

        if isinstance(context.event, UnitDefeated):
            if context.event.unit.name == self.protected_unit_name:
                self.status = ObjectiveStatus.FAILED

    def recompute(self, view: "GameView") -> ObjectiveStatus:
        """Check if protected unit still exists and is alive."""
        protected_unit = view.get_unit_by_name(self.protected_unit_name)
        if protected_unit and protected_unit.is_alive:
            self.status = ObjectiveStatus.IN_PROGRESS
        else:
            # Unit not found or not alive
            self.status = ObjectiveStatus.FAILED
        return self.status


class PositionCapturedObjective(Objective):
    """Defeat condition: enemy reaches specific position."""

    def __init__(self, position: Vector2, description: Optional[str] = None):
        desc = description or f"Prevent enemies from reaching ({position.x}, {position.y})"
        super().__init__(ObjectiveType.POSITION_CAPTURED, desc)
        self.position = position

    @property
    def interests(self) -> tuple[EventType, ...]:
        """Subscribe to unit movement events to detect position capture."""
        return (EventType.UNIT_MOVED,)

    def on_event(self, context: ObjectiveContext) -> None:
        """Check if enemy unit moved to protected position."""

        if isinstance(context.event, UnitMoved):
            if context.event.unit.team == Team.ENEMY and context.event.unit.position == self.position:
                self.status = ObjectiveStatus.FAILED

    def recompute(self, view: "GameView") -> ObjectiveStatus:
        """Check if position is currently occupied by enemy."""

        unit_at_pos = view.get_unit_at(self.position)
        if unit_at_pos and unit_at_pos.team == Team.ENEMY:
            self.status = ObjectiveStatus.FAILED
        else:
            self.status = ObjectiveStatus.IN_PROGRESS
        return self.status




class AllUnitsDefeatedObjective(Objective):
    """Defeat condition: all player units defeated."""

    def __init__(self, description: str = "Keep at least one unit alive"):
        super().__init__(ObjectiveType.ALL_UNITS_DEFEATED, description)
        self._player_count = 0  # Track player unit count

    @property
    def interests(self) -> tuple[EventType, ...]:
        """Subscribe to unit spawn/defeat events to track player unit count."""
        return (EventType.UNIT_SPAWNED, EventType.UNIT_DEFEATED)

    def on_event(self, context: ObjectiveContext) -> None:
        """Update player unit count and objective status."""

        if isinstance(context.event, UnitSpawned):
            if context.event.unit.team == Team.PLAYER:
                self._player_count += 1
        elif isinstance(context.event, UnitDefeated):
            if context.event.unit.team == Team.PLAYER:
                self._player_count -= 1

        # Update status based on player count
        if self._player_count <= 0:
            self.status = ObjectiveStatus.FAILED
        else:
            self.status = ObjectiveStatus.IN_PROGRESS

    def recompute(self, view: "GameView") -> ObjectiveStatus:
        """Initialize player unit count from current game state."""

        self._player_count = view.count_units(Team.PLAYER, alive=True)

        if self._player_count <= 0:
            self.status = ObjectiveStatus.FAILED
        else:
            self.status = ObjectiveStatus.IN_PROGRESS
        return self.status