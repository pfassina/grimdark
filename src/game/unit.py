"""Component-based Unit implementation with backward compatibility.

This module provides the new Unit class that uses the component system internally
while maintaining the exact same API as the original Unit class for backward
compatibility.
"""

from typing import TYPE_CHECKING, Optional

from ..core.game_enums import UnitClass, Team
from ..core.data_structures import Vector2
from .unit_templates import create_unit_entity
from .components import (
    ActorComponent, HealthComponent, MovementComponent, 
    CombatComponent, StatusComponent, InterruptComponent, AIComponent
)

if TYPE_CHECKING:
    from .components import MoraleComponent, WoundComponent


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
        return self._actor.name
    
    @property
    def team(self) -> Team:
        """Get team affiliation."""
        return self._actor.team
    
    @property
    def unit_id(self) -> str:
        """Get unique unit ID."""
        return self.entity.entity_id
    
    @property
    def position(self) -> Vector2:
        """Get position vector."""
        return self._movement.position
    
    @property
    def facing(self) -> str:
        """Get facing direction."""
        return self._movement.facing
    
    @property
    def hp_current(self) -> int:
        """Get current hit points."""
        return self._health.hp_current
    
    @hp_current.setter
    def hp_current(self, value: int) -> None:
        """Set current hit points directly."""
        self._health.hp_current = max(0, value)
    
    @property
    def has_moved(self) -> bool:
        """Check if unit has moved this turn."""
        return self._status.has_moved
    
    @has_moved.setter
    def has_moved(self, value: bool) -> None:
        """Set moved status directly."""
        self._status.has_moved = value
    
    @property
    def has_acted(self) -> bool:
        """Check if unit has acted this turn."""
        return self._status.has_acted
    
    @has_acted.setter
    def has_acted(self, value: bool) -> None:
        """Set acted status directly."""
        self._status.has_acted = value
    
    @property
    def is_alive(self) -> bool:
        """Check if unit is alive."""
        return self._health.is_alive()
    
    @property
    def can_act(self) -> bool:
        """Check if unit can act this turn."""
        return self._status.can_act()
    
    @property
    def can_move(self) -> bool:
        """Check if unit can move this turn."""
        return self._status.can_move()
    
    @property
    def status_effects(self) -> list[str]:
        """Get list of active status effects. Placeholder until status system is implemented."""
        return []
    
    # ============== Component Access Properties ==============
    
    @property
    def actor(self) -> ActorComponent:
        """Access Actor component for unit_class, symbol, class_name, etc."""
        return self._actor
    
    @property  
    def health(self) -> HealthComponent:
        """Access Health component for hp_max, hp_percent, healing methods, etc."""
        return self._health
    
    @property
    def movement(self) -> MovementComponent:  
        """Access Movement component for movement_points, face_direction, etc."""
        return self._movement
    
    @property
    def combat(self) -> CombatComponent:
        """Access Combat component for strength, defense, attack_range, etc."""
        return self._combat
    
    @property
    def status(self) -> StatusComponent:
        """Access Status component for speed, mark_moved, turn methods, etc."""
        return self._status
    
    
    # ============== Component Access Helpers (Internal) ==============
    
    @property
    def _actor(self) -> ActorComponent:
        """Get Actor component (internal helper)."""
        from typing import cast
        return cast(ActorComponent, self.entity.require_component("Actor"))
    
    @property  
    def _health(self) -> HealthComponent:
        """Get Health component (internal helper)."""
        from typing import cast
        return cast(HealthComponent, self.entity.require_component("Health"))
    
    @property
    def _movement(self) -> MovementComponent:
        """Get Movement component (internal helper)."""
        from typing import cast
        return cast(MovementComponent, self.entity.require_component("Movement"))
    
    @property
    def _combat(self) -> CombatComponent:
        """Get Combat component (internal helper)."""
        from typing import cast
        return cast(CombatComponent, self.entity.require_component("Combat"))
    
    @property
    def _status(self) -> StatusComponent:
        """Get Status component (internal helper)."""
        from typing import cast
        return cast(StatusComponent, self.entity.require_component("Status"))
    
    @property
    def _interrupt(self) -> InterruptComponent:
        """Get Interrupt component (internal helper)."""
        from typing import cast
        return cast(InterruptComponent, self.entity.require_component("Interrupt"))
    
    @property
    def _morale(self) -> "MoraleComponent":
        """Get Morale component (internal helper)."""
        from typing import cast
        from .components import MoraleComponent
        return cast(MoraleComponent, self.entity.require_component("Morale"))
    
    @property
    def _wound(self) -> "WoundComponent":
        """Get Wound component (internal helper)."""
        from typing import cast
        from .components import WoundComponent
        return cast(WoundComponent, self.entity.require_component("Wound"))
    
    @property
    def _ai(self) -> AIComponent:
        """Get AI component (internal helper)."""
        from typing import cast
        return cast(AIComponent, self.entity.require_component("AI"))
    
    @property
    def interrupt(self) -> InterruptComponent:
        """Access Interrupt component for prepared actions and interrupts."""
        return self._interrupt
    
    @property
    def morale(self) -> "MoraleComponent":
        """Access Morale component for psychological state management."""
        return self._morale
    
    @property
    def wound(self) -> "WoundComponent":
        """Access Wound component for injury and scar management."""
        return self._wound
    
    @property
    def ai(self) -> AIComponent:
        """Access AI component for behavior and decision-making."""
        return self._ai
    
    
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
    
    def can_attack(self, target: Vector2) -> bool:
        """Check if can attack position."""
        # Need to check status as well for backward compatibility
        if not self.status.can_act():
            return False
        return self.combat.can_attack(target)