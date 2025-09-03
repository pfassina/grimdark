from dataclasses import dataclass, field
from typing import Optional, Any, TYPE_CHECKING, Union, Tuple
from abc import ABC, abstractmethod
from enum import Enum

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


class PlacementPolicy(Enum):
    """Placement policies for region-based placement."""
    RANDOM_FREE_TILE = "random_free_tile"
    SPREAD_EVENLY = "spread_evenly"
    LINE_LEFT_TO_RIGHT = "line_left_to_right"
    LINE_TOP_TO_BOTTOM = "line_top_to_bottom"


@dataclass
class ScenarioMarker:
    """Named position marker for scenario use."""
    name: str
    position: Tuple[int, int]
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "ScenarioMarker":
        """Create marker from YAML data."""
        return cls(
            name=name,
            position=tuple(data["at"]),
            description=data.get("description")
        )


@dataclass
class ScenarioRegion:
    """Named region for scenario-based placement and triggers."""
    name: str
    rect: Tuple[int, int, int, int]  # x, y, width, height
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "ScenarioRegion":
        """Create region from YAML data."""
        rect_data = data["rect"]
        return cls(
            name=name,
            rect=tuple(rect_data),
            description=data.get("description")
        )
    
    def contains_position(self, x: int, y: int) -> bool:
        """Check if position is within this region."""
        rx, ry, rw, rh = self.rect
        return rx <= x < rx + rw and ry <= y < ry + rh
    
    def get_free_positions(self, game_map: "GameMap") -> list[Tuple[int, int]]:
        """Get all free positions within this region."""
        positions = []
        rx, ry, rw, rh = self.rect
        for x in range(rx, rx + rw):
            for y in range(ry, ry + rh):
                if game_map.is_valid_position(x, y) and not game_map.get_unit_at(x, y):
                    tile = game_map.get_tile(x, y)
                    if tile and not tile.blocks_movement:
                        positions.append((x, y))
        return positions


@dataclass
class ScenarioObject:
    """Interactive object placed in the scenario."""
    name: str
    object_type: str  # chest, door, portal, etc.
    properties: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "ScenarioObject":
        """Create object from YAML data."""
        return cls(
            name=name,
            object_type=data["type"],
            properties=data.get("properties", {})
        )


@dataclass
class ScenarioTrigger:
    """Event trigger for scenario."""
    name: str
    trigger_type: str  # enter_region, turn_start, etc.
    condition: Optional[str] = None
    action: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "ScenarioTrigger":
        """Create trigger from YAML data."""
        return cls(
            name=name,
            trigger_type=data["type"],
            condition=data.get("condition"),
            action=data.get("action", ""),
            data=data.get("data", {})
        )


@dataclass
class ActorPlacement:
    """Placement information for units and objects."""
    actor_name: str
    placement_at: Optional[Tuple[int, int]] = None
    placement_marker: Optional[str] = None
    placement_region: Optional[str] = None
    placement_policy: PlacementPolicy = PlacementPolicy.RANDOM_FREE_TILE
    
    @classmethod
    def from_dict(cls, actor_name: str, data: dict[str, Any]) -> "ActorPlacement":
        """Create placement from YAML data."""
        # Validate exactly one placement source
        placement_sources = sum(1 for key in ["at", "at_marker", "at_region"] if key in data)
        if placement_sources != 1:
            raise ValueError(f"Actor '{actor_name}' must have exactly one placement source (at/at_marker/at_region)")
        
        placement_at = None
        placement_marker = None
        placement_region = None
        placement_policy = PlacementPolicy.RANDOM_FREE_TILE
        
        if "at" in data:
            placement_at = tuple(data["at"])
        elif "at_marker" in data:
            placement_marker = data["at_marker"]
        elif "at_region" in data:
            placement_region = data["at_region"]
            if "policy" in data:
                placement_policy = PlacementPolicy(data["policy"])
        
        return cls(
            actor_name=actor_name,
            placement_at=placement_at,
            placement_marker=placement_marker,
            placement_region=placement_region,
            placement_policy=placement_policy
        )


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
    
    # Placement system
    markers: dict[str, ScenarioMarker] = field(default_factory=dict)
    regions: dict[str, ScenarioRegion] = field(default_factory=dict)
    placements: list[ActorPlacement] = field(default_factory=list)
    
    # Units to place (definitions only, no positions)
    units: list[UnitData] = field(default_factory=list)
    
    # Objects and triggers
    objects: list[ScenarioObject] = field(default_factory=list)
    triggers: list[ScenarioTrigger] = field(default_factory=list)
    
    # Objectives
    victory_objectives: list[Objective] = field(default_factory=list)
    defeat_objectives: list[Objective] = field(default_factory=list)
    
    # Settings
    settings: ScenarioSettings = field(default_factory=ScenarioSettings)
    
    # Map overrides for environmental variants
    map_overrides: dict[str, Any] = field(default_factory=dict)
    
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