"""Unit class templates for component initialization.

This module defines how different unit classes should be configured with components.
Templates are loaded from YAML files (with JSON fallback) and converted to data structures
that specify initial values for each component based on the unit's class (Knight, Archer, etc.).
"""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

import yaml

from ...core.data import Vector2, UnitClass, AOEPattern
from ...core.entities import Entity
from ..ai.ai_behaviors import AIType, create_ai_behavior
from .components import (
    ActorComponent,
    AIComponent,
    CombatComponent,
    HealthComponent,
    InterruptComponent,
    MoraleComponent,
    MovementComponent,
    StatusComponent,
    WoundComponent,
)

if TYPE_CHECKING:
    from ...core.data.game_enums import Team


@dataclass
class ComponentTemplate:
    """Template for initializing components from unit class.

    Each field corresponds to a component and contains the initial
    values that should be passed to that component's constructor.
    """

    # HealthComponent initialization
    health: dict[str, int]

    # MovementComponent initialization
    movement: dict[str, int]

    # CombatComponent initialization
    combat: dict[str, Union[int, str]]

    # StatusComponent initialization
    status: dict[str, int]

    # AIComponent initialization
    ai: dict[str, str]


def _load_unit_templates() -> dict[UnitClass, ComponentTemplate]:
    """Load unit templates from YAML file.

    Returns:
        Dictionary mapping UnitClass enums to ComponentTemplate objects
    """
    # Get the project root directory (three levels up from this file)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    yaml_path = os.path.join(
        project_root, "assets", "data", "units", "unit_templates.yaml"
    )

    try:
        with open(yaml_path, "r") as f:
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
                status=template_data["status"],
                ai=template_data.get(
                    "ai", {"behavior": "AGGRESSIVE"}
                ),  # Default to aggressive
            )

        return templates

    except KeyError as e:
        raise KeyError(f"Invalid template structure in {yaml_path}: {e}")
    except AttributeError as e:
        raise ValueError(f"Invalid unit class name in {yaml_path}: {e}")


# Load templates from YAML file
UNIT_TEMPLATES: dict[UnitClass, ComponentTemplate] = _load_unit_templates()


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


def create_unit_entity(
    name: str, unit_class: UnitClass, team: "Team", position: Vector2
) -> "Entity":
    """Create a complete unit entity with all components from a template.

    Args:
        name: Display name for the unit
        unit_class: Unit class enum
        team: Team affiliation
        position: Initial position vector

    Returns:
        Entity with all components configured according to class template
    """
    # Get template for this unit class
    template = get_template(unit_class)

    # Create entity
    entity = Entity()

    # Add all 5 core components using template values
    entity.add_component(ActorComponent(entity, name, unit_class, team))
    entity.add_component(HealthComponent(entity, **template.health))
    entity.add_component(MovementComponent(entity, position, **template.movement))

    # For combat component, ensure proper types
    combat_params = template.combat.copy()
    entity.add_component(
        CombatComponent(
            entity,
            strength=int(combat_params["strength"]),
            defense=int(combat_params["defense"]),
            attack_range_min=int(combat_params["attack_range_min"]),
            attack_range_max=int(combat_params["attack_range_max"]),
            aoe_pattern=AOEPattern(combat_params.get("aoe_pattern", "single")),
        )
    )

    entity.add_component(StatusComponent(entity, **template.status))

    # Add interrupt component for tactical combat
    entity.add_component(InterruptComponent(entity))

    # Add morale component for grimdark psychology
    entity.add_component(MoraleComponent(entity))

    # Add wound component for persistent injuries
    entity.add_component(WoundComponent(entity))

    # Add AI component for behavior and decision-making
    ai_behavior_name = template.ai.get("behavior", "AGGRESSIVE")
    ai_type = getattr(AIType, ai_behavior_name)
    ai_behavior = create_ai_behavior(ai_type)
    entity.add_component(AIComponent(entity, ai_behavior))

    return entity

