"""Event system for publisher-subscriber communication.

This package contains the complete event-driven architecture:
- event_manager.py: Publisher-subscriber event routing and coordination  
- events.py: Event definitions for inter-system communication
"""

from .event_manager import EventManager, QueuedEvent
from .events import (
    GameEvent,
    EventType,
    TurnStarted,
    TurnEnded,
    UnitSpawned,
    UnitMoved,
    UnitDefeated,
    UnitAttacked,
    UnitTookDamage,
    AttackTargetingSetup,
    AttackResolved,
    ActionExecuted,
    LogMessage,
    DebugMessage,
    LogSaveRequested,
    ManagerInitialized,
    GamePhaseChanged,
    ScenarioLoaded,
    BattlePhaseChanged,
    CombatInitiated,
    UIStateChanged,
)

__all__ = [
    "EventManager",
    "QueuedEvent", 
    "GameEvent",
    "EventType",
    "TurnStarted",
    "TurnEnded",
    "UnitSpawned",
    "UnitMoved",
    "UnitDefeated",
    "UnitAttacked",
    "UnitTookDamage",
    "AttackTargetingSetup",
    "AttackResolved",
    "ActionExecuted",
    "LogMessage",
    "DebugMessage",
    "LogSaveRequested",
    "ManagerInitialized",
    "GamePhaseChanged",
    "ScenarioLoaded",
    "BattlePhaseChanged",
    "CombatInitiated",
    "UIStateChanged",
]