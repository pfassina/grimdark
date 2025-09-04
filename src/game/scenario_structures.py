"""Data structures for scenario definition and loading.

This module contains all the data structures used to define scenarios,
including placement policies, markers, regions, objects, triggers, and
unit data for loading.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .map import GameMap


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
    position: tuple[int, int]
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "ScenarioMarker":
        """Create marker from YAML data."""
        return cls(
            name=name, position=tuple(data["at"]), description=data.get("description")
        )


@dataclass
class ScenarioRegion:
    """Named region for scenario-based placement and triggers."""

    name: str
    rect: tuple[int, int, int, int]  # x, y, width, height
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "ScenarioRegion":
        """Create region from YAML data."""
        rect_data = data["rect"]
        return cls(
            name=name, rect=tuple(rect_data), description=data.get("description")
        )

    def contains_position(self, x: int, y: int) -> bool:
        """Check if position is within this region."""
        rx, ry, rw, rh = self.rect
        return rx <= x < rx + rw and ry <= y < ry + rh

    def get_free_positions(self, game_map: "GameMap") -> list[tuple[int, int]]:
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
    x: int = 0
    y: int = 0
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "ScenarioObject":
        """Create object from YAML data."""
        return cls(
            name=name, object_type=data["type"], properties=data.get("properties", {})
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
            data=data.get("data", {}),
        )


@dataclass
class ActorPlacement:
    """Placement information for units and objects."""

    actor_name: str
    placement_at: Optional[tuple[int, int]] = None
    placement_marker: Optional[str] = None
    placement_region: Optional[str] = None
    placement_policy: PlacementPolicy = PlacementPolicy.RANDOM_FREE_TILE

    @classmethod
    def from_dict(cls, actor_name: str, data: dict[str, Any]) -> "ActorPlacement":
        """Create placement from YAML data."""
        # Validate exactly one placement source
        placement_sources = sum(
            1 for key in ["at", "at_marker", "at_region"] if key in data
        )
        if placement_sources != 1:
            raise ValueError(
                f"Actor '{actor_name}' must have exactly one placement source (at/at_marker/at_region)"
            )

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
            placement_policy=placement_policy,
        )


@dataclass
class UnitData:
    """Unit data for scenario loading and placement.

    This is the INPUT data structure used when loading scenarios from JSON.
    It contains the minimal information needed to create and place a unit
    in the game world.

    Conversion: UnitData -> Unit (via DataConverter.scenario_data_to_unit)
    """

    name: str  # Display name of the unit
    unit_class: str  # Unit class as string (e.g., "KNIGHT")
    team: str  # Team affiliation as string (e.g., "PLAYER")
    x: int  # Map x-coordinate
    y: int  # Map y-coordinate
    stats_override: Optional[dict[str, int]] = None  # Optional stat modifications


@dataclass
class ScenarioSettings:
    """General scenario settings."""

    turn_limit: Optional[int] = None
    starting_team: str = "PLAYER"
    fog_of_war: bool = False