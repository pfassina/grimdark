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
    REACH_POSITION = auto()
    DEFEAT_UNIT = auto()
    PROTECT_UNIT = auto()
    POSITION_CAPTURED = auto()
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


class AttackType(Enum):
    """Fundamental attack types for combat."""
    MELEE = auto()
    RANGED = auto()
    MAGIC = auto()


class PanicTrigger(Enum):
    """Triggers that can cause unit panic."""
    LOW_MORALE = auto()
    ALLY_DEATH = auto()
    HEAVY_DAMAGE = auto()
    OVERWHELMING_ODDS = auto()


class ActionType(Enum):
    """High-level action types for unit actions."""
    WAIT = auto()
    MOVE = auto()
    ATTACK = auto()
    DEFEND = auto()
    ABILITY = auto()  # Special abilities, magic, etc.


class AOEPattern(Enum):
    """Area of effect patterns for attacks and abilities."""
    SINGLE = "single"            # Only center tile
    CROSS = "cross"              # Center + 4 cardinal directions
    SQUARE = "square"            # 3x3 square around center
    DIAMOND = "diamond"          # Diamond shape (Manhattan distance <= 2)
    LINE_HORIZONTAL = "line_horizontal"  # 5-tile horizontal line
    LINE_VERTICAL = "line_vertical"      # 5-tile vertical line


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

ATTACK_TYPE_NAMES = {
    AttackType.MELEE: "Melee",
    AttackType.RANGED: "Ranged",
    AttackType.MAGIC: "Magic"
}

PANIC_TRIGGER_NAMES = {
    PanicTrigger.LOW_MORALE: "Low Morale",
    PanicTrigger.ALLY_DEATH: "Ally Death",
    PanicTrigger.HEAVY_DAMAGE: "Heavy Damage",
    PanicTrigger.OVERWHELMING_ODDS: "Overwhelming Odds"
}

ACTION_TYPE_NAMES = {
    ActionType.WAIT: "Wait",
    ActionType.MOVE: "Move",
    ActionType.ATTACK: "Attack",
    ActionType.DEFEND: "Defend",
    ActionType.ABILITY: "Ability"
}

AOE_PATTERN_NAMES = {
    AOEPattern.SINGLE: "Single Target",
    AOEPattern.CROSS: "Cross Pattern",
    AOEPattern.SQUARE: "Square Area",
    AOEPattern.DIAMOND: "Diamond Area",
    AOEPattern.LINE_HORIZONTAL: "Horizontal Line",
    AOEPattern.LINE_VERTICAL: "Vertical Line"
}