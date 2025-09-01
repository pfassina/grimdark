"""Standardized Info classes for game entities.

This module provides a consistent pattern for storing static information
about game entities (terrain, units, etc.) with common interfaces.
"""

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, Any

from .game_enums import TerrainType, UnitClass, TERRAIN_NAMES, UNIT_CLASS_NAMES


@dataclass
class BaseInfo(ABC):
    """Base class for all game entity info classes."""
    name: str
    symbol: str
    
    @abstractmethod
    def get_display_properties(self) -> Dict[str, Any]:
        """Get properties used for display/rendering."""
        pass
    
    @abstractmethod
    def get_gameplay_properties(self) -> Dict[str, Any]:
        """Get properties used for game mechanics."""
        pass


@dataclass
class UnitStats:
    """Statistics for units."""
    hp_max: int = 20
    strength: int = 5
    defense: int = 3
    speed: int = 5
    movement: int = 4
    attack_range_min: int = 1
    attack_range_max: int = 1


@dataclass
class UnitClassInfo(BaseInfo):
    """Static information about a unit class."""
    base_stats: UnitStats
    
    def get_display_properties(self) -> Dict[str, Any]:
        """Get display properties for this unit class."""
        return {
            "name": self.name,
            "symbol": self.symbol,
        }
    
    def get_gameplay_properties(self) -> Dict[str, Any]:
        """Get gameplay properties for this unit class."""
        return {
            "base_stats": self.base_stats,
        }


@dataclass 
class TerrainInfo(BaseInfo):
    """Static information about terrain types."""
    move_cost: int
    defense_bonus: int
    avoid_bonus: int
    blocks_movement: bool = False
    blocks_vision: bool = False
    
    def get_display_properties(self) -> Dict[str, Any]:
        """Get display properties for this terrain."""
        return {
            "name": self.name,
            "symbol": self.symbol,
        }
    
    def get_gameplay_properties(self) -> Dict[str, Any]:
        """Get gameplay properties for this terrain."""
        return {
            "move_cost": self.move_cost,
            "defense_bonus": self.defense_bonus,
            "avoid_bonus": self.avoid_bonus,
            "blocks_movement": self.blocks_movement,
            "blocks_vision": self.blocks_vision,
        }


# Centralized data for all unit classes
UNIT_CLASS_DATA: Dict[UnitClass, UnitClassInfo] = {
    UnitClass.KNIGHT: UnitClassInfo(
        UNIT_CLASS_NAMES[UnitClass.KNIGHT], "K", 
        UnitStats(25, 7, 5, 3, 3, 1, 1)
    ),
    UnitClass.ARCHER: UnitClassInfo(
        UNIT_CLASS_NAMES[UnitClass.ARCHER], "A", 
        UnitStats(18, 5, 2, 6, 4, 2, 3)
    ),
    UnitClass.MAGE: UnitClassInfo(
        UNIT_CLASS_NAMES[UnitClass.MAGE], "M", 
        UnitStats(15, 2, 1, 4, 3, 1, 2)
    ),
    UnitClass.PRIEST: UnitClassInfo(
        UNIT_CLASS_NAMES[UnitClass.PRIEST], "P", 
        UnitStats(16, 2, 2, 3, 3, 1, 2)
    ),
    UnitClass.THIEF: UnitClassInfo(
        UNIT_CLASS_NAMES[UnitClass.THIEF], "T", 
        UnitStats(16, 4, 1, 8, 5, 1, 1)
    ),
    UnitClass.WARRIOR: UnitClassInfo(
        UNIT_CLASS_NAMES[UnitClass.WARRIOR], "W", 
        UnitStats(22, 6, 3, 5, 4, 1, 1)
    ),
}

# Centralized data for all terrain types
TERRAIN_DATA: Dict[TerrainType, TerrainInfo] = {
    TerrainType.PLAIN: TerrainInfo(
        TERRAIN_NAMES[TerrainType.PLAIN], ".", 1, 0, 0
    ),
    TerrainType.FOREST: TerrainInfo(
        TERRAIN_NAMES[TerrainType.FOREST], "♣", 2, 1, 20
    ),
    TerrainType.MOUNTAIN: TerrainInfo(
        TERRAIN_NAMES[TerrainType.MOUNTAIN], "▲", 3, 2, 30
    ),
    TerrainType.WATER: TerrainInfo(
        TERRAIN_NAMES[TerrainType.WATER], "≈", 99, 0, 0, 
        blocks_movement=True
    ),
    TerrainType.ROAD: TerrainInfo(
        TERRAIN_NAMES[TerrainType.ROAD], "=", 1, 0, 0
    ),
    TerrainType.FORT: TerrainInfo(
        TERRAIN_NAMES[TerrainType.FORT], "■", 1, 3, 10
    ),
    TerrainType.BRIDGE: TerrainInfo(
        TERRAIN_NAMES[TerrainType.BRIDGE], "╬", 1, 0, 0
    ),
    TerrainType.WALL: TerrainInfo(
        TERRAIN_NAMES[TerrainType.WALL], "█", 99, 0, 0, 
        blocks_movement=True, blocks_vision=True
    ),
}