"""Centralized game enums and constants.

This module contains all core game enums that are used across multiple modules,
eliminating duplication and providing a single source of truth.
"""

from enum import Enum, auto


class Team(Enum):
    """Team affiliations for units."""
    PLAYER = 0
    ENEMY = 1
    ALLY = 2
    NEUTRAL = 3


class UnitClass(Enum):
    """Unit classes with distinct roles and capabilities."""
    KNIGHT = auto()
    ARCHER = auto()
    MAGE = auto()
    PRIEST = auto()
    THIEF = auto()
    WARRIOR = auto()


class TerrainType(Enum):
    """Types of terrain with different properties."""
    PLAIN = auto()
    FOREST = auto()
    MOUNTAIN = auto()
    WATER = auto()
    ROAD = auto()
    FORT = auto()
    BRIDGE = auto()
    WALL = auto()


class ObjectiveType(Enum):
    """Types of objectives for scenarios."""
    DEFEAT_ALL_ENEMIES = auto()
    SURVIVE_TURNS = auto()
    REACH_POSITION = auto()
    DEFEAT_UNIT = auto()
    PROTECT_UNIT = auto()
    POSITION_CAPTURED = auto()
    TURN_LIMIT = auto()
    ALL_UNITS_DEFEATED = auto()


class ObjectiveStatus(Enum):
    """Status of objectives during gameplay."""
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


class LayerType(Enum):
    """Render layers for organizing visual elements."""
    TERRAIN = 0
    OBJECTS = 1
    UNITS = 2
    EFFECTS = 3
    UI = 4
    OVERLAY = 5


# Convenience mappings for backward compatibility and easy access
TEAM_NAMES = {
    Team.PLAYER: "Player",
    Team.ENEMY: "Enemy", 
    Team.ALLY: "Ally",
    Team.NEUTRAL: "Neutral"
}

UNIT_CLASS_NAMES = {
    UnitClass.KNIGHT: "Knight",
    UnitClass.ARCHER: "Archer",
    UnitClass.MAGE: "Mage",
    UnitClass.PRIEST: "Priest",
    UnitClass.THIEF: "Thief",
    UnitClass.WARRIOR: "Warrior"
}

TERRAIN_NAMES = {
    TerrainType.PLAIN: "Plain",
    TerrainType.FOREST: "Forest",
    TerrainType.MOUNTAIN: "Mountain", 
    TerrainType.WATER: "Water",
    TerrainType.ROAD: "Road",
    TerrainType.FORT: "Fort",
    TerrainType.BRIDGE: "Bridge",
    TerrainType.WALL: "Wall"
}