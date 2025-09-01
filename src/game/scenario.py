from dataclasses import dataclass, field
from typing import Optional, Any, TYPE_CHECKING
from abc import ABC, abstractmethod

from ..core.game_enums import ObjectiveType, ObjectiveStatus

if TYPE_CHECKING:
    from .map import GameMap
    from .unit import Unit
    from ..core.game_enums import Team


@dataclass
class Objective(ABC):
    """Base class for all objectives."""
    objective_type: ObjectiveType
    description: str
    status: ObjectiveStatus = ObjectiveStatus.IN_PROGRESS
    
    @abstractmethod
    def check_status(self, game_map: "GameMap", turn: int, **kwargs) -> ObjectiveStatus:
        """Check if the objective is completed, failed, or still in progress."""
        pass


class DefeatAllEnemiesObjective(Objective):
    """Victory condition: defeat all enemy units."""
    
    def __init__(self, description: str = "Defeat all enemies"):
        super().__init__(ObjectiveType.DEFEAT_ALL_ENEMIES, description)
    
    def check_status(self, game_map: "GameMap", turn: int, **kwargs) -> ObjectiveStatus:
        from ..core.game_enums import Team
        enemy_units = game_map.get_units_by_team(Team.ENEMY)
        if not enemy_units:
            return ObjectiveStatus.COMPLETED
        return ObjectiveStatus.IN_PROGRESS


class SurviveTurnsObjective(Objective):
    """Victory condition: survive for a certain number of turns."""
    
    def __init__(self, turns: int, description: Optional[str] = None):
        desc = description or f"Survive for {turns} turns"
        super().__init__(ObjectiveType.SURVIVE_TURNS, desc)
        self.turns_required = turns
    
    def check_status(self, game_map: "GameMap", turn: int, **kwargs) -> ObjectiveStatus:
        if turn >= self.turns_required:
            return ObjectiveStatus.COMPLETED
        return ObjectiveStatus.IN_PROGRESS


class ReachPositionObjective(Objective):
    """Victory condition: move a unit to a specific position."""
    
    def __init__(self, x: int, y: int, unit_name: Optional[str] = None, description: Optional[str] = None):
        desc = description or f"Move {unit_name or 'any unit'} to ({x}, {y})"
        super().__init__(ObjectiveType.REACH_POSITION, desc)
        self.unit_name = unit_name
        self.target_x = x
        self.target_y = y
    
    def check_status(self, game_map: "GameMap", turn: int, **kwargs) -> ObjectiveStatus:
        from ..core.game_enums import Team
        
        # Check if specific unit or any player unit is at the position
        unit_at_pos = game_map.get_unit_at(self.target_x, self.target_y)
        if unit_at_pos and unit_at_pos.team == Team.PLAYER:
            if self.unit_name is None or unit_at_pos.name == self.unit_name:
                return ObjectiveStatus.COMPLETED
        
        # Check if the required unit still exists (for failure condition)
        if self.unit_name:
            found = False
            for unit in game_map.units.values():
                if unit.name == self.unit_name and unit.is_alive:
                    found = True
                    break
            if not found:
                return ObjectiveStatus.FAILED
        
        return ObjectiveStatus.IN_PROGRESS


class DefeatUnitObjective(Objective):
    """Victory condition: defeat a specific unit."""
    
    def __init__(self, unit_name: str, description: Optional[str] = None):
        desc = description or f"Defeat {unit_name}"
        super().__init__(ObjectiveType.DEFEAT_UNIT, desc)
        self.target_unit_name = unit_name
    
    def check_status(self, game_map: "GameMap", turn: int, **kwargs) -> ObjectiveStatus:
        for unit in game_map.units.values():
            if unit.name == self.target_unit_name:
                if not unit.is_alive:
                    return ObjectiveStatus.COMPLETED
                else:
                    return ObjectiveStatus.IN_PROGRESS
        # Unit not found, assume defeated
        return ObjectiveStatus.COMPLETED


class ProtectUnitObjective(Objective):
    """Defeat condition: specific unit must survive."""
    
    def __init__(self, unit_name: str, description: Optional[str] = None):
        desc = description or f"Protect {unit_name}"
        super().__init__(ObjectiveType.PROTECT_UNIT, desc)
        self.protected_unit_name = unit_name
    
    def check_status(self, game_map: "GameMap", turn: int, **kwargs) -> ObjectiveStatus:
        for unit in game_map.units.values():
            if unit.name == self.protected_unit_name:
                if unit.is_alive:
                    return ObjectiveStatus.IN_PROGRESS
                else:
                    return ObjectiveStatus.FAILED
        # Unit not found, assume dead
        return ObjectiveStatus.FAILED


class PositionCapturedObjective(Objective):
    """Defeat condition: enemy reaches specific position."""
    
    def __init__(self, x: int, y: int, description: Optional[str] = None):
        desc = description or f"Prevent enemies from reaching ({x}, {y})"
        super().__init__(ObjectiveType.POSITION_CAPTURED, desc)
        self.position_x = x
        self.position_y = y
    
    def check_status(self, game_map: "GameMap", turn: int, **kwargs) -> ObjectiveStatus:
        from ..core.game_enums import Team
        
        unit_at_pos = game_map.get_unit_at(self.position_x, self.position_y)
        if unit_at_pos and unit_at_pos.team == Team.ENEMY:
            return ObjectiveStatus.FAILED
        return ObjectiveStatus.IN_PROGRESS


class TurnLimitObjective(Objective):
    """Defeat condition: exceed turn limit."""
    
    def __init__(self, turns: int, description: Optional[str] = None):
        desc = description or f"Complete objectives within {turns} turns"
        super().__init__(ObjectiveType.TURN_LIMIT, desc)
        self.max_turns = turns
    
    def check_status(self, game_map: "GameMap", turn: int, **kwargs) -> ObjectiveStatus:
        if turn > self.max_turns:
            return ObjectiveStatus.FAILED
        return ObjectiveStatus.IN_PROGRESS


class AllUnitsDefeatedObjective(Objective):
    """Defeat condition: all player units defeated."""
    
    def __init__(self, description: str = "Keep at least one unit alive"):
        super().__init__(ObjectiveType.ALL_UNITS_DEFEATED, description)
    
    def check_status(self, game_map: "GameMap", turn: int, **kwargs) -> ObjectiveStatus:
        from ..core.game_enums import Team
        player_units = game_map.get_units_by_team(Team.PLAYER)
        if not player_units:
            return ObjectiveStatus.FAILED
        return ObjectiveStatus.IN_PROGRESS


@dataclass
class UnitData:
    """Unit data for scenario loading and placement.
    
    This is the INPUT data structure used when loading scenarios from JSON.
    It contains the minimal information needed to create and place a unit
    in the game world.
    
    Conversion: UnitData -> Unit (via DataConverter.scenario_data_to_unit)
    """
    name: str                                    # Display name of the unit
    unit_class: str                             # Unit class as string (e.g., "KNIGHT")
    team: str                                   # Team affiliation as string (e.g., "PLAYER")
    x: int                                      # Map x-coordinate
    y: int                                      # Map y-coordinate  
    stats_override: Optional[dict[str, int]] = None  # Optional stat modifications


@dataclass
class ScenarioSettings:
    """General scenario settings."""
    turn_limit: Optional[int] = None
    starting_team: str = "PLAYER"
    fog_of_war: bool = False


@dataclass
class Scenario:
    """Container for all scenario data."""
    name: str
    description: str
    author: str = "Unknown"
    
    # Map file reference
    map_file: Optional[str] = None  # Path to external map file
    
    # Units to place
    units: list[UnitData] = field(default_factory=list)
    
    # Objectives
    victory_objectives: list[Objective] = field(default_factory=list)
    defeat_objectives: list[Objective] = field(default_factory=list)
    
    # Settings
    settings: ScenarioSettings = field(default_factory=ScenarioSettings)
    
    def check_victory(self, game_map: "GameMap", turn: int) -> bool:
        """Check if all victory objectives are completed."""
        if not self.victory_objectives:
            return False
        
        for objective in self.victory_objectives:
            if objective.check_status(game_map, turn) != ObjectiveStatus.COMPLETED:
                return False
        return True
    
    def check_defeat(self, game_map: "GameMap", turn: int) -> bool:
        """Check if any defeat objective has failed."""
        for objective in self.defeat_objectives:
            if objective.check_status(game_map, turn) == ObjectiveStatus.FAILED:
                return True
        return False
    
    def get_active_objectives(self, game_map: "GameMap", turn: int) -> list[Objective]:
        """Get all objectives that are still in progress."""
        active = []
        
        for obj in self.victory_objectives:
            if obj.check_status(game_map, turn) == ObjectiveStatus.IN_PROGRESS:
                active.append(obj)
        
        for obj in self.defeat_objectives:
            if obj.check_status(game_map, turn) == ObjectiveStatus.IN_PROGRESS:
                active.append(obj)
        
        return active