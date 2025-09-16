"""Hidden intent system for tactical uncertainty.

This module implements the hidden intent system that creates tactical uncertainty
by concealing AI actions until they are revealed through time, distance, or
special abilities. This adds psychological tension and rewards scouting.

Key Features:
- Intent visibility levels (hidden, partial, full)
- Gradual revelation over time and distance
- Deception and misdirection capabilities
- Information gathering mechanics
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

from .data_structures import Vector2

if TYPE_CHECKING:
    from ..core.actions import Action
    from ..game.unit import Unit


class IntentVisibility(Enum):
    """Levels of intent visibility."""

    HIDDEN = auto()  # Completely hidden ("???")
    PARTIAL = auto()  # Partially revealed ("Preparing Attack")
    FULL = auto()  # Fully revealed ("Attack → Knight at (3,4)")


class RevealTrigger(Enum):
    """Triggers that can reveal hidden intents."""

    TIME_PASSED = auto()  # Revealed after time passes
    DISTANCE_CLOSE = auto()  # Revealed when observer gets close
    LINE_OF_SIGHT = auto()  # Revealed when in direct LoS
    SCOUTING_ABILITY = auto()  # Revealed by special abilities
    ACTION_COMMITMENT = auto()  # Revealed when action becomes locked in


@dataclass
class IntentInfo:
    """Information about a unit's intended action."""

    unit: "Unit"
    action: Optional["Action"] = None
    target: Optional[Vector2] = None

    # Visibility state
    visibility: IntentVisibility = IntentVisibility.HIDDEN
    reveal_time: Optional[int] = None  # Timeline time when it will be revealed
    reveal_distance: Optional[int] = None  # Distance at which it's revealed

    # Deception
    is_deception: bool = False
    real_action: Optional["Action"] = None
    real_target: Optional[object] = None

    # Descriptive text
    hidden_description: str = "???"
    partial_description: str = ""
    full_description: str = ""

    def get_description(
        self, observer_distance: Optional[int] = None, current_time: int = 0
    ) -> str:
        """Get the appropriate description based on visibility conditions.

        Args:
            observer_distance: Distance from observer to this unit
            current_time: Current timeline time

        Returns:
            Description string appropriate for current visibility
        """
        # Check if intent should be revealed due to conditions
        if self._should_reveal(observer_distance, current_time):
            if self.visibility == IntentVisibility.HIDDEN:
                self.visibility = IntentVisibility.PARTIAL

        # Return appropriate description
        if self.visibility == IntentVisibility.HIDDEN:
            return self.hidden_description
        elif self.visibility == IntentVisibility.PARTIAL:
            return self.partial_description or self._generate_partial_description()
        else:  # FULL
            return self.full_description or self._generate_full_description()

    def _should_reveal(
        self, observer_distance: Optional[int], current_time: int
    ) -> bool:
        """Check if intent should be revealed based on conditions."""
        # Time-based revelation
        if self.reveal_time and current_time >= self.reveal_time:
            return True

        # Distance-based revelation
        if (
            self.reveal_distance
            and observer_distance
            and observer_distance <= self.reveal_distance
        ):
            return True

        return False

    def _generate_partial_description(self) -> str:
        """Generate partial description if not set."""
        if not self.action:
            return "Preparing..."

        # Show action type but not specific target
        action_type = self._get_action_category()
        return f"Preparing {action_type}"

    def _generate_full_description(self) -> str:
        """Generate full description if not set."""
        if not self.action:
            return "Ready to Act"

        desc = self.action.name
        if self.target:
            desc += f" → ({self.target.x},{self.target.y})"

        return desc

    def _get_action_category(self) -> str:
        """Get general category of action for partial descriptions."""
        if not self.action:
            return "Action"

        name = self.action.name.lower()
        if any(word in name for word in ["attack", "strike", "slash", "stab"]):
            return "Attack"
        elif any(word in name for word in ["move", "advance", "retreat"]):
            return "Movement"
        elif any(word in name for word in ["heal", "cure", "restore"]):
            return "Healing"
        elif any(word in name for word in ["cast", "spell", "magic"]):
            return "Spell"
        else:
            return "Special Action"

    def reveal_fully(self) -> None:
        """Force full revelation of this intent."""
        self.visibility = IntentVisibility.FULL

    def reveal_partially(self) -> None:
        """Force partial revelation of this intent."""
        if self.visibility == IntentVisibility.HIDDEN:
            self.visibility = IntentVisibility.PARTIAL

    def conceal(self) -> None:
        """Hide this intent completely."""
        self.visibility = IntentVisibility.HIDDEN


class HiddenIntentManager:
    """Manages hidden intents and revelation mechanics."""

    def __init__(self):
        self.intents: dict[str, IntentInfo] = {}  # unit_id -> intent
        self.global_revelation_modifiers: dict[str, int] = {}

        # Configuration
        self.default_reveal_distance = 3
        self.default_reveal_delay = 2  # ticks

    def set_unit_intent(
        self,
        unit: "Unit",
        action: "Action",
        target: Optional[Vector2] = None,
        visibility: IntentVisibility = IntentVisibility.HIDDEN,
        custom_descriptions: Optional[dict[str, str]] = None,
    ) -> IntentInfo:
        """Set or update a unit's intent.

        Args:
            unit: Unit whose intent to set
            action: Intended action
            target: Target of the action
            visibility: Initial visibility level
            custom_descriptions: Custom description overrides

        Returns:
            Created IntentInfo object
        """
        intent = IntentInfo(
            unit=unit,
            action=action,
            target=target,
            visibility=visibility,
            reveal_distance=self.default_reveal_distance,
            reveal_time=None,  # Will be set by timeline manager
        )

        # Apply custom descriptions if provided
        if custom_descriptions:
            intent.hidden_description = custom_descriptions.get("hidden", "???")
            intent.partial_description = custom_descriptions.get("partial", "")
            intent.full_description = custom_descriptions.get("full", "")

        self.intents[unit.unit_id] = intent
        return intent

    def get_unit_intent(self, unit: "Unit") -> Optional[IntentInfo]:
        """Get a unit's current intent.

        Args:
            unit: Unit to get intent for

        Returns:
            IntentInfo if unit has an intent, None otherwise
        """
        return self.intents.get(unit.unit_id)

    def remove_unit_intent(self, unit: "Unit") -> bool:
        """Remove a unit's intent.

        Args:
            unit: Unit whose intent to remove

        Returns:
            True if intent was removed, False if no intent existed
        """
        return self.intents.pop(unit.unit_id, None) is not None

    def get_visible_intent_description(
        self, unit: "Unit", observer: Optional["Unit"] = None, current_time: int = 0
    ) -> str:
        """Get the visible description of a unit's intent.

        Args:
            unit: Unit whose intent to describe
            observer: Unit observing (affects distance calculations)
            current_time: Current timeline time

        Returns:
            Description string based on visibility conditions
        """
        intent = self.intents.get(unit.unit_id)
        if not intent:
            return "Ready to Act"

        # Calculate observer distance
        observer_distance = None
        if observer:
            observer_distance = abs(unit.position.x - observer.position.x) + abs(
                unit.position.y - observer.position.y
            )

        return intent.get_description(observer_distance, current_time)

    def create_deception(
        self,
        unit: "Unit",
        fake_action: "Action",
        real_action: "Action",
        fake_target: Optional[object] = None,
        real_target: Optional[object] = None,
    ) -> IntentInfo:
        """Create a deceptive intent that shows false information.

        Args:
            unit: Unit creating the deception
            fake_action: Action to show publicly
            real_action: Actual intended action
            fake_target: Target to show publicly
            real_target: Actual intended target

        Returns:
            Created deceptive IntentInfo
        """
        intent = IntentInfo(
            unit=unit,
            action=fake_action,
            target=fake_target,
            visibility=IntentVisibility.PARTIAL,  # Deceptions start partially visible
            is_deception=True,
            real_action=real_action,
            real_target=real_target,
        )

        self.intents[unit.unit_id] = intent
        return intent

    def reveal_deception(self, unit: "Unit") -> bool:
        """Reveal that a unit's intent was deceptive.

        Args:
            unit: Unit whose deception to reveal

        Returns:
            True if a deception was revealed
        """
        intent = self.intents.get(unit.unit_id)
        if not intent or not intent.is_deception:
            return False

        # Replace fake info with real info
        intent.action = intent.real_action
        intent.target = intent.real_target
        intent.is_deception = False
        intent.visibility = IntentVisibility.FULL

        return True

    def apply_scouting(
        self, scout: "Unit", target: "Unit", scouting_range: int = 5
    ) -> bool:
        """Apply scouting ability to reveal a target's intent.

        Args:
            scout: Unit doing the scouting
            target: Unit being scouted
            scouting_range: Maximum range for scouting

        Returns:
            True if intent was revealed
        """
        # Check range
        distance = abs(scout.position.x - target.position.x) + abs(
            scout.position.y - target.position.y
        )
        if distance > scouting_range:
            return False

        intent = self.intents.get(target.unit_id)
        if not intent:
            return False

        # Reveal intent (but don't reveal deceptions immediately)
        if not intent.is_deception:
            intent.reveal_fully()
        else:
            intent.reveal_partially()  # Just show it's deceptive

        return True

    def update_revelation_conditions(self, current_time: int) -> list[str]:
        """Update all intents based on revelation conditions.

        Args:
            current_time: Current timeline time

        Returns:
            List of unit IDs whose intents were revealed
        """
        revealed = []

        for unit_id, intent in self.intents.items():
            old_visibility = intent.visibility

            # Check time-based revelation
            if intent.reveal_time and current_time >= intent.reveal_time:
                intent.reveal_partially()

            # Track what was revealed
            if old_visibility != intent.visibility:
                revealed.append(unit_id)

        return revealed

    def get_all_visible_intents(
        self, observer: Optional["Unit"] = None, current_time: int = 0
    ) -> dict[str, str]:
        """Get all visible intents for UI display.

        Args:
            observer: Observing unit (affects distance calculations)
            current_time: Current timeline time

        Returns:
            Dictionary mapping unit_id to visible intent description
        """
        visible = {}

        for unit_id, intent in self.intents.items():
            description = self.get_visible_intent_description(
                intent.unit, observer, current_time
            )
            visible[unit_id] = description

        return visible

    def clear_all_intents(self) -> None:
        """Clear all stored intents."""
        self.intents.clear()

    def get_stats(self) -> dict[str, int]:
        """Get statistics about hidden intents.

        Returns:
            Dictionary with intent statistics
        """
        total = len(self.intents)
        hidden = sum(
            1 for i in self.intents.values() if i.visibility == IntentVisibility.HIDDEN
        )
        partial = sum(
            1 for i in self.intents.values() if i.visibility == IntentVisibility.PARTIAL
        )
        full = sum(
            1 for i in self.intents.values() if i.visibility == IntentVisibility.FULL
        )
        deceptions = sum(1 for i in self.intents.values() if i.is_deception)

        return {
            "total_intents": total,
            "hidden": hidden,
            "partial": partial,
            "full": full,
            "deceptions": deceptions,
        }


# ============== Helper Functions ==============


def create_movement_intent(unit: "Unit", destination: Vector2) -> IntentInfo:
    """Create a movement intent with appropriate descriptions.

    Args:
        unit: Unit that will move
        destination: Target coordinates

    Returns:
        IntentInfo configured for movement
    """
    return IntentInfo(
        unit=unit,
        action=None,  # Will be filled in with actual move action
        target=destination,
        visibility=IntentVisibility.HIDDEN,
        hidden_description="???",
        partial_description="Moving",
        full_description=f"Move → ({destination.y},{destination.x})",
    )


def create_attack_intent(
    unit: "Unit", target: "Unit", weapon_name: str = "Attack"
) -> IntentInfo:
    """Create an attack intent with appropriate descriptions.

    Args:
        unit: Attacking unit
        target: Target unit
        weapon_name: Name of attack/weapon

    Returns:
        IntentInfo configured for attack
    """
    return IntentInfo(
        unit=unit,
        action=None,  # Will be filled in with actual attack action
        target=target.position,
        visibility=IntentVisibility.HIDDEN,
        hidden_description="???",
        partial_description="Preparing Attack",
        full_description=f"{weapon_name} → {target.name}",
    )


def create_spell_intent(
    unit: "Unit", spell_name: str, target: Optional[Vector2] = None
) -> IntentInfo:
    """Create a spell casting intent with appropriate descriptions.

    Args:
        unit: Casting unit
        spell_name: Name of spell
        target: Target of spell (optional)

    Returns:
        IntentInfo configured for spell casting
    """
    target_desc = ""
    if target:
        target_desc = f" → ({target.x},{target.y})"

    return IntentInfo(
        unit=unit,
        action=None,
        target=target,
        visibility=IntentVisibility.HIDDEN,
        hidden_description="???",
        partial_description="Casting Spell",
        full_description=f"{spell_name}{target_desc}",
    )

