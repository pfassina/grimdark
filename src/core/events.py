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
    UNIT_ENTERED_REGION = auto()  # Future enhancement for region-based objectives
    UNIT_EXITED_REGION = auto()   # Future enhancement for region-based objectives
    UNIT_TOOK_DAMAGE = auto()
    UNIT_ATTACKED = auto()  # Combat attack actions requesting damage via CombatResolver
    UNIT_DAMAGED = auto()   # Non-combat damage from hazards, status effects, etc.
    
    # Movement and Action Events
    MOVEMENT_COMPLETED = auto()  # Emitted when unit finishes moving
    ACTION_SELECTED = auto()     # Emitted when user selects an action
    ACTION_EXECUTED = auto()     # Emitted when action is completed
    
    # Cancel Events
    ACTION_CANCELED = auto()     # Emitted when user cancels current action
    MOVEMENT_CANCELED = auto()   # Emitted when user cancels movement
    
    # Combat Events
    COMBAT_INITIATED = auto()
    ATTACK_TARGETING_SETUP = auto()
    ATTACK_RESOLVED = auto()
    COMBAT_ENDED = auto()
    DAMAGE_APPLIED = auto()
    
    # Player Input Events
    PLAYER_ACTION_REQUESTED = auto()
    PLAYER_INPUT_PROCESSED = auto()
    MENU_NAVIGATION = auto()
    CURSOR_MOVED = auto()
    
    # UI Events
    OVERLAY_OPENED = auto()
    OVERLAY_CLOSED = auto()
    DIALOG_OPENED = auto()
    DIALOG_CLOSED = auto()
    BANNER_SHOWN = auto()
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
    SYSTEM_ERROR = auto()
    LOG_SAVE_REQUESTED = auto()
    OBJECTIVES_CHECK_REQUESTED = auto()


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
    unit_id: str
    team: Team
    from_position: tuple[int, int]
    to_position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_MOVED)


@dataclass(frozen=True)
class UnitDefeated(GameEvent):
    """Event emitted when a unit is defeated/removed from the game."""
    unit_name: str
    unit_id: str  # Added for timeline cleanup and other system references
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


@dataclass(frozen=True)
class UnitTookDamage(GameEvent):
    """Event emitted when a unit takes damage."""
    unit_name: str
    team: Team
    damage_amount: int
    position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_TOOK_DAMAGE)


@dataclass(frozen=True)
class MoraleChanged(GameEvent):
    """Event emitted when a unit's morale changes significantly."""
    unit_name: str
    team: Team
    old_morale: int
    new_morale: int
    position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.MORALE_CHANGED)


@dataclass(frozen=True)
class UnitPanicked(GameEvent):
    """Event emitted when a unit enters panic state."""
    unit_name: str
    team: Team
    position: tuple[int, int]
    trigger_reason: str  # "low_morale", "ally_death", "heavy_damage", etc.
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_PANICKED)


@dataclass(frozen=True)
class UnitRouted(GameEvent):
    """Event emitted when a unit flees the battlefield due to extreme panic."""
    unit_name: str
    team: Team
    position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_ROUTED)


@dataclass(frozen=True)
class UnitRallied(GameEvent):
    """Event emitted when a unit recovers from panic state."""
    unit_name: str
    team: Team
    position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_RALLIED)


@dataclass(frozen=True)
class UnitAttacked(GameEvent):
    """Event emitted when a unit attacks another unit (requesting combat resolution)."""
    attacker_name: str
    attacker_id: str
    attacker_team: Team
    target_name: str
    target_id: str
    target_team: Team
    attack_type: str  # "QuickStrike", "PowerAttack", etc.
    base_damage: int
    damage_multiplier: float = 1.0  # For damage modifiers
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_ATTACKED)


@dataclass(frozen=True)
class UnitDamaged(GameEvent):
    """Event emitted when a unit takes damage from non-combat sources."""
    unit_name: str
    unit_id: str
    team: Team
    position: tuple[int, int]
    damage: int
    damage_type: str  # "fire", "poison", "bleeding", etc.
    source: str  # "Hazard", "StatusEffect", etc.
    
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
    unit_name: str
    unit_id: str
    team: Team
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_TURN_STARTED)


@dataclass(frozen=True)
class UnitTurnEnded(GameEvent):
    """Event emitted when a unit's turn ends."""
    unit_name: str
    unit_id: str
    team: Team
    action_taken: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.UNIT_TURN_ENDED)


@dataclass(frozen=True)
class BattlePhaseChanged(GameEvent):
    """Event emitted when battle phase changes."""
    old_phase: str
    new_phase: str
    unit_id: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.BATTLE_PHASE_CHANGED)


# Combat Events
@dataclass(frozen=True)
class CombatInitiated(GameEvent):
    """Event emitted when combat begins."""
    attacker_name: str
    attacker_id: str
    attacker_team: Team
    combat_type: str  # "ranged", "melee", "aoe", etc.
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.COMBAT_INITIATED)


@dataclass(frozen=True)
class AttackTargetingSetup(GameEvent):
    """Event emitted when attack targeting is set up."""
    attacker_name: str
    attacker_id: str
    attack_range_size: int
    targetable_enemies: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ATTACK_TARGETING_SETUP)


@dataclass(frozen=True)
class AttackResolved(GameEvent):
    """Event emitted when an attack is resolved."""
    attacker_name: str
    target_names: list[str]
    total_damage: int
    defeated_count: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ATTACK_RESOLVED)


@dataclass(frozen=True)
class CombatEnded(GameEvent):
    """Event emitted when combat phase ends."""
    attacker_name: str
    targets_hit: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.COMBAT_ENDED)


@dataclass(frozen=True)
class DamageApplied(GameEvent):
    """Event emitted when damage is applied to a unit."""
    unit_name: str
    unit_id: str
    damage: int
    hp_remaining: int
    source: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.DAMAGE_APPLIED)


# Player Input Events
@dataclass(frozen=True)
class PlayerActionRequested(GameEvent):
    """Event emitted when player action is needed."""
    unit_name: str
    unit_id: str
    available_actions: list[str]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.PLAYER_ACTION_REQUESTED)


@dataclass(frozen=True)
class PlayerInputProcessed(GameEvent):
    """Event emitted when player input is processed."""
    input_type: str
    key_pressed: Optional[str] = None
    action_executed: Optional[str] = None
    result: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.PLAYER_INPUT_PROCESSED)


@dataclass(frozen=True)
class MenuNavigation(GameEvent):
    """Event emitted when menu navigation occurs."""
    menu_type: str
    action: str  # "open", "close", "navigate"
    selection: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.MENU_NAVIGATION)


@dataclass(frozen=True)
class CursorMoved(GameEvent):
    """Event emitted when cursor position changes."""
    from_position: tuple[int, int]
    to_position: tuple[int, int]
    context: str  # "movement", "targeting", "navigation"
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.CURSOR_MOVED)


# UI Events
@dataclass(frozen=True)
class OverlayOpened(GameEvent):
    """Event emitted when an overlay is opened."""
    overlay_type: str
    data: Optional[dict] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.OVERLAY_OPENED)


@dataclass(frozen=True)
class OverlayClosed(GameEvent):
    """Event emitted when an overlay is closed."""
    overlay_type: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.OVERLAY_CLOSED)


@dataclass(frozen=True)
class DialogOpened(GameEvent):
    """Event emitted when a dialog is opened."""
    dialog_type: str
    message: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.DIALOG_OPENED)


@dataclass(frozen=True)
class DialogClosed(GameEvent):
    """Event emitted when a dialog is closed."""
    dialog_type: str
    user_choice: Optional[str] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.DIALOG_CLOSED)


@dataclass(frozen=True)
class BannerShown(GameEvent):
    """Event emitted when a banner is shown."""
    message: str
    banner_type: str  # "info", "warning", "phase", etc.
    duration: Optional[float] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.BANNER_SHOWN)


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
    level: str  # "DEBUG", "INFO", "WARNING", "ERROR"
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
class SystemError(GameEvent):
    """Event emitted when a system error occurs."""
    error_message: str
    source: str
    error_type: str
    context: Optional[dict] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.SYSTEM_ERROR)


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
class MovementCompleted(GameEvent):
    """Event emitted when a unit finishes moving."""
    unit_name: str
    unit_id: str
    from_position: tuple[int, int]
    to_position: tuple[int, int]
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.MOVEMENT_COMPLETED)


@dataclass(frozen=True)
class ActionSelected(GameEvent):
    """Event emitted when user selects an action."""
    unit_name: str
    unit_id: str
    action_name: str
    action_type: str
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ACTION_SELECTED)


@dataclass(frozen=True)
class ActionExecuted(GameEvent):
    """Event emitted when action is completed."""
    unit_name: str
    unit_id: str
    action_name: str
    action_type: str
    success: bool
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ACTION_EXECUTED)


@dataclass(frozen=True)
class ActionCanceled(GameEvent):
    """Event emitted when user cancels current action."""
    unit_name: str
    unit_id: str
    canceled_action: str
    return_to_phase: str  # The phase to return to
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.ACTION_CANCELED)


@dataclass(frozen=True)
class MovementCanceled(GameEvent):
    """Event emitted when user cancels movement."""
    unit_name: str
    unit_id: str
    original_position: tuple[int, int]
    
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