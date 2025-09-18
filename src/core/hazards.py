"""
Environmental Hazard System - Core hazard types and behaviors

This module defines the base classes and concrete implementations for 
environmental hazards that can affect the battlefield. Hazards act on 
their own timeline entries and can spread, damage units, and alter terrain.
"""

from __future__ import annotations
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

from .data.data_structures import Vector2
from .data.game_enums import Team

if TYPE_CHECKING:
    from src.game.entities.unit import Unit
    from src.game.map import GameMap


class HazardType(Enum):
    """Types of environmental hazards"""
    FIRE = auto()
    POISON_CLOUD = auto()
    COLLAPSING_TERRAIN = auto()
    ICE = auto()
    DARKNESS = auto()
    ACID_POOL = auto()
    LIGHTNING_FIELD = auto()


class HazardSpreadPattern(Enum):
    """How hazards spread across the battlefield"""
    ADJACENT = auto()      # Spreads to orthogonally adjacent tiles
    DIAGONAL = auto()      # Spreads to all 8 surrounding tiles  
    WIND_DRIVEN = auto()   # Spreads in a directional pattern
    RANDOM = auto()        # Spreads randomly to nearby tiles
    STATIC = auto()        # Does not spread


@dataclass
class HazardEffect:
    """Effects that a hazard applies to units/terrain"""
    damage: int = 0                    # Direct damage per tick
    damage_type: str = "physical"      # Type of damage dealt
    movement_penalty: int = 0          # Additional movement cost
    visibility_reduction: int = 0      # Reduces sight range
    stat_modifiers: dict[str, int] = field(default_factory=dict)  # Stat changes
    status_effects: list[str] = field(default_factory=list)       # Status conditions applied
    terrain_transformation: Optional[str] = None  # Changes terrain type
    destroys_objects: bool = False     # Destroys destructible objects
    blocks_movement: bool = False      # Completely blocks movement
    blocks_line_of_sight: bool = False # Blocks vision


@dataclass
class HazardProperties:
    """Configuration for a hazard's behavior"""
    hazard_type: HazardType
    name: str
    description: str
    
    # Lifetime
    duration: int = -1              # Ticks until expiration (-1 = permanent)
    ticks_per_action: int = 100    # Timeline weight for hazard actions
    
    # Spreading
    spread_pattern: HazardSpreadPattern = HazardSpreadPattern.STATIC
    spread_chance: float = 0.5      # Probability of spreading each tick
    spread_range: int = 1           # Max distance for spreading
    max_spread_count: int = -1      # Max tiles it can spread to (-1 = unlimited)
    spread_requires: list[str] = field(default_factory=list)  # Terrain types needed to spread
    spread_blocked_by: list[str] = field(default_factory=list)  # Terrain that blocks spread
    
    # Effects
    initial_effect: HazardEffect = field(default_factory=HazardEffect)
    recurring_effect: HazardEffect = field(default_factory=HazardEffect)
    final_effect: Optional[HazardEffect] = None  # Applied when hazard expires
    
    # Interactions
    combines_with: list[HazardType] = field(default_factory=list)  # Creates new hazards
    neutralizes: list[HazardType] = field(default_factory=list)    # Removes other hazards
    immune_units: list[str] = field(default_factory=list)          # Unit types unaffected
    
    # Visuals (for renderer)
    symbol: str = "?"
    color_hint: str = "red"
    animation_type: str = "pulse"


class Hazard(ABC):
    """Base class for all environmental hazards"""
    
    def __init__(self, position: Vector2, properties: HazardProperties, 
                 intensity: int = 1, source_unit: Optional[Unit] = None):
        """
        Initialize a hazard at a position
        
        Args:
            position: Grid position of the hazard
            properties: Configuration for hazard behavior
            intensity: Strength/size of the hazard (affects damage/spread)
            source_unit: Unit that created the hazard (for tracking kills)
        """
        self.position = position
        self.properties = properties
        self.intensity = intensity
        self.source_unit = source_unit
        self.ticks_remaining = properties.duration
        self.spread_count = 0
        self.affected_positions: set[tuple[int, int]] = {(position.y, position.x)}
        self.creation_time: int = 0  # Set by hazard manager
        
    @abstractmethod
    def tick(self, game_map: GameMap, current_time: int) -> list[HazardAction]:
        """
        Process one tick of hazard behavior
        
        Returns list of actions to perform (damage, spread, etc)
        """
        pass
        
    @abstractmethod
    def can_spread_to(self, position: Vector2, game_map: GameMap) -> bool:
        """Check if hazard can spread to a given position"""
        pass
        
    @abstractmethod
    def apply_effect_to_unit(self, unit: Unit) -> HazardEffect:
        """Apply hazard effects to a unit standing in it"""
        pass
        
    def combine_with(self, other: Hazard) -> Optional[Hazard]:
        """
        Combine with another hazard to create new effect
        
        Returns new hazard if combination is valid, None otherwise
        """
        if other.properties.hazard_type in self.properties.combines_with:
            # Subclasses implement specific combination logic
            return self._create_combined_hazard(other)
        return None
        
    def _create_combined_hazard(self, other: Hazard) -> Optional[Hazard]:
        """Subclasses override to define combination results"""
        return None
        
    def is_expired(self) -> bool:
        """Check if hazard should be removed"""
        return self.ticks_remaining == 0
        
    def reduce_duration(self, ticks: int = 1) -> None:
        """Reduce remaining duration"""
        if self.ticks_remaining > 0:
            self.ticks_remaining = max(0, self.ticks_remaining - ticks)


@dataclass
class HazardAction:
    """Action performed by a hazard during its tick"""
    action_type: str  # "damage", "spread", "transform", etc
    position: Vector2
    data: dict = field(default_factory=dict)


# Concrete Hazard Implementations

class FireHazard(Hazard):
    """Spreading fire that damages units and terrain"""
    
    @classmethod
    def get_default_properties(cls) -> HazardProperties:
        return HazardProperties(
            hazard_type=HazardType.FIRE,
            name="Fire",
            description="Spreading flames that burn everything",
            duration=300,  # Burns for 300 ticks
            ticks_per_action=80,  # Acts faster than most units
            spread_pattern=HazardSpreadPattern.ADJACENT,
            spread_chance=0.3,
            spread_range=1,
            spread_requires=["grass", "forest", "wood"],
            spread_blocked_by=["water", "stone", "void"],
            initial_effect=HazardEffect(
                damage=8,
                damage_type="fire",
                visibility_reduction=1,
                terrain_transformation="burnt_ground"
            ),
            recurring_effect=HazardEffect(
                damage=5,
                damage_type="fire"
            ),
            combines_with=[HazardType.POISON_CLOUD],  # Creates toxic smoke
            neutralizes=[HazardType.ICE],
            immune_units=["fire_elemental", "phoenix"],
            symbol="🔥",
            color_hint="orange",
            animation_type="flicker"
        )
    
    def __init__(self, position: Vector2, intensity: int = 1, 
                 source_unit: Optional[Unit] = None):
        super().__init__(position, self.get_default_properties(), intensity, source_unit)
        
    def tick(self, game_map: GameMap, current_time: int) -> list[HazardAction]:
        actions = []
        
        # Apply damage to units in fire
        for pos in self.affected_positions:
            vec_pos = Vector2(pos[1], pos[0])
            unit = game_map.get_unit_at(vec_pos)
            if unit and unit.actor.unit_class not in self.properties.immune_units:
                actions.append(HazardAction(
                    "damage",
                    vec_pos,
                    {"effect": self.properties.recurring_effect, "unit": unit}
                ))
        
        # Try to spread
        if self.spread_count < self.properties.max_spread_count or self.properties.max_spread_count == -1:
            if random.random() < self.properties.spread_chance:
                spread_targets = self._get_spread_targets(game_map)
                if spread_targets:
                    target = random.choice(spread_targets)
                    actions.append(HazardAction(
                        "spread",
                        target,
                        {"intensity": max(1, self.intensity - 1)}
                    ))
                    self.spread_count += 1
        
        # Reduce duration
        self.reduce_duration()
        
        # Transform terrain if burning out
        if self.is_expired():
            for pos in self.affected_positions:
                vec_pos = Vector2(pos[1], pos[0])
                actions.append(HazardAction(
                    "transform_terrain",
                    vec_pos,
                    {"new_terrain": self.properties.initial_effect.terrain_transformation}
                ))
        
        return actions
    
    def _get_spread_targets(self, game_map: GameMap) -> list[Vector2]:
        """Get valid positions for fire to spread to"""
        targets = []
        for pos in self.affected_positions:
            y, x = pos
            # Check adjacent tiles
            for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                new_pos = Vector2(x + dx, y + dy)
                if self.can_spread_to(new_pos, game_map):
                    targets.append(new_pos)
        return targets
    
    def can_spread_to(self, position: Vector2, game_map: GameMap) -> bool:
        # Check bounds
        if not game_map.is_valid_position(position):
            return False
            
        # Check if already burning
        if (position.y, position.x) in self.affected_positions:
            return False
            
        # Check terrain type
        tile = game_map.get_tile(position)
        if tile.terrain_type in self.properties.spread_blocked_by:
            return False
        if self.properties.spread_requires and tile.terrain_type not in self.properties.spread_requires:
            return False
            
        return True
    
    def apply_effect_to_unit(self, unit: Unit) -> HazardEffect:
        # Fire damage scales with intensity
        effect = HazardEffect(
            damage=self.properties.recurring_effect.damage * self.intensity,
            damage_type=self.properties.recurring_effect.damage_type,
            status_effects=["burning"] if self.intensity > 1 else []
        )
        return effect


class PoisonCloudHazard(Hazard):
    """Toxic cloud that spreads with wind and poisons units"""
    
    @classmethod  
    def get_default_properties(cls) -> HazardProperties:
        return HazardProperties(
            hazard_type=HazardType.POISON_CLOUD,
            name="Poison Cloud",
            description="Toxic vapors that sicken and blind",
            duration=200,
            ticks_per_action=100,
            spread_pattern=HazardSpreadPattern.WIND_DRIVEN,
            spread_chance=0.4,
            spread_range=2,
            spread_blocked_by=["wall", "door"],
            recurring_effect=HazardEffect(
                damage=3,
                damage_type="poison",
                visibility_reduction=2,
                stat_modifiers={"speed": -20, "accuracy": -15},
                status_effects=["poisoned", "blinded"],
                blocks_line_of_sight=True
            ),
            combines_with=[HazardType.FIRE],  # Creates explosion
            immune_units=["undead", "construct", "poison_elemental"],
            symbol="☣",
            color_hint="green",
            animation_type="swirl"
        )
    
    def __init__(self, position: Vector2, intensity: int = 1, 
                 source_unit: Optional[Unit] = None, wind_direction: tuple[int, int] = (0, 1)):
        super().__init__(position, self.get_default_properties(), intensity, source_unit)
        self.wind_direction = wind_direction  # (dy, dx) for wind
        
    def tick(self, game_map: GameMap, current_time: int) -> list[HazardAction]:
        actions = []
        
        # Apply poison to units  
        for pos in self.affected_positions:
            vec_pos = Vector2(pos[1], pos[0])
            unit = game_map.get_unit_at(vec_pos)
            if unit and unit.actor.unit_class not in self.properties.immune_units:
                actions.append(HazardAction(
                    "damage",
                    vec_pos,
                    {"effect": self.properties.recurring_effect, "unit": unit}
                ))
        
        # Spread with wind
        if random.random() < self.properties.spread_chance:
            # Wind-driven spread favors wind direction
            for pos in list(self.affected_positions):
                y, x = pos
                new_y = y + self.wind_direction[0]
                new_x = x + self.wind_direction[1]
                new_pos = Vector2(new_x, new_y)
                
                if self.can_spread_to(new_pos, game_map):
                    actions.append(HazardAction(
                        "spread",
                        new_pos,
                        {"intensity": self.intensity}
                    ))
                    self.affected_positions.add((new_y, new_x))
        
        # Dissipate over time
        self.intensity = max(0, self.intensity - 0.1)
        self.reduce_duration()
        
        return actions
    
    def can_spread_to(self, position: Vector2, game_map: GameMap) -> bool:
        if not game_map.is_valid_position(position):
            return False
        
        tile = game_map.get_tile(position)
        if tile.terrain_type in self.properties.spread_blocked_by:
            return False
            
        return True
    
    def apply_effect_to_unit(self, unit: Unit) -> HazardEffect:
        return self.properties.recurring_effect


class CollapsingTerrainHazard(Hazard):
    """Terrain that is collapsing and will become impassable"""
    
    @classmethod
    def get_default_properties(cls) -> HazardProperties:
        return HazardProperties(
            hazard_type=HazardType.COLLAPSING_TERRAIN,
            name="Collapsing Ground",
            description="Unstable terrain about to give way",
            duration=30,  # Collapses quickly
            ticks_per_action=50,
            spread_pattern=HazardSpreadPattern.ADJACENT,
            spread_chance=0.2,  # Can trigger nearby collapses
            initial_effect=HazardEffect(
                movement_penalty=2,
                stat_modifiers={"defense": -10}
            ),
            final_effect=HazardEffect(
                damage=15,
                damage_type="crushing",
                terrain_transformation="chasm",
                blocks_movement=True
            ),
            symbol="⚠",
            color_hint="brown",
            animation_type="shake"
        )
    
    def __init__(self, position: Vector2, intensity: int = 1, 
                 source_unit: Optional[Unit] = None):
        super().__init__(position, self.get_default_properties(), intensity, source_unit)
        self.warning_given = False
        
    def tick(self, game_map: GameMap, current_time: int) -> list[HazardAction]:
        actions = []
        
        # Give warning before collapse
        if not self.warning_given and self.ticks_remaining <= 10:
            for pos in self.affected_positions:
                vec_pos = Vector2(pos[1], pos[0])
                actions.append(HazardAction(
                    "warning",
                    vec_pos,
                    {"message": "The ground is about to collapse!"}
                ))
            self.warning_given = True
        
        # Apply movement penalty to units
        for pos in self.affected_positions:
            vec_pos = Vector2(pos[1], pos[0])
            unit = game_map.get_unit_at(vec_pos)
            if unit:
                actions.append(HazardAction(
                    "apply_effect",
                    vec_pos,
                    {"effect": self.properties.initial_effect, "unit": unit}
                ))
        
        self.reduce_duration()
        
        # Collapse when expired
        if self.is_expired() and self.properties.final_effect:
            for pos in self.affected_positions:
                vec_pos = Vector2(pos[1], pos[0])
                unit = game_map.get_unit_at(vec_pos)
                if unit:
                    actions.append(HazardAction(
                        "damage",
                        vec_pos,
                        {"effect": self.properties.final_effect, "unit": unit}
                    ))
                actions.append(HazardAction(
                    "transform_terrain",
                    vec_pos,
                    {"new_terrain": self.properties.final_effect.terrain_transformation}
                ))
        
        return actions
    
    def can_spread_to(self, position: Vector2, game_map: GameMap) -> bool:
        # Collapses can trigger nearby unstable terrain
        if not game_map.is_valid_position(position):
            return False
            
        tile = game_map.get_tile(position)
        # Only spreads to similar terrain types
        return tile.terrain_type in ["bridge", "wood_floor", "cracked_stone"]
    
    def apply_effect_to_unit(self, unit: Unit) -> HazardEffect:
        if self.is_expired():
            return self.properties.final_effect or HazardEffect()
        return self.properties.initial_effect


class IceHazard(Hazard):
    """Slippery ice that affects movement and can spread cold"""
    
    @classmethod
    def get_default_properties(cls) -> HazardProperties:
        return HazardProperties(
            hazard_type=HazardType.ICE,
            name="Ice",
            description="Slippery frozen surface",
            duration=500,
            ticks_per_action=150,
            spread_pattern=HazardSpreadPattern.ADJACENT,
            spread_chance=0.1,
            spread_requires=["water", "wet_stone"],
            initial_effect=HazardEffect(
                movement_penalty=-1,  # Ice makes movement faster but uncontrolled
                stat_modifiers={"accuracy": -20, "evasion": -15},
                status_effects=["slipping"],
                terrain_transformation="ice"
            ),
            recurring_effect=HazardEffect(
                damage=1,
                damage_type="cold",
                status_effects=["chilled"]
            ),
            neutralizes=[HazardType.FIRE],
            immune_units=["ice_elemental", "frost_giant"],
            symbol="❄",
            color_hint="cyan",
            animation_type="sparkle"
        )
    
    def __init__(self, position: Vector2, intensity: int = 1, 
                 source_unit: Optional[Unit] = None):
        super().__init__(position, self.get_default_properties(), intensity, source_unit)
        
    def tick(self, game_map: GameMap, current_time: int) -> list[HazardAction]:
        actions = []
        
        # Apply cold damage and slipping to units
        for pos in self.affected_positions:
            vec_pos = Vector2(pos[1], pos[0])
            unit = game_map.get_unit_at(vec_pos)
            if unit and unit.actor.unit_class not in self.properties.immune_units:
                actions.append(HazardAction(
                    "apply_effect",
                    vec_pos,
                    {"effect": self.properties.recurring_effect, "unit": unit}
                ))
                
                # Chance to make unit slip and move randomly
                if random.random() < 0.2:  # 20% slip chance
                    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    dy, dx = random.choice(directions)
                    new_pos = Vector2(vec_pos.x + dx, vec_pos.y + dy)
                    if game_map.is_valid_position(new_pos) and not game_map.is_position_blocked(new_pos, self.source_unit.team if self.source_unit else Team.NEUTRAL):
                        actions.append(HazardAction(
                            "force_move",
                            vec_pos,
                            {"unit": unit, "new_position": new_pos, "message": f"{unit.name} slips on ice!"}
                        ))
        
        # Slowly spread to water tiles
        if random.random() < self.properties.spread_chance:
            for pos in list(self.affected_positions):
                y, x = pos
                for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    new_pos = Vector2(x + dx, y + dy)
                    if self.can_spread_to(new_pos, game_map):
                        actions.append(HazardAction(
                            "spread",
                            new_pos,
                            {"intensity": self.intensity}
                        ))
                        break
        
        # Melt over time (especially near fire)
        self.reduce_duration()
        
        return actions
    
    def can_spread_to(self, position: Vector2, game_map: GameMap) -> bool:
        if not game_map.is_valid_position(position):
            return False
            
        if (position.y, position.x) in self.affected_positions:
            return False
            
        tile = game_map.get_tile(position)
        return tile.terrain_type in self.properties.spread_requires
    
    def apply_effect_to_unit(self, unit: Unit) -> HazardEffect:
        return self.properties.recurring_effect


# Hazard Factory

def create_hazard(hazard_type: HazardType, position: Vector2, 
                  intensity: int = 1, source_unit: Optional[Unit] = None,
                  **kwargs) -> Hazard:
    """
    Factory function to create hazards by type
    
    Args:
        hazard_type: Type of hazard to create
        position: Position on the battlefield
        intensity: Strength of the hazard
        source_unit: Unit that created the hazard
        **kwargs: Additional parameters for specific hazard types
    
    Returns:
        Hazard instance
    """
    hazard_map = {
        HazardType.FIRE: FireHazard,
        HazardType.POISON_CLOUD: PoisonCloudHazard,
        HazardType.COLLAPSING_TERRAIN: CollapsingTerrainHazard,
        HazardType.ICE: IceHazard,
    }
    
    hazard_class = hazard_map.get(hazard_type)
    if not hazard_class:
        raise ValueError(f"Unknown hazard type: {hazard_type}")
    
    # Handle special construction parameters
    if hazard_type == HazardType.POISON_CLOUD and "wind_direction" in kwargs:
        return hazard_class(position, intensity, source_unit, kwargs["wind_direction"])
    
    return hazard_class(position, intensity, source_unit)