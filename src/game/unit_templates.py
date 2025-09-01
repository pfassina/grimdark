"""Unit class templates for component initialization.

This module defines how different unit classes should be configured with components.
Templates are loaded from YAML files (with JSON fallback) and converted to data structures 
that specify initial values for each component based on the unit's class (Knight, Archer, etc.).
"""

import json
import os
from dataclasses import dataclass
from typing import Dict

from ..core.game_enums import UnitClass

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class ComponentTemplate:
    """Template for initializing components from unit class.
    
    Each field corresponds to a component and contains the initial
    values that should be passed to that component's constructor.
    """
    # HealthComponent initialization
    health: Dict[str, int]
    
    # MovementComponent initialization  
    movement: Dict[str, int]
    
    # CombatComponent initialization
    combat: Dict[str, int]
    
    # StatusComponent initialization
    status: Dict[str, int]


def _load_unit_templates() -> Dict[UnitClass, ComponentTemplate]:
    """Load unit templates from YAML file.
    
    Returns:
        Dictionary mapping UnitClass enums to ComponentTemplate objects
    """
    # Get the project root directory (two levels up from this file)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    yaml_path = os.path.join(project_root, "assets", "data", "units", "unit_templates.yaml")
    
    if not HAS_YAML:
        raise ImportError("PyYAML is required for unit templates. Please install pyyaml.")
    
    try:
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Unit templates file not found: {yaml_path}")
    
    # Parse templates from loaded data
    try:
        templates = {}
        for class_name, template_data in data["unit_templates"].items():
            # Convert string to UnitClass enum
            unit_class = getattr(UnitClass, class_name)
            templates[unit_class] = ComponentTemplate(
                health=template_data["health"],
                movement=template_data["movement"], 
                combat=template_data["combat"],
                status=template_data["status"]
            )
        
        print(f"Loaded {len(templates)} unit templates from {yaml_path}")
        return templates
        
    except KeyError as e:
        raise KeyError(f"Invalid template structure in {yaml_path}: {e}")
    except AttributeError as e:
        raise ValueError(f"Invalid unit class name in {yaml_path}: {e}")


# Load templates from YAML file
UNIT_TEMPLATES: Dict[UnitClass, ComponentTemplate] = _load_unit_templates()


def get_template(unit_class: UnitClass) -> ComponentTemplate:
    """Get the component template for a unit class.
    
    Args:
        unit_class: The unit class to get template for
        
    Returns:
        ComponentTemplate with initialization data
        
    Raises:
        KeyError: If unit_class is not recognized
    """
    if unit_class not in UNIT_TEMPLATES:
        raise KeyError(f"No template found for unit class: {unit_class}")
    
    return UNIT_TEMPLATES[unit_class]


def create_unit_entity(name: str, unit_class: UnitClass, team: "Team", x: int, y: int) -> "Entity":
    """Create a complete unit entity with all components from a template.
    
    Args:
        name: Display name for the unit
        unit_class: Unit class enum
        team: Team affiliation 
        x: Initial x position
        y: Initial y position
        
    Returns:
        Entity with all 5 core components configured according to class template
    """
    from ..core.components import Entity
    from ..core.game_enums import Team
    from .components import (
        ActorComponent, HealthComponent, MovementComponent, 
        CombatComponent, StatusComponent
    )
    
    # Get template for this unit class
    template = get_template(unit_class)
    
    # Create entity
    entity = Entity()
    
    # Add all 5 core components using template values
    entity.add_component(ActorComponent(entity, name, unit_class, team))
    entity.add_component(HealthComponent(entity, **template.health))
    entity.add_component(MovementComponent(entity, x, y, **template.movement))
    entity.add_component(CombatComponent(entity, **template.combat))
    entity.add_component(StatusComponent(entity, **template.status))
    
    return entity