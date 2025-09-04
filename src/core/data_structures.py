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

from .game_enums import Team, UnitClass

if TYPE_CHECKING:
    from ..game.unit import Unit
    from ..game.scenario_structures import UnitData
    from .renderable import UnitRenderData


@dataclass
class BaseUnitData(ABC):
    """Base class defining common unit data fields."""
    name: str
    x: int
    y: int
    

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
            x=unit.x,
            y=unit.y,
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
            x=unit_data.x,
            y=unit_data.y
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
        if not hasattr(self, 'x') or not hasattr(self, 'y'):
            return False
        x = getattr(self, 'x', None)
        y = getattr(self, 'y', None)
        return 0 <= x < max_width and 0 <= y < max_height if x is not None and y is not None else False
    
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