"""Event-driven system events and context.

This module defines all game events that managers can subscribe to,
following the event-driven architecture with timeline-based timing.

Event Design Principles:
- Events are immutable dataclasses with rich object payloads  
- All events include timeline_time timestamp from timeline system
- Events use rich objects (Unit, Vector2) instead of primitive fields
- Events use proper enums instead of magic strings
- Keep event types focused and avoid over-granular events
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from abc import ABC
from enum import Enum, auto

from ..data import Team, PanicTrigger

if TYPE_CHECKING:
    from ..game_view import GameView
    from ..data.data_structures import Vector2
    from ...game.entities.unit import Unit
    from ..engine.actions import Action
    from ..wounds import WoundType
    from ...game.managers.log_manager import LogLevel
    from ..engine.game_state import BattlePhase


class EventType(Enum):
    """Types of game events that managers can subscribe to."""
    # Turn and Timeline Events
    TURN_STARTED = auto()
    TURN_ENDED = auto()
    TIMELINE_PROCESSED = auto()
    UNIT_TURN_STARTED = auto()
    UNIT_TURN_ENDED = auto()
    BATTLE_PHASE_CHANGED = auto()
    
    # Unit Events  
    UNIT_SPAWNED = auto()
    UNIT_MOVED = auto()
    UNIT_DEFEATED = auto()
    UNIT_ATTACKED = auto()  # Combat attack actions requesting damage via CombatResolver
    UNIT_DAMAGED = auto()   # All damage from combat, hazards, status effects, etc.
    
    # Movement and Action Events
    ACTION_SELECTED = auto()     # Emitted when user selects an action
    ACTION_EXECUTED = auto()     # Emitted when action is completed
    
    # Cancel Events
    ACTION_CANCELED = auto()     # Emitted when user cancels current action
    MOVEMENT_CANCELED = auto()   # Emitted when user cancels movement
    
    # Combat Events
    ATTACK_TARGETING_SETUP = auto()
    ATTACK_RESOLVED = auto()
    FRIENDLY_FIRE_DETECTED = auto()    # Friendly fire detected during action validation
    
    # Player Input Events
    PLAYER_ACTION_REQUESTED = auto()
    CURSOR_MOVED = auto()
    
    # UI Events
    UI_STATE_CHANGED = auto()
    
    # Logging Events
    LOG_MESSAGE = auto()
    DEBUG_MESSAGE = auto()
    
    # Game State Events
    GAME_PHASE_CHANGED = auto()
    SCENARIO_LOADED = auto()
    GAME_STARTED = auto()
    GAME_ENDED = auto()
    
    # Morale Events
    MORALE_CHANGED = auto()
    UNIT_PANICKED = auto()
    UNIT_ROUTED = auto()
    UNIT_RALLIED = auto()
    
    # System Events
    MANAGER_INITIALIZED = auto()
    LOG_SAVE_REQUESTED = auto()
    OBJECTIVES_CHECK_REQUESTED = auto()


@dataclass(frozen=True)
class GameEvent(ABC):
    """Base class for all game events."""
    timeline_time: int
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
    unit: "Unit"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_SPAWNED)


@dataclass(frozen=True)
class UnitMoved(GameEvent):
    """Event emitted when a unit moves to a new position."""
    unit: "Unit"  # unit.position contains destination after movement
    from_position: "Vector2"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_MOVED)


@dataclass(frozen=True)
class UnitDefeated(GameEvent):
    """Event emitted when a unit is defeated/removed from the game."""
    unit: "Unit"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_DEFEATED)




@dataclass(frozen=True)
class MoraleChanged(GameEvent):
    """Event emitted when a unit's morale changes significantly."""
    unit: "Unit"
    old_morale: int
    new_morale: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.MORALE_CHANGED)


@dataclass(frozen=True)
class UnitPanicked(GameEvent):
    """Event emitted when a unit enters panic state."""
    unit: "Unit"
    trigger: PanicTrigger
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_PANICKED)


@dataclass(frozen=True)
class UnitRouted(GameEvent):
    """Event emitted when a unit flees the battlefield due to extreme panic."""
    unit: "Unit"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_ROUTED)


@dataclass(frozen=True)
class UnitRallied(GameEvent):
    """Event emitted when a unit recovers from panic state."""
    unit: "Unit"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_RALLIED)


@dataclass(frozen=True)
class UnitAttacked(GameEvent):
    """Event emitted when a unit attacks another unit (requesting combat resolution)."""
    attacker: "Unit"
    target: "Unit"
    base_damage: int
    damage_multiplier: float = 1.0  # For damage modifiers
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_ATTACKED)


@dataclass(frozen=True)
class UnitDamaged(GameEvent):
    """Event emitted when a unit takes damage from all sources."""
    unit: "Unit"
    damage: int
    damage_type: "WoundType"
    source: str  # "Combat", "Hazard", "StatusEffect", etc.
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_DAMAGED)


# Timeline and Battle Phase Events
@dataclass(frozen=True)
class TimelineProcessed(GameEvent):
    """Event emitted when timeline processes an entry."""
    entries_processed: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.TIMELINE_PROCESSED)


@dataclass(frozen=True) 
class UnitTurnStarted(GameEvent):
    """Event emitted when a unit's turn starts."""
    unit: "Unit"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_TURN_STARTED)


@dataclass(frozen=True)
class UnitTurnEnded(GameEvent):
    """Event emitted when a unit's turn ends."""
    unit: "Unit"
    action_taken: Optional["Action"] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_TURN_ENDED)


@dataclass(frozen=True)
class BattlePhaseChanged(GameEvent):
    """Event emitted when battle phase changes."""
    old_phase: "BattlePhase"
    new_phase: "BattlePhase"
    unit: Optional["Unit"] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.BATTLE_PHASE_CHANGED)


# Combat Events


@dataclass(frozen=True)
class AttackTargetingSetup(GameEvent):
    """Event emitted when attack targeting is set up."""
    attacker: "Unit"
    attack_range_size: int
    targetable_enemies: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ATTACK_TARGETING_SETUP)


@dataclass(frozen=True)
class AttackResolved(GameEvent):
    """Event emitted when an attack is resolved."""
    attacker: "Unit"
    targets: list["Unit"]
    total_damage: int
    defeated_count: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ATTACK_RESOLVED)


@dataclass(frozen=True)
class FriendlyFireDetected(GameEvent):
    """Event emitted when friendly fire is detected during action validation."""
    attacker: "Unit"
    friendly_units: list["Unit"]
    target_position: "Vector2"
    action_name: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.FRIENDLY_FIRE_DETECTED)




# Player Input Events
@dataclass(frozen=True)
class PlayerActionRequested(GameEvent):
    """Event emitted when player action is needed."""
    unit: "Unit"
    available_actions: list[str]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.PLAYER_ACTION_REQUESTED)




@dataclass(frozen=True)
class CursorMoved(GameEvent):
    """Event emitted when cursor position changes."""
    from_position: "Vector2"
    to_position: "Vector2"
    context: str  # "movement", "targeting", "navigation"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.CURSOR_MOVED)


# UI Events


@dataclass(frozen=True)
class UIStateChanged(GameEvent):
    """Event emitted when UI state changes."""
    state_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UI_STATE_CHANGED)


# Logging Events
@dataclass(frozen=True)
class LogMessage(GameEvent):
    """Event emitted when a log message is created."""
    message: str
    category: str
    level: "LogLevel"
    source: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.LOG_MESSAGE)


@dataclass(frozen=True)
class DebugMessage(GameEvent):
    """Event emitted for debug-specific messages."""
    message: str
    source: str
    context: Optional[dict] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.DEBUG_MESSAGE)


# Game State Events
@dataclass(frozen=True)
class GamePhaseChanged(GameEvent):
    """Event emitted when main game phase changes."""
    old_phase: str
    new_phase: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.GAME_PHASE_CHANGED)


@dataclass(frozen=True)
class ScenarioLoaded(GameEvent):
    """Event emitted when a scenario is loaded."""
    scenario_name: str
    scenario_path: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.SCENARIO_LOADED)


@dataclass(frozen=True)
class GameStarted(GameEvent):
    """Event emitted when game starts."""
    scenario_name: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.GAME_STARTED)


@dataclass(frozen=True)
class GameEnded(GameEvent):
    """Event emitted when game ends."""
    result: str  # "victory", "defeat", "quit"
    reason: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.GAME_ENDED)


# System Events
@dataclass(frozen=True)
class ManagerInitialized(GameEvent):
    """Event emitted when a manager is initialized."""
    manager_name: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.MANAGER_INITIALIZED)




@dataclass(frozen=True)
class LogSaveRequested(GameEvent):
    """Event emitted when user requests to save the log to file."""
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.LOG_SAVE_REQUESTED)


@dataclass(frozen=True)
class ObjectivesCheckRequested(GameEvent):
    """Event emitted when objectives should be checked (after unit actions)."""
    trigger_reason: str  # "unit_action_completed", "unit_defeated", etc.
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.OBJECTIVES_CHECK_REQUESTED)


# Movement and Action Events


@dataclass(frozen=True)
class ActionSelected(GameEvent):
    """Event emitted when user selects an action."""
    unit: "Unit"
    action: "Action"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ACTION_SELECTED)


@dataclass(frozen=True)
class ActionExecuted(GameEvent):
    """Event emitted when action is completed."""
    unit: "Unit"
    action: "Action"
    success: bool
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ACTION_EXECUTED)


@dataclass(frozen=True)
class ActionCanceled(GameEvent):
    """Event emitted when user cancels current action."""
    unit: "Unit"
    canceled_action: Optional["Action"]  # None if action not yet determined
    return_to_phase: str  # The phase to return to
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ACTION_CANCELED)


@dataclass(frozen=True)
class MovementCanceled(GameEvent):
    """Event emitted when user cancels movement."""
    unit: "Unit"
    original_position: "Vector2"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.MOVEMENT_CANCELED)


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