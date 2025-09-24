"""Component-based Unit implementation with backward compatibility.

This module provides the new Unit class that uses the component system internally
while maintaining the exact same API as the original Unit class for backward
compatibility.
"""

from typing import Optional, cast

from ...core.data import UnitClass, Team, Vector2, ComponentType
from ...core.entities import Component
from .unit_templates import create_unit_entity
from .components import (
    ActorComponent, HealthComponent, MovementComponent, 
    CombatComponent, StatusComponent, InterruptComponent, AIComponent,
    MoraleComponent, WoundComponent
)


class Unit:
    """Component-based unit with hybrid property access.
    
    This Unit class uses an Entity + 5 Components internally:
    - Actor: Identity and classification
    - Health: Life and death management  
    - Movement: Position and movement
    - Combat: Combat statistics and abilities
    - Status: Turn state and action management
    
    Property Access Patterns:
    1. **Core properties** (most frequent): unit.x, unit.hp_current, unit.is_alive
    2. **Component access** (less frequent): unit.combat.strength, unit.health.hp_max
    
    Examples:
        # Frequent operations (direct properties)
        unit.x = 5
        unit.hp_current = 20
        if unit.is_alive and unit.can_move:
            # Note: Movement should be done via map.move_unit(unit.unit_id, position)
            pass
        
        # Less frequent operations (component access)  
        unit.combat.strength = 10
        unit.health.hp_max = 25
        unit.actor.unit_class  # UnitClass.KNIGHT
        unit.status.speed = 5
        unit.actor.get_class_name()  # "Knight"
    """
    
    def __init__(self, name: str, unit_class: UnitClass, team: Team, position: Vector2, unit_id: Optional[str] = None):
        """Initialize unit using component system.
        
        Args:
            name: Display name
            unit_class: Unit class enum
            team: Team affiliation
            position: Initial position vector
            unit_id: Optional custom unit ID (for backward compatibility)
        """
        # Create entity with all components
        self.entity = create_unit_entity(name, unit_class, team, position)
        
        # Override entity ID if provided (for backward compatibility)
        if unit_id is not None:
            self.entity.entity_id = unit_id
    
    # ============== Core Properties (Most Frequently Used) ==============
    
    @property
    def name(self) -> str:
        """Get unit name."""
        return self.actor.name
    
    @property
    def team(self) -> Team:
        """Get team affiliation."""
        return self.actor.team
    
    @property
    def unit_id(self) -> str:
        """Get unique unit ID."""
        return self.entity.entity_id
    
    @property
    def position(self) -> Vector2:
        """Get position vector."""
        return self.movement.position
    
    @property
    def facing(self) -> str:
        """Get facing direction."""
        return self.movement.facing
    
    @property
    def hp_current(self) -> int:
        """Get current hit points."""
        return self.health.hp_current
    
    @hp_current.setter
    def hp_current(self, value: int) -> None:
        """Set current hit points directly."""
        self.health.hp_current = max(0, value)
    
    @property  
    def mana_current(self) -> int:
        """Get current mana points (placeholder for future magic system)."""
        # For now, return 0 since mana system isn't implemented yet
        return 0
    
    @property
    def mana_max(self) -> int:
        """Get maximum mana points (placeholder for future magic system)."""
        # For now, return 0 since mana system isn't implemented yet
        return 0
    
    @property
    def has_moved(self) -> bool:
        """Check if unit has moved this turn."""
        return self.status.has_moved
    
    @has_moved.setter
    def has_moved(self, value: bool) -> None:
        """Set moved status directly."""
        self.status.has_moved = value
    
    @property
    def has_acted(self) -> bool:
        """Check if unit has acted this turn."""
        return self.status.has_acted
    
    @has_acted.setter
    def has_acted(self, value: bool) -> None:
        """Set acted status directly."""
        self.status.has_acted = value
    
    @property
    def is_alive(self) -> bool:
        """Check if unit is alive."""
        return self.health.is_alive()
    
    @property
    def can_act(self) -> bool:
        """Check if unit can act this turn."""
        return self.health.is_alive() and self.status.can_act()
    
    @property
    def can_move(self) -> bool:
        """Check if unit can move this turn."""
        return self.health.is_alive() and self.status.can_move()
    
    @property
    def status_effects(self) -> list[str]:
        """Get list of active status effects. Placeholder until status system is implemented."""
        return []
    
    
    
    # ============== Core Components (Always Present) ==============
    
    @property
    def actor(self) -> ActorComponent:
        """Actor component - identity and team affiliation."""
        return cast(ActorComponent, self.entity.require_component(ComponentType.ACTOR))
    
    @property  
    def health(self) -> HealthComponent:
        """Health component - HP and life status."""
        return cast(HealthComponent, self.entity.require_component(ComponentType.HEALTH))
    
    @property
    def movement(self) -> MovementComponent:
        """Movement component - position and mobility."""
        return cast(MovementComponent, self.entity.require_component(ComponentType.MOVEMENT))
    
    @property
    def combat(self) -> CombatComponent:
        """Combat component - attack and defense capabilities."""
        return cast(CombatComponent, self.entity.require_component(ComponentType.COMBAT))
    
    @property
    def status(self) -> StatusComponent:
        """Status component - turn state and availability."""
        return cast(StatusComponent, self.entity.require_component(ComponentType.STATUS))
    
    # ============== Optional Components ==============
    
    @property
    def interrupt(self) -> InterruptComponent:
        """Interrupt component - prepared actions and reactions."""
        return cast(InterruptComponent, self.entity.require_component(ComponentType.INTERRUPT))
    
    @property
    def morale(self) -> MoraleComponent:
        """Morale component - psychological state."""
        return cast(MoraleComponent, self.entity.require_component(ComponentType.MORALE))
    
    @property
    def wound(self) -> WoundComponent:
        """Wound component - injury tracking."""
        return cast(WoundComponent, self.entity.require_component(ComponentType.WOUND))
    
    @property
    def ai(self) -> AIComponent:
        """AI component - computer control behavior."""
        return cast(AIComponent, self.entity.require_component(ComponentType.AI))
    
    
    # ============== Methods (delegate to components) ==============
    
    def update_position_and_status(self, position: Vector2) -> None:
        """Update position and movement status. Does NOT update map occupancy.
        
        This method should only be called by the Map class during unit movement.
        External code should use map.move_unit() instead.
        """
        old_position = self.position
        self.movement.set_position(position)
        self.movement.update_facing_from_movement(old_position, position)
        self.status.mark_moved()
    
    def take_damage(self, damage: int) -> None:
        """Take damage."""
        self.health.take_damage(damage)
    
    def heal(self, amount: int) -> None:
        """Heal damage."""
        self.health.heal(amount)
    
    def end_turn(self) -> None:
        """End turn."""
        self.status.end_turn()
    
    def start_turn(self) -> None:
        """Start turn."""
        self.status.start_turn()
    
    def calculate_damage_to(self, target: "Unit") -> int:
        """Calculate damage to target."""
        return self.combat.calculate_damage_to(target.combat)
    
    
    # ============== Component Management ==============
    
    def add_component(self, component: "Component") -> None:
        """Add a component, checking for duplicates.
        
        Args:
            component: Fully configured component to add
            
        Raises:
            ValueError: If unit already has this component type
        """
        component_type = component.get_component_type()
        
        if self.entity.has_component(component_type):
            raise ValueError(f"Unit already has component: {component_type}")
            
        self.entity.add_component(component)
    
    def has_component(self, component_type: ComponentType) -> bool:
        """Check if unit has the specified component type.
        
        Args:
            component_type: Component type to check for
            
        Returns:
            True if component is present
        """
        return self.entity.has_component(component_type)
    
    def remove_component(self, component_type: ComponentType) -> None:
        """Remove component by type.
        
        Args:
            component_type: Component type to remove
        """
        self.entity.remove_component(component_type)