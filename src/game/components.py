"""Game-specific components for units and other game entities.

This module contains the concrete component implementations for the Grimdark SRPG,
including the 5 core unit components: Actor, Health, Movement, Combat, and Status.
"""

from typing import TYPE_CHECKING

from ..core.components import Component
from ..core.game_enums import UnitClass, Team, UNIT_CLASS_NAMES
from ..core.game_info import UNIT_CLASS_DATA
from ..core.data_structures import Vector2

if TYPE_CHECKING:
    from ..core.components import Entity
    from ..core.game_info import UnitClassInfo


class ActorComponent(Component):
    """Component for identity and classification.
    
    Handles who the unit is in the game world - their name, class, team affiliation,
    and display information. This component provides the core identity that other
    components may reference for class-specific behaviors in the future.
    """
    
    def __init__(self, entity: "Entity", name: str, unit_class: UnitClass, team: Team):
        """Initialize actor component.
        
        Args:
            entity: The entity this component belongs to
            name: Display name of the unit
            unit_class: Unit class enum (Knight, Archer, etc.)
            team: Team affiliation enum (Player, Enemy, etc.)
        """
        super().__init__(entity)
        self.name = name
        self.unit_class = unit_class
        self.team = team
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Actor"
    
    def get_display_name(self) -> str:
        """Get the display name for this unit."""
        return self.name
    
    def get_class_name(self) -> str:
        """Get the human-readable class name."""
        return UNIT_CLASS_NAMES[self.unit_class]
    
    def get_class_info(self) -> "UnitClassInfo":
        """Get the class information for this unit's class."""
        return UNIT_CLASS_DATA[self.unit_class]
    
    def is_ally_of(self, other: "ActorComponent") -> bool:
        """Check if this unit is an ally of another unit.
        
        Args:
            other: The other unit's ActorComponent to check against
            
        Returns:
            True if units are on the same team, False otherwise
        """
        return self.team == other.team
    
    def get_symbol(self) -> str:
        """Get the display symbol for this unit's class."""
        return self.get_class_info().symbol


class HealthComponent(Component):
    """Component for life and death management.
    
    Handles the unit's vitality, including current and maximum hit points,
    damage and healing operations, and life/death state tracking.
    """
    
    def __init__(self, entity: "Entity", hp_max: int):
        """Initialize health component.
        
        Args:
            entity: The entity this component belongs to
            hp_max: Maximum hit points for this unit
        """
        super().__init__(entity)
        self.hp_max = hp_max
        self.hp_current = hp_max  # Start at full health
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Health"
    
    def is_alive(self) -> bool:
        """Check if the unit is alive.
        
        Returns:
            True if hp_current > 0, False otherwise
        """
        return self.hp_current > 0
    
    def get_hp_percent(self) -> float:
        """Get current health as a percentage of maximum.
        
        Returns:
            Health percentage from 0.0 to 1.0
        """
        if self.hp_max <= 0:
            return 0.0
        return self.hp_current / self.hp_max
    
    def take_damage(self, amount: int) -> int:
        """Apply damage to this unit.
        
        Args:
            amount: Amount of damage to apply
            
        Returns:
            Actual damage dealt (may be less due to overkill prevention)
        """
        if amount < 0:
            raise ValueError("Damage amount cannot be negative")
        
        old_hp = self.hp_current
        self.hp_current = max(0, self.hp_current - amount)
        return old_hp - self.hp_current
    
    def heal(self, amount: int) -> int:
        """Apply healing to this unit.
        
        Args:
            amount: Amount of healing to apply
            
        Returns:
            Actual healing done (may be less due to max hp cap)
        """
        if amount < 0:
            raise ValueError("Healing amount cannot be negative")
        
        old_hp = self.hp_current
        self.hp_current = min(self.hp_max, self.hp_current + amount)
        return self.hp_current - old_hp
    
    def set_max_hp(self, new_max: int) -> None:
        """Set a new maximum HP value.
        
        Args:
            new_max: New maximum HP value
        """
        if new_max < 0:
            raise ValueError("Maximum HP cannot be negative")
        
        self.hp_max = new_max
        # If current HP exceeds new max, reduce it
        if self.hp_current > self.hp_max:
            self.hp_current = self.hp_max
    
    def restore_full_health(self) -> None:
        """Restore unit to full health."""
        self.hp_current = self.hp_max


class MovementComponent(Component):
    """Component for position and movement capabilities.
    
    Handles the unit's spatial location, facing direction, and movement-related
    functionality including position tracking and orientation management.
    """
    
    def __init__(self, entity: "Entity", position: Vector2, movement_points: int):
        """Initialize movement component.
        
        Args:
            entity: The entity this component belongs to
            position: Initial position vector
            movement_points: Base movement points per turn
        """
        super().__init__(entity)
        self.position = position
        self.facing = "south"  # Default facing direction
        self.movement_points = movement_points
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Movement"
    
    def get_position(self) -> Vector2:
        """Get the current position vector.
        
        Returns:
            Vector2 position
        """
        return self.position
    
    def set_position(self, position: Vector2) -> None:
        """Set the position directly without movement logic.
        
        Args:
            position: New position vector
        """
        self.position = position
    
    def move_to(self, position: Vector2) -> None:
        """Move to a new position and update facing direction.
        
        Args:
            position: Target position vector
        """
        # Update facing based on movement direction
        dx = position.x - self.position.x
        dy = position.y - self.position.y
        
        if dx > 0:
            self.facing = "east"
        elif dx < 0:
            self.facing = "west"
        elif dy > 0:
            self.facing = "south"
        elif dy < 0:
            self.facing = "north"
        # If dx == 0 and dy == 0, keep current facing
        
        self.position = position
    
    def face_direction(self, direction: str) -> None:
        """Set the facing direction explicitly.
        
        Args:
            direction: Direction to face ("north", "south", "east", "west")
        """
        if direction not in ["north", "south", "east", "west"]:
            raise ValueError(f"Invalid facing direction: {direction}")
        self.facing = direction
    
    def face_towards(self, target: Vector2) -> None:
        """Face towards a target position.
        
        Args:
            target: Position vector to face towards
        """
        dx = target.x - self.position.x
        dy = target.y - self.position.y
        
        # Face the direction with the largest absolute difference
        if abs(dx) > abs(dy):
            self.facing = "east" if dx > 0 else "west"
        elif dy != 0:
            self.facing = "south" if dy > 0 else "north"
        # If both are 0, keep current facing


class CombatComponent(Component):
    """Component for combat statistics and abilities.
    
    Handles combat-related data including attack and defense values,
    attack range, and damage calculations. This component focuses purely
    on combat mechanics and statistics.
    """
    
    def __init__(self, entity: "Entity", strength: int, defense: int, 
                 attack_range_min: int, attack_range_max: int, 
                 aoe_pattern: str = "single"):
        """Initialize combat component.
        
        Args:
            entity: The entity this component belongs to
            strength: Attack strength value
            defense: Defense value
            attack_range_min: Minimum attack range
            attack_range_max: Maximum attack range
            aoe_pattern: Area of effect pattern ("single", "cross", etc.)
        """
        super().__init__(entity)
        self.strength = strength
        self.defense = defense
        self.attack_range_min = attack_range_min
        self.attack_range_max = attack_range_max
        self.aoe_pattern = aoe_pattern
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Combat"
    
    def calculate_damage_to(self, target_combat: "CombatComponent") -> int:
        """Calculate damage this unit would deal to a target.
        
        Args:
            target_combat: The target's CombatComponent
            
        Returns:
            Damage amount (minimum 1)
        """
        base_damage = self.strength
        mitigation = target_combat.defense
        return max(1, base_damage - mitigation)
    
    def can_attack(self, target: Vector2) -> bool:
        """Check if this unit can attack a position based on range.
        
        Args:
            target: Target position vector
            
        Returns:
            True if position is within attack range, False otherwise
        """
        # Get position from movement component
        movement_component = self.entity.get_component("Movement")
        if movement_component is None:
            return False
        
        # Cast to MovementComponent to access position attribute
        from typing import cast
        movement = cast('MovementComponent', movement_component)
        
        # Calculate Manhattan distance
        distance = movement.position.manhattan_distance_to(target)
        
        return self.attack_range_min <= distance <= self.attack_range_max
    
    def get_attack_range(self) -> tuple[int, int]:
        """Get the attack range as a tuple.
        
        Returns:
            Tuple of (min_range, max_range)
        """
        return (self.attack_range_min, self.attack_range_max)


class StatusComponent(Component):
    """Component for turn state and action availability.
    
    Manages the unit's state within the turn-based system, including
    movement and action availability, turn initialization/cleanup,
    and speed/initiative tracking.
    """
    
    def __init__(self, entity: "Entity", speed: int):
        """Initialize status component.
        
        Args:
            entity: The entity this component belongs to
            speed: Speed/initiative value for turn order
        """
        super().__init__(entity)
        self.speed = speed
        self.has_moved = False
        self.has_acted = False
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Status"
    
    def can_move(self) -> bool:
        """Check if the unit can move this turn.
        
        Returns:
            True if unit is alive and hasn't moved yet, False otherwise
        """
        # Check if unit is alive
        health_component = self.entity.get_component("Health")
        if health_component is None:
            return False
        
        from typing import cast
        health = cast('HealthComponent', health_component)
        if not health.is_alive():
            return False
        
        return not self.has_moved
    
    def can_act(self) -> bool:
        """Check if the unit can perform an action this turn.
        
        Returns:
            True if unit is alive and hasn't acted yet, False otherwise
        """
        # Check if unit is alive
        health_component = self.entity.get_component("Health")
        if health_component is None:
            return False
        
        from typing import cast
        health = cast('HealthComponent', health_component)
        if not health.is_alive():
            return False
        
        return not self.has_acted
    
    def mark_moved(self) -> None:
        """Mark that the unit has moved this turn."""
        self.has_moved = True
    
    def mark_acted(self) -> None:
        """Mark that the unit has acted this turn."""
        self.has_acted = True
    
    def start_turn(self) -> None:
        """Initialize the unit for a new turn."""
        self.has_moved = False
        self.has_acted = False
    
    def end_turn(self) -> None:
        """Clean up the unit at the end of their turn."""
        # Currently same as start_turn, but kept separate for future expansion
        self.has_moved = False
        self.has_acted = False
    
    def get_turn_priority(self) -> int:
        """Get the turn priority for initiative order.
        
        Returns:
            Speed value for determining turn order (higher = earlier)
        """
        return self.speed