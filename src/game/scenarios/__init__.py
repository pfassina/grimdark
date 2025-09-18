"""Scenario system components.

This package contains scenario loading, menu systems, and objective management:
- scenario_loader.py: YAML scenario parsing and game state initialization
- scenario.py: Scenario data structures and validation
- scenario_structures.py: Data classes for scenario definitions
- scenario_menu.py: Scenario selection interface
- objectives.py: Victory/defeat condition implementations
"""

from .scenario_loader import ScenarioLoader
from .scenario import Scenario
from .scenario_structures import UnitData, ScenarioMarker, ScenarioRegion, ActorPlacement, ScenarioSettings
from .scenario_menu import ScenarioMenu
from .objectives import Objective, DefeatAllEnemiesObjective, ReachPositionObjective, DefeatUnitObjective

__all__ = [
    "ScenarioLoader",
    "Scenario", 
    "UnitData",
    "ScenarioMarker",
    "ScenarioRegion", 
    "ActorPlacement",
    "ScenarioSettings",
    "ScenarioMenu",
    "Objective",
    "DefeatAllEnemiesObjective",
    "ReachPositionObjective", 
    "DefeatUnitObjective",
]