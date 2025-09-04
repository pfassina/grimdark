"""Event-driven objective system events and context.

This module defines all game events that objectives can subscribe to,
following the event-driven architecture recommended for scalable objectives.

Event Design Principles:
- Events are immutable dataclasses with minimal payloads  
- All events include turn timestamp
- Events represent "what happened" with stable identifiers (names, coordinates, teams)
- Keep event types focused and avoid over-granular events
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from abc import ABC
from enum import Enum, auto

from .game_enums import Team

if TYPE_CHECKING:
    from .game_view import GameView


class EventType(Enum):
    """Types of game events that objectives can subscribe to."""
    TURN_STARTED = auto()
    TURN_ENDED = auto()
    UNIT_SPAWNED = auto()
    UNIT_MOVED = auto()
    UNIT_DEFEATED = auto()
    UNIT_ENTERED_REGION = auto()  # Future enhancement for region-based objectives
    UNIT_EXITED_REGION = auto()   # Future enhancement for region-based objectives


@dataclass(frozen=True)
class GameEvent(ABC):
    """Base class for all game events."""
    turn: int
    event_type: EventType = field(init=False)


@dataclass(frozen=True)
class TurnStarted(GameEvent):
    """Event emitted when a new turn begins."""
    team: Team
    
    def __post_init__(self):
        # Set event_type since dataclass frozen=True prevents normal assignment
        object.__setattr__(self, 'event_type', EventType.TURN_STARTED)


@dataclass(frozen=True)
class TurnEnded(GameEvent):
    """Event emitted when a turn ends."""
    team: Team
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.TURN_ENDED)


@dataclass(frozen=True)
class UnitSpawned(GameEvent):
    """Event emitted when a unit is added to the game."""
    unit_name: str
    team: Team
    position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_SPAWNED)


@dataclass(frozen=True)
class UnitMoved(GameEvent):
    """Event emitted when a unit moves to a new position."""
    unit_name: str
    team: Team
    from_position: tuple[int, int]
    to_position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_MOVED)


@dataclass(frozen=True)
class UnitDefeated(GameEvent):
    """Event emitted when a unit is defeated/removed from the game."""
    unit_name: str
    team: Team
    position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_DEFEATED)


@dataclass(frozen=True)
class UnitEnteredRegion(GameEvent):
    """Event emitted when a unit enters a named region (future enhancement)."""
    unit_name: str
    team: Team
    region_name: str
    position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_ENTERED_REGION)


@dataclass(frozen=True)
class UnitExitedRegion(GameEvent):
    """Event emitted when a unit exits a named region (future enhancement)."""
    unit_name: str
    team: Team  
    region_name: str
    position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_EXITED_REGION)


@dataclass
class ObjectiveContext:
    """Context provided to objectives when handling events.
    
    This context provides:
    1. The event that triggered the objective update
    2. A read-only view of the game state for queries
    3. Optional metadata for future cross-cutting concerns
    """
    event: GameEvent
    view: "GameView"
    meta: Optional[dict] = None  # Reserved for future scenario ID, debug info, etc.