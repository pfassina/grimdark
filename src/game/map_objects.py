"""Map objects system for spawn points, regions, and triggers.

This module provides data structures and loaders for map-specific objects
that define unit placement, special areas, and interactive elements.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum
import yaml
import os

from ..core.game_enums import Team


class TriggerType(Enum):
    """Types of triggers that can be placed on maps."""
    ENTER_REGION = "enter_region"
    EXIT_MAP = "exit_map"
    INTERACT = "interact"
    TURN_START = "turn_start"
    UNIT_DEFEATED = "unit_defeated"


@dataclass
class SpawnPoint:
    """Defines a spawn location for a unit on the map."""
    name: str
    team: Team
    position: tuple[int, int]
    unit_class: Optional[str] = None  # Optional unit class override
    facing: Optional[str] = None  # Optional facing direction
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpawnPoint":
        """Create a SpawnPoint from dictionary data."""
        return cls(
            name=data["name"],
            team=Team[data["team"]],
            position=tuple(data["pos"]),
            unit_class=data.get("class"),
            facing=data.get("facing")
        )


@dataclass
class Region:
    """Defines a special area on the map with gameplay effects."""
    name: str
    rect: tuple[int, int, int, int]  # x, y, width, height
    defense_bonus: int = 0
    avoid_bonus: int = 0
    heal_per_turn: int = 0
    damage_per_turn: int = 0
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Region":
        """Create a Region from dictionary data."""
        rect_data = data["rect"]
        return cls(
            name=data["name"],
            rect=(rect_data[0], rect_data[1], rect_data[2], rect_data[3]),
            defense_bonus=data.get("defense_bonus", 0),
            avoid_bonus=data.get("avoid_bonus", 0),
            heal_per_turn=data.get("heal_per_turn", 0),
            damage_per_turn=data.get("damage_per_turn", 0),
            description=data.get("description")
        )
    
    def contains_position(self, x: int, y: int) -> bool:
        """Check if a position is within this region."""
        rx, ry, rw, rh = self.rect
        return rx <= x < rx + rw and ry <= y < ry + rh


@dataclass 
class Trigger:
    """Defines an interactive trigger on the map."""
    name: str
    trigger_type: TriggerType
    position: Optional[tuple[int, int]] = None
    region_name: Optional[str] = None
    condition: Optional[str] = None
    action: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trigger":
        """Create a Trigger from dictionary data."""
        pos_data = data.get("pos")
        return cls(
            name=data["name"],
            trigger_type=TriggerType(data["type"]),
            position=tuple(pos_data) if pos_data else None,
            region_name=data.get("region"),
            condition=data.get("condition"),
            action=data.get("action"),
            data=data.get("data", {})
        )


@dataclass
class MapObjects:
    """Container for all objects associated with a map."""
    spawn_points: list[SpawnPoint] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    triggers: list[Trigger] = field(default_factory=list)
    
    def get_spawn_point(self, name: str) -> Optional[SpawnPoint]:
        """Get a spawn point by name."""
        for sp in self.spawn_points:
            if sp.name == name:
                return sp
        return None
    
    def get_spawn_points_for_team(self, team: Team) -> list[SpawnPoint]:
        """Get all spawn points for a specific team."""
        return [sp for sp in self.spawn_points if sp.team == team]
    
    def get_region_at(self, x: int, y: int) -> Optional[Region]:
        """Get the region at a specific position (returns first match)."""
        for region in self.regions:
            if region.contains_position(x, y):
                return region
        return None
    
    def get_regions_at(self, x: int, y: int) -> list[Region]:
        """Get all regions at a specific position."""
        return [r for r in self.regions if r.contains_position(x, y)]


def load_map_objects(map_directory: str) -> MapObjects:
    """Load map objects from objects.yaml file in the map directory.
    
    Args:
        map_directory: Path to the map directory
        
    Returns:
        MapObjects instance with loaded data, or empty MapObjects if file not found
    """
    objects_path = os.path.join(map_directory, "objects.yaml")
    
    if not os.path.exists(objects_path):
        # Return empty objects if file doesn't exist
        return MapObjects()
    
    try:
        with open(objects_path, 'r') as f:
            data = yaml.safe_load(f)
            
        if not data:
            return MapObjects()
        
        objects = MapObjects()
        
        # Load spawn points
        if "spawns" in data:
            for spawn_data in data["spawns"]:
                objects.spawn_points.append(SpawnPoint.from_dict(spawn_data))
        
        # Load regions
        if "regions" in data:
            for region_data in data["regions"]:
                objects.regions.append(Region.from_dict(region_data))
        
        # Load triggers
        if "triggers" in data:
            for trigger_data in data["triggers"]:
                objects.triggers.append(Trigger.from_dict(trigger_data))
        
        return objects
        
    except Exception as e:
        print(f"Warning: Failed to load objects.yaml from {map_directory}: {e}")
        return MapObjects()
