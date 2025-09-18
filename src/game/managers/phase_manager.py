"""
Phase Management System with Event-Driven State Machine.

This module implements a centralized phase management system that handles both
GamePhase and BattlePhase transitions based on events, following a state machine
pattern. This ensures consistent phase transitions and eliminates direct phase
assignments scattered throughout the codebase.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from ...core.events.event_manager import EventManager
    from ...core.engine.game_state import GameState

from ...core.events.events import (
    BattlePhaseChanged,
    EventType,
    GameEvent,
    GamePhaseChanged,
    LogMessage,
)
from ...core.engine.game_state import BattlePhase, GamePhase
from ...core.data.data_structures import VectorArray


@dataclass
class GamePhaseTransitionRule:
    """Defines a game phase transition rule."""

    from_phase: GamePhase
    event_type: EventType
    to_phase: GamePhase
    description: str

    def matches(self, current_phase: GamePhase, event_type: EventType) -> bool:
        """Check if this rule matches the current conditions."""
        return self.from_phase == current_phase and self.event_type == event_type


@dataclass
class BattlePhaseTransitionRule:
    """Defines a battle phase transition rule."""

    from_phase: BattlePhase
    event_type: EventType
    to_phase: BattlePhase
    description: str

    def matches(self, current_phase: BattlePhase, event_type: EventType) -> bool:
        """Check if this rule matches the current conditions."""
        return self.from_phase == current_phase and self.event_type == event_type


class PhaseManager:
    """Centralized phase management with event-driven state machine.

    This manager listens to events and automatically transitions between
    GamePhase and BattlePhase states according to predefined rules.
    All phase transitions are centralized here, eliminating the need for
    managers to directly modify phase state.
    """

    def __init__(self, game_state: "GameState", event_manager: "EventManager"):
        self.state = game_state
        self.event_manager = event_manager

        # Transition rules
        self.game_phase_rules: List[GamePhaseTransitionRule] = []
        self.battle_phase_rules: List[BattlePhaseTransitionRule] = []

        # Set up transition rules
        self._setup_game_phase_transitions()
        self._setup_battle_phase_transitions()

        # Subscribe to relevant events
        self._subscribe_to_events()

    def _emit_log(
        self, message: str, category: str = "SYSTEM", level: str = "DEBUG"
    ) -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=self.state.battle.current_turn if self.state.battle else 0,
                message=message,
                category=category,
                level=level,
                source="PhaseManager",
            ),
            source="PhaseManager",
        )

    def _setup_game_phase_transitions(self) -> None:
        """Define GamePhase transition rules."""
        self.game_phase_rules = [
            GamePhaseTransitionRule(
                from_phase=GamePhase.MAIN_MENU,
                event_type=EventType.SCENARIO_LOADED,
                to_phase=GamePhase.BATTLE,
                description="Start battle when scenario is loaded from main menu",
            ),
            GamePhaseTransitionRule(
                from_phase=GamePhase.BATTLE,
                event_type=EventType.GAME_ENDED,
                to_phase=GamePhase.GAME_OVER,
                description="End game when battle concludes",
            ),
        ]

    def _setup_battle_phase_transitions(self) -> None:
        """Define BattlePhase transition rules."""
        self.battle_phase_rules = [
            # Timeline processing flows
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.TIMELINE_PROCESSING,
                event_type=EventType.UNIT_TURN_STARTED,
                to_phase=BattlePhase.UNIT_MOVING,
                description="Begin unit movement when their turn starts",
            ),
            # Unit movement flows
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.UNIT_MOVING,
                event_type=EventType.UNIT_MOVED,
                to_phase=BattlePhase.UNIT_ACTION_SELECTION,
                description="Allow action selection after unit movement",
            ),
            # Action selection flows
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.UNIT_ACTION_SELECTION,
                event_type=EventType.ACTION_SELECTED,
                to_phase=BattlePhase.ACTION_TARGETING,
                description="Begin targeting after action is selected",
            ),
            # Quick action flows (skip action selection menu)
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.UNIT_SELECTION,
                event_type=EventType.ACTION_SELECTED,
                to_phase=BattlePhase.ACTION_TARGETING,
                description="Quick attack from unit selection",
            ),
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.UNIT_MOVING,
                event_type=EventType.ACTION_SELECTED,
                to_phase=BattlePhase.ACTION_TARGETING,
                description="Quick attack from movement phase",
            ),
            # Action execution flows
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.ACTION_TARGETING,
                event_type=EventType.ACTION_EXECUTED,
                to_phase=BattlePhase.TIMELINE_PROCESSING,
                description="Return to timeline processing after action execution",
            ),
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.ACTION_EXECUTION,
                event_type=EventType.ACTION_EXECUTED,
                to_phase=BattlePhase.TIMELINE_PROCESSING,
                description="Return to timeline processing after action execution",
            ),
            # Quick wait flows (skip everything, go directly to timeline processing)
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.UNIT_SELECTION,
                event_type=EventType.ACTION_EXECUTED,
                to_phase=BattlePhase.TIMELINE_PROCESSING,
                description="Quick wait from unit selection",
            ),
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.UNIT_MOVING,
                event_type=EventType.ACTION_EXECUTED,
                to_phase=BattlePhase.TIMELINE_PROCESSING,
                description="Quick wait from movement phase",
            ),
            # Turn completion flows
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.UNIT_MOVING,
                event_type=EventType.UNIT_TURN_ENDED,
                to_phase=BattlePhase.TIMELINE_PROCESSING,
                description="End turn during movement phase",
            ),
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.UNIT_ACTION_SELECTION,
                event_type=EventType.UNIT_TURN_ENDED,
                to_phase=BattlePhase.TIMELINE_PROCESSING,
                description="End turn during action selection",
            ),
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.ACTION_TARGETING,
                event_type=EventType.UNIT_TURN_ENDED,
                to_phase=BattlePhase.TIMELINE_PROCESSING,
                description="End turn during targeting phase",
            ),
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.ACTION_EXECUTION,
                event_type=EventType.UNIT_TURN_ENDED,
                to_phase=BattlePhase.TIMELINE_PROCESSING,
                description="End turn during action execution",
            ),
            # Timeline continues processing
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.TIMELINE_PROCESSING,
                event_type=EventType.TIMELINE_PROCESSED,
                to_phase=BattlePhase.TIMELINE_PROCESSING,
                description="Continue timeline processing after each processing cycle",
            ),
            # Cancel transition rules
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.ACTION_TARGETING,
                event_type=EventType.ACTION_CANCELED,
                to_phase=BattlePhase.UNIT_ACTION_SELECTION,
                description="Cancel action targeting returns to action selection",
            ),
            BattlePhaseTransitionRule(
                from_phase=BattlePhase.UNIT_ACTION_SELECTION,
                event_type=EventType.MOVEMENT_CANCELED,
                to_phase=BattlePhase.UNIT_MOVING,
                description="Cancel action selection returns to movement phase",
            ),
        ]

    def _subscribe_to_events(self) -> None:
        """Subscribe to events that can trigger phase transitions."""
        # Game phase events
        self.event_manager.subscribe(
            EventType.SCENARIO_LOADED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.scenario_loaded",
        )
        self.event_manager.subscribe(
            EventType.GAME_ENDED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.game_ended",
        )

        # Battle phase events
        self.event_manager.subscribe(
            EventType.UNIT_TURN_STARTED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.unit_turn_started",
        )
        self.event_manager.subscribe(
            EventType.UNIT_TURN_ENDED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.unit_turn_ended",
        )
        self.event_manager.subscribe(
            EventType.UNIT_MOVED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.unit_moved",
        )
        self.event_manager.subscribe(
            EventType.ACTION_SELECTED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.action_selected",
        )
        self.event_manager.subscribe(
            EventType.ACTION_EXECUTED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.action_executed",
        )
        self.event_manager.subscribe(
            EventType.ACTION_CANCELED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.action_canceled",
        )
        self.event_manager.subscribe(
            EventType.MOVEMENT_CANCELED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.movement_canceled",
        )
        self.event_manager.subscribe(
            EventType.TIMELINE_PROCESSED,
            self._handle_phase_transition_event,
            subscriber_name="PhaseManager.timeline_processed",
        )

    def _handle_phase_transition_event(self, event: GameEvent) -> None:
        """Handle events that might trigger phase transitions."""

        # Check for game phase transitions
        for rule in self.game_phase_rules:
            if rule.matches(self.state.phase, event.event_type):
                self._transition_game_phase(rule.to_phase, event, rule.description)
                return

        # Check for battle phase transitions (only if we're in battle)
        if self.state.phase == GamePhase.BATTLE and self.state.battle:
            for rule in self.battle_phase_rules:
                if rule.matches(self.state.battle.phase, event.event_type):
                    unit_id = getattr(event, "unit_id", None)
                    self._transition_battle_phase(
                        rule.to_phase, unit_id, event, rule.description
                    )
                    return

    def _transition_game_phase(
        self, new_phase: GamePhase, triggering_event: GameEvent, description: str
    ) -> None:
        """Transition to a new game phase."""
        old_phase = self.state.phase
        if old_phase == new_phase:
            return  # No transition needed

        self.state.phase = new_phase

        # Emit phase change event
        self.event_manager.publish(
            GamePhaseChanged(
                turn=self.state.battle.current_turn if self.state.battle else 0,
                old_phase=old_phase.name,
                new_phase=new_phase.name,
            ),
            source="PhaseManager",
        )

        self._emit_log(
            f"Game phase: {old_phase.name} -> {new_phase.name} ({description})"
        )

    def _transition_battle_phase(
        self,
        new_phase: BattlePhase,
        unit_id: Optional[str],
        triggering_event: GameEvent,
        description: str,
    ) -> None:
        """Transition to a new battle phase."""
        if not self.state.battle:
            self._emit_log(
                "Cannot transition battle phase without battle state", level="ERROR"
            )
            return

        old_phase = self.state.battle.phase
        if old_phase == new_phase:
            return  # No transition needed

        self.state.battle.phase = new_phase

        # Clear movement range when unit turn ends (transitioning to TIMELINE_PROCESSING)
        if (new_phase == BattlePhase.TIMELINE_PROCESSING and 
            triggering_event.event_type == EventType.UNIT_TURN_ENDED):
            self.state.battle.movement_range = VectorArray()
            self._emit_log("Movement range cleared at end of unit turn")

        # Emit battle phase change event
        self.event_manager.publish(
            BattlePhaseChanged(
                turn=self.state.battle.current_turn,
                old_phase=old_phase.name,
                new_phase=new_phase.name,
                unit_id=unit_id,
            ),
            source="PhaseManager",
        )

    def force_game_phase_transition(
        self, new_phase: GamePhase, reason: str = "Manual override"
    ) -> None:
        """Force a game phase transition without an event trigger.

        This should be used sparingly, mainly for initialization or emergency recovery.
        """
        old_phase = self.state.phase
        if old_phase == new_phase:
            return

        self.state.phase = new_phase

        self.event_manager.publish(
            GamePhaseChanged(
                turn=self.state.battle.current_turn if self.state.battle else 0,
                old_phase=old_phase.name,
                new_phase=new_phase.name,
            ),
            source="PhaseManager",
        )

        self._emit_log(
            f"FORCED game phase: {old_phase.name} -> {new_phase.name} ({reason})"
        )

    def force_battle_phase_transition(
        self,
        new_phase: BattlePhase,
        unit_id: Optional[str] = None,
        reason: str = "Manual override",
    ) -> None:
        """Force a battle phase transition without an event trigger.

        This should be used sparingly, mainly for initialization or emergency recovery.
        """
        if not self.state.battle:
            self._emit_log(
                "Cannot force battle phase transition without battle state",
                level="ERROR",
            )
            return

        old_phase = self.state.battle.phase
        if old_phase == new_phase:
            return

        self.state.battle.phase = new_phase

        self.event_manager.publish(
            BattlePhaseChanged(
                turn=self.state.battle.current_turn,
                old_phase=old_phase.name,
                new_phase=new_phase.name,
                unit_id=unit_id,
            ),
            source="PhaseManager",
        )

        unit_info = f" (unit: {unit_id})" if unit_id else ""
        self._emit_log(
            f"FORCED battle phase: {old_phase.name} -> {new_phase.name}{unit_info} ({reason})"
        )

    def add_game_phase_rule(self, rule: GamePhaseTransitionRule) -> None:
        """Add a custom game phase transition rule."""
        self.game_phase_rules.append(rule)
        self._emit_log(f"Added game phase rule: {rule.description}")

    def add_battle_phase_rule(self, rule: BattlePhaseTransitionRule) -> None:
        """Add a custom battle phase transition rule."""
        self.battle_phase_rules.append(rule)
        self._emit_log(f"Added battle phase rule: {rule.description}")
