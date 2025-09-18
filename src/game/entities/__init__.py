"""Entity system components.

This package contains entity definitions and component implementations:
- components.py: Game-specific component implementations (Actor, Health, Movement, Combat, Status)  
- unit.py: Component-based units with Vector2 positioning
- map_objects.py: Interactive map objects and environmental elements
- unit_templates.py: Unit class definitions and base stats
"""

from .components import (
    ActorComponent,
    HealthComponent, 
    MovementComponent,
    CombatComponent,
    StatusComponent,
    MoraleComponent,
    WoundComponent,
    InterruptComponent,
)
from .unit import Unit
from .map_objects import MapObjects, SpawnPoint, Region, Trigger
from .unit_templates import ComponentTemplate, get_template, create_unit_entity

__all__ = [
    "ActorComponent",
    "HealthComponent",
    "MovementComponent", 
    "CombatComponent",
    "StatusComponent",
    "MoraleComponent",
    "WoundComponent",
    "InterruptComponent",
    "Unit",
    "MapObjects",
    "SpawnPoint",
    "Region",
    "Trigger",
    "ComponentTemplate",
    "get_template",
    "create_unit_entity",
]