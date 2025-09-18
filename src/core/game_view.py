"""Read-only game view adapter for objectives.

This module provides a stable, minimal interface for objectives to query
game state without coupling to internal GameMap implementation details.

Design Principles:
- Read-only interface prevents objectives from mutating game state
- Minimal query surface reduces coupling 
- Stable contract allows GameMap implementation to evolve
- Performance-conscious with targeted queries instead of full scans
"""

from typing import Optional, Iterable, TYPE_CHECKING
from dataclasses import dataclass

from .data.game_enums import Team
from .data.data_structures import Vector2

if TYPE_CHECKING:
    from ..game.map import GameMap
    from ..game.entities.unit import Unit


@dataclass
class UnitView:
    """Read-only view of a unit for objectives.
    
    Contains only the essential information objectives need
    without exposing full Unit implementation details.
    """
    name: str
    team: Team
    position: Vector2
    is_alive: bool
    can_move: bool
    can_act: bool
    hp_current: int
    hp_max: int


class GameView:
    """Read-only facade over game state for objective queries.
    
    This adapter provides only the minimal queries objectives need,
    keeping them decoupled from the full GameMap implementation.
    """
    
    def __init__(self, game_map: "GameMap"):
        """Initialize with a GameMap reference.
        
        Args:
            game_map: The GameMap instance to provide read-only access to
        """
        self._game_map = game_map
    
    def get_unit_at(self, position: Vector2) -> Optional[UnitView]:
        """Get unit at specific position.
        
        Args:
            position: Position to check
            
        Returns:
            UnitView if unit exists at position, None otherwise
        """
        unit = self._game_map.get_unit_at(position)
        return self._unit_to_view(unit) if unit else None
    
    def get_unit_by_name(self, name: str) -> Optional[UnitView]:
        """Get unit by name.
        
        Args:
            name: Name of the unit to find
            
        Returns:
            UnitView if unit exists and is alive, None otherwise
        """
        for unit in self._game_map.units:
            if unit.name == name and unit.is_alive:
                return self._unit_to_view(unit)
        return None
    
    def count_units(self, team: Team, alive: bool = True) -> int:
        """Count units belonging to a team.
        
        Args:
            team: Team to count units for
            alive: If True, only count living units
            
        Returns:
            Number of units matching criteria
        """
        if alive:
            # Use vectorized O(1) count for alive units (most common case)
            return self._game_map.count_units_by_team(team)
        else:
            # For dead units, we need to iterate (rare case)
            count = 0
            for unit in self._game_map.units:
                if unit.team == team and not unit.is_alive:
                    count += 1
            return count
    
    def iter_units(self, team: Optional[Team] = None, alive: bool = True) -> Iterable[UnitView]:
        """Iterate over units matching criteria.
        
        Args:
            team: If specified, only include units from this team
            alive: If True, only include living units
            
        Yields:
            UnitView for each unit matching criteria
        """
        for unit in self._game_map.units:
            if unit is None:
                continue
            if team is not None and unit.team != team:
                continue
            if alive and not unit.is_alive:
                continue
            yield self._unit_to_view(unit)
    
    def get_map_dimensions(self) -> tuple[int, int]:
        """Get map width and height.
        
        Returns:
            Tuple of (width, height)
        """
        return (self._game_map.width, self._game_map.height)
    
    def is_valid_position(self, position: Vector2) -> bool:
        """Check if position is within map bounds.
        
        Args:
            position: Position to check
            
        Returns:
            True if position is valid
        """
        return self._game_map.is_valid_position(position)
    
    def _unit_to_view(self, unit: "Unit") -> UnitView:
        """Convert Unit to UnitView.
        
        Args:
            unit: Unit instance to convert
            
        Returns:
            UnitView with essential unit information
        """
        return UnitView(
            name=unit.name,
            team=unit.team,
            position=unit.position,
            is_alive=unit.is_alive,
            can_move=unit.can_move,
            can_act=unit.can_act,
            hp_current=unit.hp_current,
            hp_max=unit.health.hp_max
        )
