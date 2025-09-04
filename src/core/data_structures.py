"""Unified data structures and conversion utilities.

This module provides clear definitions and conversion utilities for the different
data representations used throughout the game architecture.

Data Flow:
1. UnitData (scenarios) -> Unit (game logic) -> UnitRenderData (display)
2. Input -> Processing -> Output

Each structure serves a specific architectural layer and should not be merged.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
from abc import ABC
import math

from .game_enums import Team, UnitClass

if TYPE_CHECKING:
    from ..game.unit import Unit
    from ..game.scenario_structures import UnitData
    from .renderable import UnitRenderData


@dataclass
class Vector2:
    """2D vector for coordinates and positions.
    
    Uses (y, x) ordering for direct alignment with 2D array access patterns.
    First parameter is row (y-coordinate), second is column (x-coordinate).
    This creates perfect alignment with array[y][x] access patterns.
    
    Provides mathematical operations and conversion utilities for consistent
    position handling throughout the game architecture.
    """
    y: int
    x: int
    
    def __add__(self, other: "Vector2") -> "Vector2":
        """Vector addition."""
        return Vector2(self.y + other.y, self.x + other.x)
    
    def __sub__(self, other: "Vector2") -> "Vector2":
        """Vector subtraction."""
        return Vector2(self.y - other.y, self.x - other.x)
    
    def __mul__(self, scalar: int) -> "Vector2":
        """Scalar multiplication."""
        return Vector2(self.y * scalar, self.x * scalar)
    
    def __floordiv__(self, scalar: int) -> "Vector2":
        """Integer division."""
        return Vector2(self.y // scalar, self.x // scalar)
    
    def __eq__(self, other: object) -> bool:
        """Vector equality comparison."""
        if not isinstance(other, Vector2):
            return False
        return self.y == other.y and self.x == other.x
    
    def __hash__(self) -> int:
        """Hash for use in sets and dictionaries."""
        return hash((self.y, self.x))
    
    def __iter__(self):
        """Make Vector2 iterable for unpacking (y, x order)."""
        yield self.y
        yield self.x
    
    def __getitem__(self, key: int) -> int:
        """Enable indexed access like Vector2[0] for y, Vector2[1] for x."""
        if key == 0:
            return self.y
        elif key == 1:
            return self.x
        else:
            raise IndexError("Vector2 index out of range (must be 0 or 1)")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Vector2({self.y}, {self.x})"
    
    def distance_to(self, other: "Vector2") -> float:
        """Calculate Euclidean distance to another vector."""
        dy = self.y - other.y
        dx = self.x - other.x
        return math.sqrt(dx * dx + dy * dy)
    
    def manhattan_distance_to(self, other: "Vector2") -> int:
        """Calculate Manhattan distance to another vector."""
        return abs(self.y - other.y) + abs(self.x - other.x)
    
    def magnitude(self) -> float:
        """Calculate vector magnitude (distance from origin)."""
        return math.sqrt(self.y * self.y + self.x * self.x)
    
    def normalize(self) -> "Vector2":
        """Return normalized vector (magnitude 1). Returns (0,0) for zero vector."""
        mag = self.magnitude()
        if mag == 0:
            return Vector2(0, 0)
        return Vector2(int(self.y / mag), int(self.x / mag))
    
    @classmethod
    def from_tuple(cls, coords: tuple[int, int]) -> "Vector2":
        """Create Vector2 from coordinate tuple (y, x order)."""
        return cls(coords[0], coords[1])
    
    @classmethod
    def from_list(cls, coords: list[int]) -> "Vector2":
        """Create Vector2 from coordinate list (y, x order)."""
        if len(coords) < 2:
            raise ValueError("List must contain at least 2 elements")
        return cls(coords[0], coords[1])
    
    def to_tuple(self) -> tuple[int, int]:
        """Convert to coordinate tuple (y, x order)."""
        return (self.y, self.x)
    
    def to_list(self) -> list[int]:
        """Convert to coordinate list (y, x order)."""
        return [self.y, self.x]


@dataclass
class BaseUnitData(ABC):
    """Base class defining common unit data fields."""
    name: str
    position: Vector2
    

class DataConverter:
    """Utilities for converting between different data representations."""
    
    @staticmethod
    def unit_to_render_data(unit: "Unit", highlight_type: Optional[str] = None) -> "UnitRenderData":
        """Convert a game Unit to UnitRenderData for rendering.
        
        Args:
            unit: The game logic Unit instance
            highlight_type: Optional highlighting type (e.g., "target")
            
        Returns:
            UnitRenderData ready for display
        """
        from ..core.renderable import UnitRenderData
        
        return UnitRenderData(
            position=unit.position,
            unit_type=unit.actor.get_class_name(),
            team=unit.team.value,
            hp_current=unit.hp_current,
            hp_max=unit.health.hp_max,
            facing=unit.facing,
            is_active=unit.can_move or unit.can_act,
            highlight_type=highlight_type,
            # Enhanced stats for strategic TUI
            level=1,  # Placeholder - would come from experience system
            exp=0,    # Placeholder - would come from experience system  
            attack=unit.combat.strength,
            defense=unit.combat.defense,
            speed=unit.status.speed,
            status_effects=[]  # Placeholder - would come from status effect system
        )
    
    @staticmethod
    def scenario_data_to_unit(unit_data: "UnitData") -> "Unit":
        """Convert scenario UnitData to a game Unit instance.
        
        Args:
            unit_data: UnitData from scenario loading
            
        Returns:
            Fully initialized Unit instance
        """
        from ..game.unit import Unit
        
        # Parse unit class and team from strings
        unit_class = UnitClass[unit_data.unit_class.upper()]
        team = Team[unit_data.team.upper()]
        
        # Create unit
        unit = Unit(
            name=unit_data.name,
            unit_class=unit_class,
            team=team,
            position=unit_data.position
        )
        
        # Apply stat overrides if any
        if unit_data.stats_override:
            for stat_name, value in unit_data.stats_override.items():
                # Handle special case for hp_current
                if stat_name == "hp_current":
                    unit.hp_current = value
                # Handle component-specific stat overrides
                else:
                    # Get the appropriate component and modify the value
                    if stat_name in ["hp_max"]:
                        unit.health.hp_max = value
                    elif stat_name in ["strength", "defense", "attack_range_min", "attack_range_max", "aoe_pattern"]:
                        setattr(unit.combat, stat_name, value)
                    elif stat_name in ["movement"]:
                        unit.movement.movement_points = value
                    elif stat_name in ["speed"]:
                        unit.status.speed = value
        
        return unit
    
    @staticmethod
    def units_to_render_data_list(units: dict[str, "Unit"], highlight_func=None) -> list["UnitRenderData"]:
        """Convert a collection of Units to a list of UnitRenderData.
        
        Args:
            units: Dictionary of unit_id -> Unit instances
            highlight_func: Optional function that takes a unit and returns highlight_type
            
        Returns:
            List of UnitRenderData for all alive units
        """
        render_data = []
        for unit in units.values():
            if unit.is_alive:
                highlight_type = highlight_func(unit) if highlight_func else None
                render_data.append(DataConverter.unit_to_render_data(unit, highlight_type))
        return render_data


class ValidationMixin:
    """Mixin providing validation utilities for data structures."""
    
    def validate_position(self, max_width: int, max_height: int) -> bool:
        """Validate that position is within map bounds."""
        if not hasattr(self, 'position'):
            return False
        position = getattr(self, 'position', None)
        if position is None or not isinstance(position, Vector2):
            return False
        return 0 <= position.x < max_width and 0 <= position.y < max_height
    
    def validate_required_fields(self, required_fields: list[str]) -> bool:
        """Validate that all required fields are present and non-None."""
        for field in required_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                return False
        return True


# Type aliases for cleaner code
UnitCollection = dict[str, "Unit"]
RenderDataCollection = list["UnitRenderData"]
ScenarioDataCollection = list["UnitData"]