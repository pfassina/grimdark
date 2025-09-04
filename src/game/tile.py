from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ..core.game_enums import TerrainType
from ..core.game_info import TERRAIN_DATA
from ..core.data_structures import Vector2

if TYPE_CHECKING:
    from .unit import Unit


@dataclass
class Tile:
    position: Vector2
    terrain_type: TerrainType
    elevation: int = 0
    
    def __post_init__(self):
        self._info = TERRAIN_DATA[self.terrain_type]
    
    @property
    def name(self) -> str:
        return self._info.name
    
    @property
    def symbol(self) -> str:
        return self._info.symbol
    
    @property
    def move_cost(self) -> int:
        return self._info.move_cost
    
    @property
    def defense_bonus(self) -> int:
        return self._info.defense_bonus + self.elevation
    
    @property
    def avoid_bonus(self) -> int:
        return self._info.avoid_bonus
    
    @property
    def blocks_movement(self) -> bool:
        return self._info.blocks_movement
    
    @property
    def blocks_vision(self) -> bool:
        return self._info.blocks_vision
    
    def can_enter(self, unit: Optional["Unit"] = None) -> bool:
        """Check if a unit can enter this tile.
        
        Args:
            unit: The unit trying to enter (optional, for future unit-specific movement rules)
            
        TODO: Implement unit-specific movement rules:
        - Flying units could cross water/mountains
        - Cavalry might have restrictions in forests
        - Ships could only move on water
        For now, the unit parameter is kept for API consistency and future expansion.
        """
        if self.blocks_movement:
            return False
        return True