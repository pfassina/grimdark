"""Action system for timeline-based combat.

This module defines the action class hierarchy that drives the timeline combat
system. Each action has a weight that determines how long until the unit's next
turn, creating tactical depth through time management.

Action Categories:
- Quick Actions (50-80 weight): Fast but weak effects
- Normal Actions (100 weight): Standard balanced actions
- Heavy Actions (150-200+ weight): Slow but powerful effects
- Prepared Actions (120-140 weight): Set up interrupts/reactions
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ...game.entities.unit import Unit
    from ...game.map import GameMap

from ..data import Vector2
from ..events.events import UnitAttacked


class ActionCategory(Enum):
    """Categories of actions based on their speed and power."""

    QUICK = auto()  # 50-80 weight: Fast, weak actions
    NORMAL = auto()  # 100 weight: Standard actions
    HEAVY = auto()  # 150-200+ weight: Slow, powerful actions
    PREPARED = auto()  # 120-140 weight: Set up interrupts


class ActionResult(Enum):
    """Results of action execution."""

    SUCCESS = auto()  # Action completed successfully
    FAILED = auto()  # Action failed (invalid target, etc.)
    CANCELLED = auto()  # Action was cancelled
    INTERRUPTED = auto()  # Action was interrupted by enemy
    REQUIRES_TARGET = auto()  # Action needs target selection
    REQUIRES_INPUT = auto()  # Action needs additional input
    REQUIRES_CONFIRMATION = auto()  # Action requires user confirmation (e.g., friendly fire)


@dataclass
class ActionValidation:
    """Result of action validation."""

    is_valid: bool
    reason: str = ""
    friendly_units: Optional[list["Unit"]] = None

    @classmethod
    def valid(cls) -> "ActionValidation":
        """Create a valid result."""
        return cls(is_valid=True)

    @classmethod
    def invalid(cls, reason: str) -> "ActionValidation":
        """Create an invalid result with reason."""
        return cls(is_valid=False, reason=reason)

    @classmethod
    def friendly_fire(cls, friendly_units: list["Unit"]) -> "ActionValidation":
        """Create a friendly fire validation result."""
        return cls(is_valid=False, reason="friendly_fire", friendly_units=friendly_units)


class Action(ABC):
    """Base class for all actions in the timeline combat system.

    Actions define what a unit can do and how it affects the timeline. Each
    action has a weight that determines the time cost, and methods for
    validation and execution.
    """

    def __init__(self, name: str, weight: int, category: ActionCategory):
        self.name = name
        self.weight = weight  # Time cost for this action
        self.category = category
        self.is_interruptible = True  # Can this action be interrupted?
        self.requires_line_of_sight = False
        self.max_range = 1  # Maximum range in tiles

    @abstractmethod
    def validate(
        self, actor: "Unit", game_map: "GameMap", target: Optional[Any] = None
    ) -> ActionValidation:
        """Validate if this action can be performed.

        Args:
            actor: Unit attempting the action
            game_map: Current game map
            target: Optional target (position, unit, etc.)

        Returns:
            ActionValidation result
        """
        pass

    @abstractmethod
    def execute(
        self,
        actor: "Unit",
        game_map: "GameMap",
        target: Optional[Any] = None,
        event_emitter: Optional[Callable] = None,
    ) -> ActionResult:
        """Execute the action.

        Args:
            actor: Unit performing the action
            game_map: Current game map
            target: Optional target (position, unit, etc.)
            event_emitter: Optional event emitter for damage events

        Returns:
            Result of the action execution
        """
        pass

    def get_weight_modifier(self, actor: "Unit") -> int:
        """Get any weight modifications based on actor state.

        Args:
            actor: Unit performing the action

        Returns:
            Weight modifier (added to base weight)
        """
        modifier = 0

        # Example modifiers (can be extended)
        # if hasattr(actor, 'status') and actor.status.is_wounded:
        #     modifier += 20  # Wounded units act slower

        return modifier

    def get_effective_weight(self, actor: "Unit") -> int:
        """Get the total effective weight for this action.

        Args:
            actor: Unit performing the action

        Returns:
            Total weight including modifiers
        """
        return self.weight + self.get_weight_modifier(actor)

    def can_interrupt(self, trigger_condition: str) -> bool:
        """Check if this action can be used as an interrupt.

        Args:
            trigger_condition: The trigger that might activate this interrupt

        Returns:
            True if this action can interrupt on the given condition
        """
        return False  # Most actions can't be used as interrupts

    def get_description(self) -> str:
        """Get human-readable description of the action."""
        return self.name

    def get_intent_description(self, hidden: bool = False) -> str:
        """Get description for timeline display.

        Args:
            hidden: Whether to show hidden/partial information

        Returns:
            Description for timeline UI
        """
        if hidden:
            return "???"
        return self.get_description()


# ============== Base Attack Action ==============


class AttackAction(Action):
    """Base class for all attack actions with unified AOE system."""
    
    def __init__(self, name: str, weight: int, category: ActionCategory, 
                 damage_multiplier: float, max_range: int = 1):
        super().__init__(name, weight, category)
        self.damage_multiplier = damage_multiplier
        self.requires_line_of_sight = True
        self.max_range = max_range

    def validate(
        self, actor: "Unit", game_map: "GameMap", target: Optional[Any] = None
    ) -> ActionValidation:
        if target is None:
            return ActionValidation.invalid("No target selected")

        # All attacks use Vector2 position as target (center of AOE)
        if not isinstance(target, Vector2):
            return ActionValidation.invalid("Target must be a position (Vector2)")
            
        # Validate position is in range
        distance = actor.position.manhattan_distance_to(target)
        if distance > self.max_range:
            return ActionValidation.invalid(
                f"Target position out of range (max {self.max_range})"
            )
        
        # Validate position is on the map
        if not game_map.is_valid_position(target):
            return ActionValidation.invalid("Invalid target position")
        
        # Check for targets in AOE and detect friendly fire
        aoe_pattern = actor.combat.aoe_pattern
        aoe_tiles = game_map.calculate_aoe_tiles(target, aoe_pattern)
        targets_in_aoe = game_map.get_units_in_positions(aoe_tiles)
        valid_targets = [t for t in targets_in_aoe if t.unit_id != actor.unit_id]
        
        if not valid_targets:
            return ActionValidation.invalid("No valid targets in area")
        
        # Check for friendly fire
        friendly_targets = [t for t in valid_targets if t.team == actor.team]
        if friendly_targets:
            return ActionValidation.friendly_fire(friendly_targets)
            
        return ActionValidation.valid()

    def execute(
        self,
        actor: "Unit",
        game_map: "GameMap",
        target: Optional[Any] = None,
        event_emitter: Optional[Callable] = None,
    ) -> ActionResult:
        # Validate but allow friendly fire (it should have been confirmed already)
        validation = self.validate(actor, game_map, target)
        if not validation.is_valid and validation.reason != "friendly_fire":
            return ActionResult.FAILED

        assert target is not None  # validate() ensures this
        assert isinstance(target, Vector2)  # validate() ensures this

        # CRITICAL: Always use the event system for proper combat resolution
        if not event_emitter:
            raise RuntimeError(f"{self.name} requires event system - no backward compatibility")

        # Standard damage calculation
        base_damage = actor.combat.strength

        # All attacks are AOE - get pattern from actor's combat component
        aoe_pattern = actor.combat.aoe_pattern
        
        # Calculate AOE tiles based on center position and pattern
        aoe_tiles = game_map.calculate_aoe_tiles(target, aoe_pattern)
        
        # Find all units in AOE area
        targets_in_aoe = game_map.get_units_in_positions(aoe_tiles)
        
        # Filter out the attacker and build target list
        valid_targets = [t for t in targets_in_aoe if t.unit_id != actor.unit_id]
        
        if not valid_targets:
            return ActionResult.FAILED  # No valid targets in AOE
        
        # Emit UnitAttacked event for each target
        for target_unit in valid_targets:
            attack_event = UnitAttacked(
                timeline_time=0,  # Timeline manager will fill in correct timeline_time
                attacker=actor,
                target=target_unit,
                base_damage=base_damage,
                damage_multiplier=self.damage_multiplier,  # Use instance's damage multiplier
            )
            event_emitter(attack_event)
        
        return ActionResult.SUCCESS


# ============== Quick Actions (50-80 weight) ==============


class QuickStrike(AttackAction):
    """Fast, light attack with minimal damage."""

    def __init__(self):
        super().__init__("Quick Strike", 70, ActionCategory.QUICK, 0.7)


class QuickMove(Action):
    """Fast movement with limited distance."""

    def __init__(self):
        super().__init__("Quick Move", 60, ActionCategory.QUICK)
        self.max_range = 2  # Can move up to 2 tiles

    def validate(
        self, actor: "Unit", game_map: "GameMap", target: Optional[Any] = None
    ) -> ActionValidation:
        if target is None:
            return ActionValidation.invalid("No destination selected")

        # Assume target is a Vector2 position
        if not isinstance(target, Vector2):
            return ActionValidation.invalid("Invalid destination")

        # Check range
        distance = actor.position.manhattan_distance_to(target)
        if distance > self.max_range:
            return ActionValidation.invalid(f"Too far (max {self.max_range} tiles)")

        # Check if destination is valid and walkable
        if not game_map.is_valid_position(target):
            return ActionValidation.invalid("Invalid position")

        if game_map.is_position_blocked(target, actor.team):
            return ActionValidation.invalid("Position blocked")

        return ActionValidation.valid()

    def execute(
        self,
        actor: "Unit",
        game_map: "GameMap",
        target: Optional[Any] = None,
        event_emitter: Optional[Callable] = None,
    ) -> ActionResult:
        if not self.validate(actor, game_map, target).is_valid:
            return ActionResult.FAILED

        # Move the unit - target is guaranteed to be Vector2 by validation
        if isinstance(target, Vector2):
            if not game_map.move_unit(actor.unit_id, target):
                return ActionResult.FAILED

        return ActionResult.SUCCESS


# ============== Normal Actions (100 weight) ==============


class StandardAttack(AttackAction):
    """Standard melee or ranged attack."""

    def __init__(self):
        super().__init__("Attack", 100, ActionCategory.NORMAL, 1.0)


class StandardMove(Action):
    """Standard movement action."""

    def __init__(self):
        super().__init__("Move", 100, ActionCategory.NORMAL)
        self.max_range = 3  # Standard movement range

    def validate(
        self, actor: "Unit", game_map: "GameMap", target: Optional[Any] = None
    ) -> ActionValidation:
        if target is None:
            return ActionValidation.invalid("No destination selected")

        if not isinstance(target, Vector2):
            return ActionValidation.invalid("Invalid destination")

        # Check range based on unit's movement
        max_move = getattr(actor.movement, "movement_points", 3)
        distance = actor.position.manhattan_distance_to(target)
        if distance > max_move:
            return ActionValidation.invalid(f"Too far (max {max_move} tiles)")

        if not game_map.is_valid_position(target):
            return ActionValidation.invalid("Invalid position")

        if game_map.is_position_blocked(target, actor.team):
            return ActionValidation.invalid("Position blocked")

        return ActionValidation.valid()

    def execute(
        self,
        actor: "Unit",
        game_map: "GameMap",
        target: Optional[Any] = None,
        event_emitter: Optional[Callable] = None,
    ) -> ActionResult:
        if not self.validate(actor, game_map, target).is_valid:
            return ActionResult.FAILED

        # Move the unit - target is guaranteed to be Vector2 by validation
        if isinstance(target, Vector2):
            if not game_map.move_unit(actor.unit_id, target):
                return ActionResult.FAILED

        return ActionResult.SUCCESS


class Wait(Action):
    """Wait action - unit skips turn but recovers faster."""

    def __init__(self):
        super().__init__("Wait", 100, ActionCategory.NORMAL)

    def validate(
        self, actor: "Unit", game_map: "GameMap", target: Optional[Any] = None
    ) -> ActionValidation:
        # Wait is always valid if unit is alive
        if not actor.is_alive:
            return ActionValidation.invalid("Unit is not alive")
        return ActionValidation.valid()

    def execute(
        self,
        actor: "Unit",
        game_map: "GameMap",
        target: Optional[Any] = None,
        event_emitter: Optional[Callable] = None,
    ) -> ActionResult:
        # Wait action does nothing but allows unit to recover
        return ActionResult.SUCCESS


# ============== Heavy Actions (150-200+ weight) ==============


class PowerAttack(AttackAction):
    """Devastating attack that takes a long time to recover from."""

    def __init__(self):
        super().__init__("Power Attack", 180, ActionCategory.HEAVY, 1.5)


class ChargeAttack(Action):
    """Move and attack in one action with high damage but long recovery."""

    def __init__(self):
        super().__init__("Charge", 170, ActionCategory.HEAVY)
        self.requires_line_of_sight = True
        self.max_range = 4  # Can charge up to 4 tiles

    def validate(
        self, actor: "Unit", game_map: "GameMap", target: Optional[Any] = None
    ) -> ActionValidation:
        if target is None:
            return ActionValidation.invalid("No target selected")

        if not hasattr(target, "is_alive"):
            return ActionValidation.invalid("Invalid target")

        if not target.is_alive:
            return ActionValidation.invalid("Target is dead")

        # Check range
        distance = actor.position.manhattan_distance_to(target.position)
        if distance > self.max_range or distance < 2:
            return ActionValidation.invalid("Invalid charge range (2-4 tiles)")

        # TODO: Check if path is clear for charging

        return ActionValidation.valid()

    def execute(
        self,
        actor: "Unit",
        game_map: "GameMap",
        target: Optional[Any] = None,
        event_emitter: Optional[Callable] = None,
    ) -> ActionResult:
        if not self.validate(actor, game_map, target).is_valid:
            return ActionResult.FAILED

        assert target is not None  # validate() ensures this

        # Move adjacent to target
        # TODO: Implement proper pathfinding for charge

        # Heavy damage with charge bonus
        base_damage = actor.combat.strength

        if event_emitter and hasattr(target, "unit_id"):
            # Emit UnitAttacked event for proper combat resolution
            attack_event = UnitAttacked(
                timeline_time=0,  # Timeline manager will fill in correct time
                attacker=actor,  # actor is already a Unit
                target=target,
                base_damage=base_damage,
                damage_multiplier=1.3,  # 130% damage
            )
            event_emitter(attack_event)
        else:
            # Fallback to direct damage if no event system available
            if hasattr(target, "take_damage"):
                damage = int(base_damage * 1.3)
                target.take_damage(damage)

        return ActionResult.SUCCESS


# ============== Prepared Actions (120-140 weight) ==============


class OverwatchAction(Action):
    """Prepare to attack the first enemy that moves in range."""

    def __init__(self):
        super().__init__("Overwatch", 130, ActionCategory.PREPARED)
        self.max_range = 3  # Watching range

    def validate(
        self, actor: "Unit", game_map: "GameMap", target: Optional[Any] = None
    ) -> ActionValidation:
        # Overwatch can always be activated if unit isn't already preparing something
        return ActionValidation.valid()

    def execute(
        self,
        actor: "Unit",
        game_map: "GameMap",
        target: Optional[Any] = None,
        event_emitter: Optional[Callable] = None,
    ) -> ActionResult:
        # Set the unit's prepared action
        # This would integrate with the interrupt system
        return ActionResult.SUCCESS

    def can_interrupt(self, trigger_condition: str) -> bool:
        """Overwatch can interrupt on movement."""
        return trigger_condition == "enemy_movement_in_range"


class ShieldWall(Action):
    """Prepare defensive stance to block incoming attacks."""

    def __init__(self):
        super().__init__("Shield Wall", 125, ActionCategory.PREPARED)

    def validate(
        self, actor: "Unit", game_map: "GameMap", target: Optional[Any] = None
    ) -> ActionValidation:
        # Check if unit has a shield or defensive capability
        return ActionValidation.valid()

    def execute(
        self,
        actor: "Unit",
        game_map: "GameMap",
        target: Optional[Any] = None,
        event_emitter: Optional[Callable] = None,
    ) -> ActionResult:
        # Set defensive prepared action
        return ActionResult.SUCCESS

    def can_interrupt(self, trigger_condition: str) -> bool:
        """Shield wall can interrupt incoming attacks."""
        return trigger_condition == "incoming_attack"


# ============== Action Factory ==============


def get_available_actions(unit: "Unit") -> list[Action]:
    """Get list of actions available to a unit.

    Args:
        unit: The unit to get actions for

    Returns:
        List of available actions based on unit class and state
    """
    actions = []

    # Basic actions available to all units
    actions.extend(
        [
            QuickStrike(),
            QuickMove(),
            StandardAttack(),
            StandardMove(),
        ]
    )

    # Class-specific or conditional actions
    unit_class = getattr(unit, "unit_class", None)

    # Warriors get power attacks and charges
    if unit_class and unit_class.name in ["KNIGHT", "WARRIOR"]:
        actions.extend(
            [
                PowerAttack(),
                ChargeAttack(),
                ShieldWall(),
            ]
        )

    # Ranged units get overwatch
    if unit_class and unit_class.name in ["ARCHER", "MAGE"]:
        actions.append(OverwatchAction())

    return actions


def create_action_by_name(action_name: str) -> Action:
    """Create an action instance by name.

    Args:
        action_name: Name of the action to create

    Returns:
        Action instance

    Raises:
        ValueError: If action_name is not recognized
    """
    action_map = {
        "Quick Strike": QuickStrike(),
        "Quick Move": QuickMove(),
        "Attack": StandardAttack(),
        "Move": StandardMove(),
        "Wait": Wait(),
        "Power Attack": PowerAttack(),
        "Charge": ChargeAttack(),
        "Overwatch": OverwatchAction(),
        "Shield Wall": ShieldWall(),
    }

    action = action_map.get(action_name)
    if action is None:
        raise ValueError(f"Unknown action name: {action_name}")
    return action

