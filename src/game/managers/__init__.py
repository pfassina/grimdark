"""Manager systems for game logic coordination.

This package contains all manager classes that coordinate different aspects
of game functionality through the event-driven architecture.
"""

from .combat_manager import CombatManager
from .escalation_manager import EscalationManager
from .hazard_manager import HazardManager
from .log_manager import LogManager, LogLevel
from .morale_manager import MoraleManager
from .objective_manager import ObjectiveManager
from .phase_manager import PhaseManager
from .scenario_manager import ScenarioManager
from .selection_manager import SelectionManager
from .timeline_manager import TimelineManager
from .ui_manager import UIManager

__all__ = [
    "CombatManager",
    "EscalationManager", 
    "HazardManager",
    "LogManager",
    "LogLevel",
    "MoraleManager",
    "ObjectiveManager",
    "PhaseManager",
    "ScenarioManager",
    "SelectionManager",
    "TimelineManager",
    "UIManager",
]