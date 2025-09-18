"""Unified data structures and conversion utilities.

This module provides clear definitions and conversion utilities for the different
data representations used throughout the game architecture.

Data Flow:
1. UnitData (scenarios) -> Unit (game logic) -> UnitRenderData (display)
2. Input -> Processing -> Output

Each structure serves a specific architectural layer and should not be merged.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Union
from abc import ABC
import math
import numpy as np
from numpy.typing import NDArray

from .game_enums import Team, UnitClass

if TYPE_CHECKING:
    from ...game.entities.unit import Unit
    from ...game.scenarios.scenario_structures import UnitData
    from ..entities.renderable import UnitRenderData


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
    
    def to_numpy(self) -> NDArray[np.int16]:
        """Convert to numpy array (y, x order). Uses int16 for memory efficiency."""
        return np.array([self.y, self.x], dtype=np.int16)
    
    @classmethod
    def from_numpy(cls, arr: NDArray[np.int16]) -> "Vector2":
        """Create Vector2 from numpy array (y, x order)."""
        if arr.shape != (2,):
            raise ValueError("Array must have shape (2,) for Vector2 conversion")
        return cls(int(arr[0]), int(arr[1]))


class VectorArray:
    """Efficient collection of Vector2 objects using numpy arrays for batch operations.
    
    Provides numpy-accelerated operations on collections of 2D positions while 
    maintaining compatibility with Vector2 objects. Ideal for spatial queries,
    range calculations, and batch transformations.
    """
    
    def __init__(self, vectors: Optional[Union[list[Vector2], NDArray[np.int16]]] = None):
        """Initialize VectorArray from list of Vector2 objects or numpy array.
        
        Args:
            vectors: List of Vector2 objects or numpy array of shape (N, 2).
                    If None, creates an empty VectorArray.
        """
        if vectors is None:
            self._data = np.empty((0, 2), dtype=np.int16)
        elif isinstance(vectors, list):
            if not vectors:
                self._data = np.empty((0, 2), dtype=np.int16)
            else:
                self._data = np.array([[v.y, v.x] for v in vectors], dtype=np.int16)
        else:
            if vectors.shape[-1] != 2:
                raise ValueError("Numpy array must have shape (N, 2)")
            self._data = vectors.astype(np.int16)
    
    @property
    def data(self) -> NDArray[np.int16]:
        """Get the underlying numpy array (N, 2) shape."""
        return self._data
    
    @property
    def y_coords(self) -> NDArray[np.int16]:
        """Get all y coordinates."""
        return self._data[:, 0]
    
    @property 
    def x_coords(self) -> NDArray[np.int16]:
        """Get all x coordinates."""
        return self._data[:, 1]
    
    def __len__(self) -> int:
        """Get number of vectors."""
        return len(self._data)
    
    def __getitem__(self, index: int) -> Vector2:
        """Get Vector2 at index."""
        if index >= len(self._data) or index < -len(self._data):
            raise IndexError("VectorArray index out of range")
        row = self._data[index]
        return Vector2(int(row[0]), int(row[1]))
    
    def __iter__(self):
        """Make VectorArray iterable."""
        for row in self._data:
            yield Vector2(int(row[0]), int(row[1]))
    
    def to_vector_list(self) -> list[Vector2]:
        """Convert to list of Vector2 objects."""
        return [Vector2(int(row[0]), int(row[1])) for row in self._data]
    
    def distance_to_point(self, target: Vector2) -> NDArray[np.float64]:
        """Calculate Euclidean distances from all vectors to a target point.
        
        Args:
            target: Target Vector2 position
            
        Returns:
            Array of distances from each vector to target
        """
        target_arr = np.array([target.y, target.x], dtype=np.int16)
        diff = self._data - target_arr
        return np.sqrt(np.sum(diff**2, axis=1))
    
    def manhattan_distance_to_point(self, target: Vector2) -> NDArray[np.int16]:
        """Calculate Manhattan distances from all vectors to a target point.
        
        Args:
            target: Target Vector2 position
            
        Returns:
            Array of Manhattan distances from each vector to target
        """
        target_arr = np.array([target.y, target.x], dtype=np.int16)
        return np.sum(np.abs(self._data - target_arr), axis=1)
    
    def filter_by_distance(self, center: Vector2, min_dist: int, max_dist: int) -> "VectorArray":
        """Filter vectors by Manhattan distance range from center.
        
        Args:
            center: Center point for distance calculation
            min_dist: Minimum distance (inclusive)
            max_dist: Maximum distance (inclusive)
            
        Returns:
            New VectorArray containing vectors within distance range
        """
        distances = self.manhattan_distance_to_point(center)
        mask = (distances >= min_dist) & (distances <= max_dist)
        return VectorArray(self._data[mask])
    
    def filter_by_bounds(self, min_y: int, max_y: int, min_x: int, max_x: int) -> "VectorArray":
        """Filter vectors by rectangular bounds.
        
        Args:
            min_y, max_y: Y coordinate bounds (inclusive)
            min_x, max_x: X coordinate bounds (inclusive)
            
        Returns:
            New VectorArray containing vectors within bounds
        """
        mask = ((self._data[:, 0] >= min_y) & (self._data[:, 0] <= max_y) & 
                (self._data[:, 1] >= min_x) & (self._data[:, 1] <= max_x))
        return VectorArray(self._data[mask])
    
    def contains(self, vector: Vector2) -> bool:
        """Check if array contains a specific vector.
        
        Args:
            vector: Vector to search for
            
        Returns:
            True if vector is in the array
        """
        target = np.array([vector.y, vector.x], dtype=np.int16)
        return bool(np.any(np.all(self._data == target, axis=1)))
    
    def unique(self) -> "VectorArray":
        """Remove duplicate vectors.
        
        Returns:
            New VectorArray with unique vectors only
        """
        unique_data = np.unique(self._data, axis=0)
        return VectorArray(unique_data)
    
    @classmethod
    def from_ranges(cls, y_range: tuple[int, int], x_range: tuple[int, int]) -> "VectorArray":
        """Create VectorArray from coordinate ranges.
        
        Args:
            y_range: (min_y, max_y) inclusive range
            x_range: (min_x, max_x) inclusive range
            
        Returns:
            VectorArray containing all coordinate combinations in ranges
        """
        y_min, y_max = y_range
        x_min, x_max = x_range
        
        y_coords, x_coords = np.mgrid[y_min:y_max+1, x_min:x_max+1]
        positions = np.column_stack((y_coords.ravel(), x_coords.ravel()))
        
        return cls(positions)


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
        from ..entities.renderable import UnitRenderData
        
        # Extract wound information
        wound_count = 0
        wound_descriptions = []
        wound_penalties = {}
        if hasattr(unit, 'wound') and unit.wound:
            wound_count = unit.wound.get_wound_count()
            wound_penalties = unit.wound.get_wound_penalties()
            
            # Generate wound descriptions for display
            for wound in unit.wound.active_wounds:
                severity_text = wound.properties.severity.name.lower()
                body_part_text = wound.properties.body_part.name.replace('_', ' ').lower()
                wound_descriptions.append(f"{severity_text.title()} {body_part_text} {wound.properties.wound_type.name.lower()}")
        
        # Extract morale information
        morale_current = 100
        morale_state = "Steady"
        morale_modifiers = {}
        if hasattr(unit, 'morale') and unit.morale:
            morale_current = unit.morale.get_effective_morale()
            morale_state = unit.morale.get_morale_state()
            morale_modifiers = unit.morale.temporary_modifiers.copy()
        
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
            status_effects=[],  # Placeholder - would come from status effect system
            # Wound and injury information
            wound_count=wound_count,
            wound_descriptions=wound_descriptions,
            wound_penalties=wound_penalties,
            # Morale and psychological state
            morale_current=morale_current,
            morale_state=morale_state,
            morale_modifiers=morale_modifiers
        )
    
    @staticmethod
    def scenario_data_to_unit(unit_data: "UnitData") -> "Unit":
        """Convert scenario UnitData to a game Unit instance.
        
        Args:
            unit_data: UnitData from scenario loading
            
        Returns:
            Fully initialized Unit instance
        """
        from ...game.entities.unit import Unit
        
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
                    elif stat_name == "ai_behavior":
                        # Override AI behavior - value should be string like "AGGRESSIVE" or "INACTIVE"
                        from ...game.ai.ai_behaviors import create_ai_behavior, AIType
                        try:
                            ai_type = getattr(AIType, value)
                            ai_behavior = create_ai_behavior(ai_type)
                            unit.ai.set_behavior(ai_behavior)
                        except (AttributeError, ValueError):
                            # Invalid AI behavior type - ignore or use default
                            pass
        
        return unit
    
    @staticmethod
    def units_to_render_data_list(units, highlight_func=None) -> list["UnitRenderData"]:
        """Convert a collection of Units to a list of UnitRenderData.
        
        Args:
            units: Dictionary of unit_id -> Unit instances or list of Unit instances
            highlight_func: Optional function that takes a unit and returns highlight_type
            
        Returns:
            List of UnitRenderData for all alive units
        """
        render_data = []
        
        # Handle dict, list, and UnitCollection types
        if isinstance(units, dict):
            unit_collection = units.values()
        elif hasattr(units, '__iter__'):
            unit_collection = units
        else:
            unit_collection = [units]
            
        for unit in unit_collection:
            if unit is not None and unit.is_alive:
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