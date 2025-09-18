"""Interrupt and prepared action system for tactical combat.

This module implements the interrupt system that allows units to prepare actions
that trigger on specific conditions. This creates tactical depth where players
can set up defensive reactions and ambushes.

Key Features:
- Prepared actions that wait for triggers
- Interrupt chains and resolution order
- Trigger condition framework
- Action pre-emption and timing
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ...core.engine.actions import Action
    from ..map import GameMap
    from ..entities.unit import Unit

from ...core.engine.actions import ActionResult
from ...core.data.game_enums import Team


class TriggerType(Enum):
    """Types of triggers that can activate interrupts."""

    ENEMY_MOVEMENT = auto()  # Enemy moves within range/sight
    INCOMING_ATTACK = auto()  # Unit is being attacked
    ALLY_DAMAGE = auto()  # Allied unit takes damage
    ENEMY_CASTING = auto()  # Enemy begins casting/channeling
    TURN_START = auto()  # At start of unit's turn
    TURN_END = auto()  # At end of unit's turn
    HP_THRESHOLD = auto()  # HP drops below threshold
    POSITION_ENTERED = auto()  # Someone enters marked position


@dataclass
class TriggerCondition:
    """Defines when an interrupt should activate."""

    trigger_type: TriggerType

    # Additional parameters based on trigger type
    range_limit: Optional[int] = None  # For movement/sight triggers
    hp_threshold: Optional[int] = None  # For health triggers
    target_position: Optional[tuple[int, int]] = None  # For position triggers
    target_team: Optional[Team] = None  # Filter by team

    def matches(self, event_type: TriggerType, **event_data) -> bool:
        """Check if this condition matches the given event.

        Args:
            event_type: The type of event that occurred
            **event_data: Additional event data for matching

        Returns:
            True if the condition is satisfied
        """
        if self.trigger_type != event_type:
            return False

        # Additional matching based on trigger type
        if self.trigger_type == TriggerType.ENEMY_MOVEMENT:
            if self.range_limit is not None:
                distance = event_data.get("distance", 0)
                if distance > self.range_limit:
                    return False

        elif self.trigger_type == TriggerType.HP_THRESHOLD:
            if self.hp_threshold is not None:
                current_hp = event_data.get("current_hp", 0)
                if current_hp >= self.hp_threshold:
                    return False

        elif self.trigger_type == TriggerType.POSITION_ENTERED:
            if self.target_position is not None:
                position = event_data.get("position")
                if position != self.target_position:
                    return False

        # Team filtering
        if self.target_team is not None:
            event_team = event_data.get("team")
            if event_team != self.target_team:
                return False

        return True


@dataclass
class PreparedAction:
    """A prepared action waiting for its trigger condition."""

    action: "Action"
    trigger: TriggerCondition
    owner: "Unit"
    target: Optional[Any] = None
    priority: int = 0  # Higher priority interrupts resolve first
    uses_remaining: int = 1  # How many times this can trigger

    # Timeline integration
    timeline_entry_id: Optional[int] = None

    def can_execute(self, game_map: "GameMap") -> bool:
        """Check if this prepared action can currently execute."""
        if self.uses_remaining <= 0:
            return False

        if not self.owner.is_alive:
            return False

        # Validate the action can still be performed
        validation = self.action.validate(self.owner, game_map, self.target)
        return validation.is_valid

    def consume_use(self) -> None:
        """Consume one use of this prepared action."""
        if self.uses_remaining > 0:
            self.uses_remaining -= 1


class InterruptManager:
    """Manages interrupt resolution and prepared actions."""

    def __init__(self):
        self.prepared_actions: list[PreparedAction] = []
        self.interrupt_stack: list[PreparedAction] = []  # Actions ready to execute

        # Callbacks for main game coordination
        self.on_action_executed: Optional[Callable] = None

    def add_prepared_action(self, prepared: PreparedAction) -> None:
        """Add a prepared action to the system.

        Args:
            prepared: The prepared action to add
        """
        self.prepared_actions.append(prepared)

    def remove_prepared_actions(self, unit: "Unit") -> int:
        """Remove all prepared actions for a unit.

        Args:
            unit: Unit whose prepared actions to remove

        Returns:
            Number of actions removed
        """
        original_count = len(self.prepared_actions)
        self.prepared_actions = [p for p in self.prepared_actions if p.owner != unit]
        removed = original_count - len(self.prepared_actions)

        # Also remove from interrupt stack
        self.interrupt_stack = [p for p in self.interrupt_stack if p.owner != unit]

        return removed

    def check_triggers(
        self, event_type: TriggerType, **event_data
    ) -> list[PreparedAction]:
        """Check if any prepared actions are triggered by an event.

        Args:
            event_type: The type of event that occurred
            **event_data: Additional event data

        Returns:
            List of triggered prepared actions, sorted by priority
        """
        triggered = []

        for prepared in self.prepared_actions[
            :
        ]:  # Copy list to avoid modification issues
            if prepared.trigger.matches(event_type, **event_data):
                triggered.append(prepared)

        # Sort by priority (highest first) then by owner speed for tiebreaking
        triggered.sort(key=lambda p: (-p.priority, -getattr(p.owner, "speed", 100)))

        return triggered

    def queue_interrupts(
        self, triggered_actions: list[PreparedAction], game_map: "GameMap"
    ) -> None:
        """Queue triggered actions for execution.

        Args:
            triggered_actions: List of prepared actions that were triggered
            game_map: Game map for action validation
        """
        for prepared in triggered_actions:
            if prepared.can_execute(game_map):
                self.interrupt_stack.append(prepared)

    def execute_next_interrupt(self, game_map: "GameMap") -> Optional[ActionResult]:
        """Execute the next interrupt in the stack.

        Args:
            game_map: Current game map

        Returns:
            Result of the interrupt execution or None if no interrupts
        """
        if not self.interrupt_stack:
            return None

        # Get the highest priority interrupt
        interrupt = self.interrupt_stack.pop(0)

        # Double-check it can still execute
        if not interrupt.can_execute(game_map):
            return ActionResult.FAILED

        # Execute the interrupt
        result = interrupt.action.execute(interrupt.owner, game_map, interrupt.target)

        # Consume a use
        interrupt.consume_use()

        # Remove if no uses left
        if interrupt.uses_remaining <= 0:
            self.prepared_actions = [p for p in self.prepared_actions if p != interrupt]

        # Notify callback
        if self.on_action_executed:
            self.on_action_executed(interrupt.owner, interrupt.action, result)

        return result

    def has_pending_interrupts(self) -> bool:
        """Check if there are interrupts waiting to execute."""
        return len(self.interrupt_stack) > 0

    def resolve_interrupt_chain(self, game_map: "GameMap") -> list[ActionResult]:
        """Resolve a complete chain of interrupts.

        Args:
            game_map: Current game map

        Returns:
            List of results from all executed interrupts
        """
        results = []

        # Execute all queued interrupts
        while self.has_pending_interrupts():
            result = self.execute_next_interrupt(game_map)
            if result is not None:
                results.append(result)

                # Check if this interrupt triggered more interrupts
                # (This could lead to interrupt chains)
                # For now, we'll keep it simple and not chain

        return results

    def get_prepared_actions_for_unit(self, unit: "Unit") -> list[PreparedAction]:
        """Get all prepared actions for a specific unit.

        Args:
            unit: Unit to get prepared actions for

        Returns:
            List of prepared actions owned by the unit
        """
        return [p for p in self.prepared_actions if p.owner == unit]

    def get_interrupt_summary(self) -> dict[str, Any]:
        """Get summary information about current interrupt state.

        Returns:
            Dictionary with interrupt statistics and info
        """
        return {
            "total_prepared": len(self.prepared_actions),
            "pending_interrupts": len(self.interrupt_stack),
            "prepared_by_unit": {
                p.owner.name: p.action.name for p in self.prepared_actions
            },
            "interrupt_queue": [
                f"{p.owner.name}: {p.action.name}" for p in self.interrupt_stack
            ],
        }


# ============== Interrupt Integration Functions ==============


def create_overwatch_interrupt(
    unit: "Unit", action: "Action", watch_range: int = 3
) -> PreparedAction:
    """Create an overwatch interrupt that triggers on enemy movement.

    Args:
        unit: Unit setting up overwatch
        action: Action to execute when triggered
        watch_range: Range to watch for movement

    Returns:
        Prepared action for overwatch
    """
    trigger = TriggerCondition(
        trigger_type=TriggerType.ENEMY_MOVEMENT,
        range_limit=watch_range,
        target_team=Team.ENEMY,
    )

    return PreparedAction(
        action=action,
        trigger=trigger,
        owner=unit,
        priority=10,  # High priority for reactive actions
        uses_remaining=1,
    )


def create_shield_wall_interrupt(unit: "Unit", action: "Action") -> PreparedAction:
    """Create a shield wall interrupt that triggers on incoming attacks.

    Args:
        unit: Unit setting up shield wall
        action: Defensive action to execute

    Returns:
        Prepared action for shield wall
    """
    trigger = TriggerCondition(
        trigger_type=TriggerType.INCOMING_ATTACK, target_team=Team.ENEMY
    )

    return PreparedAction(
        action=action,
        trigger=trigger,
        owner=unit,
        target=unit,  # Self-targeted defensive action
        priority=15,  # Very high priority for defense
        uses_remaining=1,
    )


def create_ambush_interrupt(
    unit: "Unit", action: "Action", position: tuple[int, int]
) -> PreparedAction:
    """Create an ambush interrupt that triggers when someone enters a position.

    Args:
        unit: Unit setting up ambush
        action: Attack action to execute
        position: Position to watch (x, y coordinates)

    Returns:
        Prepared action for ambush
    """
    trigger = TriggerCondition(
        trigger_type=TriggerType.POSITION_ENTERED,
        target_position=position,
        target_team=Team.ENEMY,
    )

    return PreparedAction(
        action=action,
        trigger=trigger,
        owner=unit,
        priority=8,  # Medium-high priority for ambushes
        uses_remaining=1,
    )


def create_heal_interrupt(
    unit: "Unit", action: "Action", ally: "Unit", hp_threshold: int
) -> PreparedAction:
    """Create a healing interrupt that triggers when an ally's HP drops low.

    Args:
        unit: Unit providing healing
        action: Healing action to execute
        ally: Allied unit to monitor
        hp_threshold: HP threshold to trigger at

    Returns:
        Prepared action for emergency healing
    """
    trigger = TriggerCondition(
        trigger_type=TriggerType.HP_THRESHOLD,
        hp_threshold=hp_threshold,
        target_team=Team.PLAYER,
    )

    return PreparedAction(
        action=action,
        trigger=trigger,
        owner=unit,
        target=ally,
        priority=20,  # Highest priority for life-saving actions
        uses_remaining=1,
    )

