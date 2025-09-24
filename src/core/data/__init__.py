"""Core data structures and definitions.

This package contains fundamental data types and game definitions:
- data_structures.py: Vector2 and VectorArray for efficient spatial operations
- game_enums.py: Centralized enums for teams, unit classes, terrain types
- game_info.py: Static game data and lookup tables
"""

from .data_structures import Vector2, VectorArray, BaseUnitData, DataConverter, ValidationMixin
from .game_enums import Team, UnitClass, TerrainType, ObjectiveType, ObjectiveStatus, LayerType, PanicTrigger, AOEPattern, ComponentType, UNIT_CLASS_NAMES, TERRAIN_NAMES, AOE_PATTERN_NAMES, COMPONENT_TYPE_NAMES
from .game_info import BaseInfo, UnitClassInfo, TerrainInfo, UNIT_CLASS_DATA, TERRAIN_DATA

__all__ = [
    "Vector2",
    "VectorArray", 
    "BaseUnitData",
    "DataConverter",
    "ValidationMixin",
    "Team",
    "UnitClass", 
    "TerrainType",
    "ObjectiveType",
    "ObjectiveStatus",
    "LayerType", 
    "PanicTrigger",
    "AOEPattern",
    "ComponentType",
    "UNIT_CLASS_NAMES",
    "TERRAIN_NAMES",
    "AOE_PATTERN_NAMES",
    "COMPONENT_TYPE_NAMES",
    "BaseInfo",
    "UnitClassInfo",
    "UNIT_CLASS_DATA",
    "TerrainInfo",
    "TERRAIN_DATA",
]