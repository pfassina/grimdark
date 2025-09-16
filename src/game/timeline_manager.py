"""Timeline-based combat management system.

This module replaces the traditional turn-based system with a fluid timeline
where units act based on action weights and speed. It manages the timeline queue,
processes unit actions, and handles the flow between different combat phases.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..core.event_manager import EventManager
    from ..core.game_state import GameState
    from .map import GameMap
    from .unit import Unit

from ..core.actions import Action, ActionResult, create_action_by_name
from ..core.events import (
    ActionExecuted,
    LogMessage,
    ManagerInitialized,
    ObjectivesCheckRequested,
    PlayerActionRequested,
    TimelineProcessed,
    TurnEnded,
    TurnStarted,
    UIStateChanged,
    UnitTurnEnded,
    UnitTurnStarted,
)
from ..core.game_enums import Team
from ..core.game_state import BattlePhase
from ..core.hidden_intent import HiddenIntentManager
from ..core.timeline import TimelineEntry

# AI controller imports removed - now using AI components


class TimelineManager:
    """Manages timeline-based combat flow.

    The TimelineManager replaces the traditional TurnManager with a fluid system
    where units are scheduled on a timeline based on their action weights and speed.
    This creates tactical depth where fast units with light actions can act multiple
    times before slow units with heavy actions get their turn.
    """

    def __init__(
        self,
        game_map: "GameMap",
        game_state: "GameState",
        event_manager: "EventManager",
    ):
        self.game_map = game_map
        self.state = game_state
        self.event_manager = event_manager

        # Initialize timeline
        self.timeline = game_state.battle.timeline

        # Initialize hidden intent system
        self.intent_manager = HiddenIntentManager()

        # Timeline statistics
        self.total_ticks_processed = 0
        self.actions_executed = 0

        # Subscribe to relevant events
        self._setup_event_subscriptions()

        # Emit initialization event
        self.event_manager.publish(
            ManagerInitialized(turn=0, manager_name="TimelineManager"),
            source="TimelineManager",
        )

    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for timeline manager."""
        from ..core.events import EventType

        self.event_manager.subscribe(
            event_type=EventType.UNIT_DEFEATED,
            subscriber=self._handle_unit_defeated,
            subscriber_name="TimelineManager.unit_defeated",
        )
        
        self.event_manager.subscribe(
            event_type=EventType.BATTLE_PHASE_CHANGED,
            subscriber=self._handle_battle_phase_changed,
            subscriber_name="TimelineManager.battle_phase_changed",
        )
        
        self.event_manager.subscribe(
            event_type=EventType.ACTION_EXECUTED,
            subscriber=self._handle_action_executed,
            subscriber_name="TimelineManager.action_executed",
        )

    def _handle_unit_defeated(self, event) -> None:
        """Handle unit defeat by removing from timeline."""
        from ..core.events import UnitDefeated

        if isinstance(event, UnitDefeated):
            removed_count = self.timeline.remove_entry(event.unit_id)

            if removed_count > 0:
                self._emit_log(
                    f"Cleaned up {removed_count} timeline entries for defeated unit {event.unit_name}",
                    "TIMELINE",
                )

    def _handle_battle_phase_changed(self, event) -> None:
        """Handle battle phase changes to restore movement range when needed."""
        from ..core.events import BattlePhaseChanged

        if isinstance(event, BattlePhaseChanged):
            # When transitioning to UNIT_MOVING or UNIT_ACTION_SELECTION phase (e.g., after canceling),
            # restore the original movement range that was calculated when turn started
            if (event.new_phase in ["UNIT_MOVING", "UNIT_ACTION_SELECTION"] and 
                event.unit_id and 
                self.state.battle.selected_unit_id == event.unit_id and
                self.state.battle.original_movement_range):
                
                # Restore the exact movement range that was originally calculated
                # This prevents exploitation and preserves the exact original range
                self.state.battle.set_movement_range(self.state.battle.original_movement_range)
                
                unit = self.game_map.get_unit(event.unit_id)
                unit_name = unit.name if unit else event.unit_id
                self._emit_log(
                    f"Restored original movement range for {unit_name}",
                    "TIMELINE",
                )

    def _handle_action_executed(self, event) -> None:
        """Handle action execution by scheduling the unit for their next turn."""
        from ..core.events import ActionExecuted
        from ..core.actions import create_action_by_name
        
        if not isinstance(event, ActionExecuted):
            return
            
        self._emit_log(f"Received ActionExecuted event: {event.unit_name} -> {event.action_name}", "TIMELINE", "DEBUG")
            
        # Get the unit that executed the action - log error if not found
        unit = self.game_map.get_unit(event.unit_id)
        if not unit:
            self._emit_log(f"ActionExecuted event references non-existent unit: {event.unit_id}", "TIMELINE", "ERROR")
            return
            
        # Get the action - log error if not found  
        action = create_action_by_name(event.action_name)
        if not action:
            self._emit_log(f"ActionExecuted event references unknown action: {event.action_name}", "TIMELINE", "ERROR")
            return
            
        # Schedule the unit for their next turn using proper action weight
        effective_weight = action.get_effective_weight(unit)
        self.timeline.schedule_unit(
            unit=unit,
            action_weight=effective_weight,
            action_description=f"Recovering from {event.action_name}",
        )
        
        self.actions_executed += 1
        self._emit_log(f"{unit.name}: {event.action_name} (+{effective_weight} weight)")

    def initialize_battle_timeline(self) -> None:
        """Initialize the timeline with all units at battle start.

        Each unit gets an initial scheduling based on their base speed.
        Faster units will act first, creating natural turn order.
        """
        self.timeline.clear()

        # Schedule all alive units
        units_added = 0

        for unit in self.game_map.units:
            if not unit:
                continue

            if unit.is_alive:
                self._emit_log(
                    f"✓ Adding {unit.name} (team: {unit.team}, id: {unit.unit_id}) to timeline",
                    "TIMELINE",
                )

                # Initial action weight of 0 means units act based on speed alone
                initial_weight = 0
                self.timeline.schedule_unit(
                    unit=unit,
                    action_weight=initial_weight,
                    action_description="Ready to Act",
                )
                units_added += 1
        self.state.battle.start_timeline_processing()
        # Start timeline processing

        self._emit_log(
            f"Timeline initialized with {units_added} units out of {len(self.game_map.units)} total",
            "TIMELINE",
        )

        # Safeguard: Ensure timeline consistency
        self._ensure_timeline_consistency()

        # Emit timeline processed event
        self.event_manager.publish(
            TimelineProcessed(
                turn=self.timeline.current_time, entries_processed=units_added
            ),
            source="TimelineManager",
        )

    def _emit_log(
        self, message: str, category: str = "TIMELINE", level: str = "INFO"
    ) -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=self.timeline.current_time,
                message=message,
                category=category,
                level=level,
                source="TimelineManager",
            ),
            source="TimelineManager",
        )

    def _emit_ui_message(self, message: str) -> None:
        """Emit a UI message event."""
        self.event_manager.publish(
            UIStateChanged(
                turn=self.timeline.current_time,
                state_type="user_message",
                new_value=message,
            ),
            source="TimelineManager",
        )

    def process_timeline(self) -> bool:
        """Process the next entry in the timeline.

        Returns:
            True if an entry was processed, False if timeline is empty
        """
        if self.timeline.is_empty:
            self._emit_log("Timeline is empty, no entries to process", level="WARNING")
            return False

        # Get next timeline entry
        next_entry = self.timeline.peek_next()
        if not next_entry:
            self._emit_log("No next entry found in timeline", level="WARNING")
            return False

        if next_entry.entity_type == "unit":
            unit = self._get_unit_from_entry(next_entry)

        # Handle different entity types
        if next_entry.entity_type == "hazard":
            # Process hazard tick
            return self._process_hazard_entry(next_entry)
        elif next_entry.entity_type == "unit":
            # Unit in timeline must exist and be alive
            unit = self._get_unit_from_entry(next_entry)
            assert unit.is_alive, (
                f"Dead unit {unit.name} found in timeline - data inconsistency"
            )

            # For interactive turns, DON'T pop the entry until action is complete
            # Only peek at the entry to start the turn
            entry = next_entry  # Use the peeked entry

            self.total_ticks_processed += 1

            # Handle scheduled actions (for interrupts/prepared actions)
            if entry.scheduled_action:
                # Pop entry for immediate scheduled actions
                self.timeline.pop_next()
                self._execute_scheduled_action(entry)
            else:
                # Regular unit turn - DON'T pop entry yet, wait for actual action
                # Entry will be popped when action is executed via execute_unit_action
                self._begin_unit_turn(unit)
        else:
            self._emit_log(
                f"Unknown entity type: {next_entry.entity_type}", level="WARNING"
            )

        return True

    def _begin_unit_turn(self, unit: "Unit") -> None:
        """Begin a unit's turn, either player or AI controlled."""

        # Emit turn started events
        self.event_manager.publish(
            TurnStarted(turn=self.timeline.current_time, team=unit.team),
            source="TimelineManager",
        )
        self.event_manager.publish(
            UnitTurnStarted(
                turn=self.timeline.current_time,
                unit_name=unit.name,
                unit_id=unit.unit_id,
                team=unit.team,
            ),
            source="TimelineManager",
        )

        if unit.team == Team.PLAYER:
            self._begin_player_unit_turn(unit)
        else:
            self._begin_ai_unit_turn(unit)

    def _begin_player_unit_turn(self, unit: "Unit") -> None:
        """Handle the start of a player unit's turn."""
        self._emit_log(f"{unit.name}: Turn started")

        # Move cursor to the unit and select it
        self.state.cursor.set_position(unit.position)
        self.state.battle.selected_unit_id = unit.unit_id
        self.state.battle.current_acting_unit_id = (
            unit.unit_id
        )  # CRITICAL: Set acting unit ID

        # DEFENSIVE: Validate synchronization and attempt recovery if needed
        self._validate_timeline_unit_synchronization(unit)

        # Store original position for potential movement cancellation
        self.state.battle.original_unit_position = unit.position

        # CRITICAL: Reset unit flags for new turn
        unit.has_moved = False
        unit.has_acted = False

        # Emit unit turn started - PhaseManager will transition to UNIT_MOVING
        self.event_manager.publish(
            UnitTurnStarted(
                turn=self.timeline.current_time,
                unit_name=unit.name,
                unit_id=unit.unit_id,
                team=unit.team,
            ),
            source="TimelineManager",
        )

        # Calculate and show movement range
        movement_range = self.game_map.calculate_movement_range(unit)
        self.state.battle.set_movement_range(movement_range)
        # Store original movement range for potential restoration after canceling actions
        self.state.battle.original_movement_range = movement_range

        # Emit player action request
        self.event_manager.publish(
            PlayerActionRequested(
                turn=self.timeline.current_time,
                unit_name=unit.name,
                unit_id=unit.unit_id,
                available_actions=["Move", "Attack", "Wait"],
            ),
            source="TimelineManager",
        )

        # Emit UI message
        self._emit_ui_message(
            f"Unit {unit.name} selected. Use arrow keys to move, Enter to confirm position, then choose action."
        )

    def _begin_ai_unit_turn(self, unit: "Unit") -> None:
        """Handle the start of an AI unit's turn using AI component."""

        # CRITICAL: Set acting unit ID so execute_unit_action can find the unit
        self.state.battle.current_acting_unit_id = unit.unit_id

        # CRITICAL: Reset unit flags for new turn
        unit.has_moved = False
        unit.has_acted = False

        # Use AI component to make decision
        try:
            decision = unit.ai.make_decision(self.game_map, self.timeline)

            self._emit_log(f"{unit.name}: {decision.action_name} selected", "AI")

        except Exception as e:
            self._emit_log(
                f"AI component decision failed for {unit.name}: {e}", "AI", "ERROR"
            )
            # Fall back to wait action
            self._execute_fallback_ai_action(unit)
            return

        # Execute the AI's decision directly - no callbacks to avoid complexity
        result = self.execute_unit_action(decision.action_name, decision.target)

        if result == ActionResult.SUCCESS:
            self._emit_log(f"{unit.name}: {decision.action_name} completed", "AI")
        else:
            self._emit_log(
                f"Action: {decision.action_name}, Target: {decision.target} Failed",
                "AI",
                "ERROR",
            )
            # Fall back to a simple action if the AI decision fails
            self._execute_fallback_ai_action(unit)
            return  # Exit early since fallback will set the phase

        # Emit timeline processed event - PhaseManager will transition to TIMELINE_PROCESSING
        self.event_manager.publish(
            TimelineProcessed(turn=self.timeline.current_time, entries_processed=1),
            source="TimelineManager",
        )

    def _execute_fallback_ai_action(self, unit: "Unit") -> None:
        """Execute a simple fallback AI action when the main AI fails."""
        if unit:
            # CRITICAL: Pop the current timeline entry since the primary action failed
            # The unit's timeline entry must be popped before rescheduling
            current_entry = self.timeline.peek_next()
            if (
                current_entry
                and current_entry.entity_type == "unit"
                and current_entry.entity_id == unit.unit_id
            ):
                self.timeline.pop_next()
            
            # For now, skip trying alternative actions to avoid complexity
            # Just go straight to Wait action
            
            # If no attack available, just wait
            self._emit_log(f"{unit.name}: Wait (fallback)", "AI")
            
            # Directly reschedule with Wait weight (entry already popped above)
            result = self._execute_wait_action(unit)
            if result != ActionResult.SUCCESS:
                self._emit_log(
                    f"Fallback Wait action also failed for {unit.name}", "AI", "ERROR"
                )
                # Last resort - just reschedule with basic parameters
                self.timeline.schedule_unit(
                    unit=unit,
                    action_weight=100,
                    action_description="Waiting",
                )
            # Emit timeline processed event - PhaseManager will transition to TIMELINE_PROCESSING
            self.event_manager.publish(
                TimelineProcessed(turn=self.timeline.current_time, entries_processed=1),
                source="TimelineManager",
            )

        # Emit turn ended event
        if unit:
            self.event_manager.publish(
                TurnEnded(turn=self.timeline.current_time, team=unit.team),
                source="TimelineManager",
            )

        # Emit timeline processed event - PhaseManager will transition to TIMELINE_PROCESSING
        self.event_manager.publish(
            TimelineProcessed(turn=self.timeline.current_time, entries_processed=1),
            source="TimelineManager",
        )

    def execute_unit_action(
        self, action_name: str, target: Optional[object] = None
    ) -> ActionResult:
        """Execute an action for the current acting unit.

        Args:
            action_name: Name of the action to execute
            target: Optional target for the action

        Returns:
            Result of the action execution
        """
        # Get the current acting unit
        unit = self._get_current_acting_unit()
        if not unit:
            return ActionResult.FAILED

        # Handle special "Wait" action BEFORE trying to look up regular actions
        if action_name == "Wait":
            # Pop the timeline entry since we're executing
            current_entry = self.timeline.peek_next()
            if (
                current_entry
                and current_entry.entity_type == "unit"
                and current_entry.entity_id == unit.unit_id
            ):
                self.timeline.pop_next()

            # Execute Wait action directly and return immediately
            result = self._execute_wait_action(unit)

            # CRITICAL: Clear unit selection and acting unit after Wait
            self.state.battle.selected_unit_id = None
            self.state.battle.current_acting_unit_id = None
            self.state.ui.close_action_menu()

            return result

        # Now that the unit is actually taking action, pop their timeline entry
        current_entry = self.timeline.peek_next()
        if (
            current_entry
            and current_entry.entity_type == "unit"
            and current_entry.entity_id == unit.unit_id
        ):
            self.timeline.pop_next()
        else:
            self._emit_log(
                f"✗ Timeline entry mismatch for {unit.name} action {action_name}",
                "TIMELINE",
                "WARNING",
            )
            if current_entry and current_entry.entity_type == "unit":
                entry_unit = self._get_unit_from_entry(current_entry)
                self._emit_log(
                    f"Expected {unit.name}, found {entry_unit.name}",
                    "TIMELINE",
                    "WARNING",
                )
            else:
                self._emit_log("No current entry or unit found", "TIMELINE", "WARNING")

        # Create the action
        action = create_action_by_name(action_name)
        if not action:
            self._emit_log(f"Unknown action: {action_name}", "TIMELINE", "ERROR")
            return ActionResult.FAILED

        # Store the pending action
        self.state.battle.set_pending_action(action_name, target)

        # If no target provided but action needs one, wait for targeting
        if target is None and self._action_requires_target(action):
            return ActionResult.REQUIRES_TARGET

        # Validate the action
        validation = action.validate(unit, self.game_map, target)
        if not validation.is_valid:
            self._emit_log(
                f"Action invalid: {validation.reason}", "TIMELINE", "WARNING"
            )
            # CRITICAL: Clear the pending action since validation failed
            self.state.battle.clear_pending_action()
            return ActionResult.FAILED

        # Execute the action
        def emit_event(event):
            self.event_manager.publish(event, source="ActionExecution")

        result = action.execute(unit, self.game_map, target, emit_event)

        if result == ActionResult.SUCCESS:
            # Emit turn ended events
            self.event_manager.publish(
                TurnEnded(turn=self.timeline.current_time, team=unit.team),
                source="TimelineManager",
            )
            self.event_manager.publish(
                UnitTurnEnded(
                    turn=self.timeline.current_time,
                    unit_name=unit.name,
                    unit_id=unit.unit_id,
                    team=unit.team,
                    action_taken=action_name,
                ),
                source="TimelineManager",
            )

        # Clear the pending action and return to timeline processing
        self.state.battle.clear_pending_action()

        # Clear unit selection to end the turn properly
        self.state.battle.selected_unit_id = None
        self.state.ui.close_action_menu()

        # Emit action executed event - PhaseManager will transition to TIMELINE_PROCESSING
        self.event_manager.publish(
            ActionExecuted(
                turn=self.timeline.current_time,
                unit_name=unit.name if unit else "Unknown",
                unit_id=unit.unit_id if unit else "unknown",
                action_name=action_name,
                action_type=action.name if action else "Unknown",
                success=(result == ActionResult.SUCCESS),
            ),
            source="TimelineManager",
        )

        # Check objectives after action (emit event for objective system)
        self.event_manager.publish(
            ObjectivesCheckRequested(
                turn=self.timeline.current_time,
                trigger_reason="unit_action_completed"
            ),
            source="TimelineManager"
        )

        return result

    def handle_action_targeting(self, target: object) -> ActionResult:
        """Handle target selection for pending action.

        Args:
            target: The selected target

        Returns:
            Result of executing the action with target
        """
        if not self.state.battle.pending_action:
            return ActionResult.FAILED

        # Execute the action with the selected target
        return self.execute_unit_action(self.state.battle.pending_action, target)

    def _get_current_acting_unit(self) -> Optional["Unit"]:
        """Get the unit that is currently acting."""
        unit_id = self.state.battle.current_acting_unit_id
        if not unit_id:
            return None

        return self.game_map.get_unit(unit_id)

    def _get_unit_from_entry(self, entry: TimelineEntry) -> "Unit":
        """Get unit from timeline entry with validation.

        Args:
            entry: Timeline entry that should reference a unit

        Returns:
            The Unit object

        Raises:
            AssertionError: If entry is not a unit or unit doesn't exist
        """
        assert entry.entity_type == "unit", (
            f"Expected unit entry, got {entry.entity_type}"
        )
        unit = self.game_map.get_unit(entry.entity_id)
        assert unit is not None, (
            f"Timeline entry references non-existent unit: {entry.entity_id}"
        )
        return unit

    def _action_requires_target(self, action: Action) -> bool:
        """Check if an action requires target selection."""
        # Most attack actions require targets
        # Movement actions need destination
        # This could be enhanced with action metadata
        return action.name in [
            "Attack",
            "Quick Strike",
            "Power Attack",
            "Charge",
            "Move",
            "Quick Move",
        ]

    def _execute_scheduled_action(self, entry: TimelineEntry) -> None:
        """Execute a pre-scheduled action (interrupt/prepared action)."""
        if entry.entity_type == "unit":
            unit = self._get_unit_from_entry(entry)
            action = entry.scheduled_action
            self._emit_log(f"{unit.name}: {action} triggered", "INTERRUPT")

            # This would integrate with the interrupt system
            # For now, just schedule the unit normally
            self.timeline.schedule_unit(
                unit=unit,
                action_weight=100,  # Standard weight for scheduled actions
                action_description="Ready to Act",
            )
        else:
            self._emit_log(
                "Scheduled action called with None unit", "TIMELINE", "WARNING"
            )

    def skip_unit_turn(self) -> None:
        """Skip the current unit's turn (wait/pass action)."""
        unit = self._get_current_acting_unit()
        if unit:
            # Schedule with minimal weight (pass/wait is quick)
            self.timeline.schedule_unit(
                unit=unit,
                action_weight=50,  # Quick action weight
                action_description="Waiting",
            )

            self._emit_log(f"{unit.name}: Pass (+50 weight)")

            # Emit turn ended events
            self.event_manager.publish(
                TurnEnded(turn=self.timeline.current_time, team=unit.team),
                source="TimelineManager",
            )
            self.event_manager.publish(
                UnitTurnEnded(
                    turn=self.timeline.current_time,
                    unit_name=unit.name,
                    unit_id=unit.unit_id,
                    team=unit.team,
                    action_taken="Pass",
                ),
                source="TimelineManager",
            )

            # Clear action state and return to timeline processing
            self.state.battle.clear_pending_action()

            # Check objectives after skip action (emit event for objective system)
            self.event_manager.publish(
                ObjectivesCheckRequested(
                    turn=self.timeline.current_time,
                    trigger_reason="unit_skip_action"
                ),
                source="TimelineManager"
            )

    def _process_hazard_entry(self, entry: TimelineEntry) -> bool:
        """Process a hazard timeline entry.

        Args:
            entry: The hazard timeline entry to process

        Returns:
            True if processed successfully
        """
        # Pop the entry from timeline
        self.timeline.pop_next()

        # Skip hazard processing for now - hazard manager not implemented
        return True

    def remove_unit_from_timeline(self, unit: "Unit") -> None:
        """Remove a unit from the timeline (when they die)."""

        # If this was the current acting unit, return to timeline processing
        if self.state.battle.current_acting_unit_id == unit.unit_id:
            self.state.battle.clear_pending_action()

    def get_timeline_preview(self, count: int = 7) -> list[dict]:
        """Get a preview of the timeline for UI display.

        Args:
            count: Number of entries to preview

        Returns:
            List of timeline entry info for display
        """
        entries = self.timeline.get_preview(count)
        preview = []

        for entry in entries:
            if entry.entity_type == "hazard":
                # Handle hazard entries
                preview.append(
                    {
                        "unit_name": f"[{entry.action_description}]",
                        "unit_id": entry.entity_id,
                        "team": "hazard",
                        "execution_time": entry.execution_time,
                        "time_until_action": entry.execution_time
                        - self.timeline.current_time,
                        "intent_visible": True,
                        "intent_description": entry.action_description,
                    }
                )
            elif entry.entity_type == "unit":
                unit = self._get_unit_from_entry(entry)
                intent_desc = self.intent_manager.get_visible_intent_description(
                    unit,
                    observer=None,  # TODO: Pass actual observer unit
                    current_time=self.timeline.current_time,
                )

                preview.append(
                    {
                        "unit_name": unit.name,
                        "unit_id": unit.unit_id,
                        "team": unit.team.name,
                        "execution_time": entry.execution_time,
                        "time_until_action": entry.execution_time
                        - self.timeline.current_time,
                        "intent_visible": True,  # Visibility handled by intent_description
                        "intent_description": intent_desc,
                    }
                )

        return preview

    def get_timeline_stats(self) -> dict:
        """Get timeline statistics for debugging."""
        stats = self.timeline.get_stats()
        stats.update(
            {
                "total_ticks_processed": self.total_ticks_processed,
                "actions_executed": self.actions_executed,
            }
        )
        return stats

    def is_battle_over(self) -> bool:
        """Check if the battle should end (all units of one side dead)."""
        player_alive = any(
            unit.team == Team.PLAYER and unit.is_alive
            for unit in self.game_map.units
            if unit
        )
        enemy_alive = any(
            unit.team == Team.ENEMY and unit.is_alive
            for unit in self.game_map.units
            if unit
        )

        return not (player_alive and enemy_alive)

    def _validate_timeline_unit_synchronization(self, expected_unit: "Unit") -> None:
        """Validate that timeline, cursor, and selection are properly synchronized.

        Args:
            expected_unit: The unit that should be acting according to the timeline
        """
        inconsistencies = []

        # Check cursor position matches unit position
        if self.state.cursor.position != expected_unit.position:
            inconsistencies.append(
                f"Cursor position {self.state.cursor.position} != unit position {expected_unit.position}"
            )

        # Check selected unit ID matches timeline unit
        if self.state.battle.selected_unit_id != expected_unit.unit_id:
            inconsistencies.append(
                f"Selected unit '{self.state.battle.selected_unit_id}' != timeline unit '{expected_unit.unit_id}'"
            )

        # Check that the current acting unit ID matches
        if self.state.battle.current_acting_unit_id != expected_unit.unit_id:
            inconsistencies.append(
                f"Acting unit '{self.state.battle.current_acting_unit_id}' != timeline unit '{expected_unit.unit_id}'"
            )

        if inconsistencies:
            self._emit_log(
                "=== SYNCHRONIZATION ISSUES DETECTED ===", "TIMELINE", "WARNING"
            )
            for issue in inconsistencies:
                self._emit_log(f"  - {issue}", "TIMELINE", "WARNING")
            self._emit_log("Attempting recovery...", "TIMELINE", "WARNING")

            # Attempt recovery by forcing synchronization
            self.state.cursor.set_position(expected_unit.position)
            self.state.battle.selected_unit_id = expected_unit.unit_id
            self.state.battle.current_acting_unit_id = expected_unit.unit_id

            self._emit_log(
                "Recovery completed - cursor and selection forced to sync with timeline",
                "TIMELINE",
                "WARNING",
            )

    def update(self) -> None:
        """Update the timeline manager (called each game loop).

        This processes the timeline when appropriate and handles
        phase transitions.
        """
        if self.state.battle.phase == BattlePhase.TIMELINE_PROCESSING:
            # Try to process next timeline entry
            if not self.process_timeline():
                # Timeline is empty - check if battle is over or if we need recovery
                if self.is_battle_over():
                    self._emit_log("Battle is over!", "SYSTEM")
                    # Let game handle battle end
                else:
                    self._emit_log(
                        "Timeline empty but battle not over - attempting recovery",
                        "TIMELINE",
                        "ERROR",
                    )
                    # Try to recover timeline consistency
                    self._ensure_timeline_consistency()

        # Periodic cleanup of removed entries
        if self.total_ticks_processed % 100 == 0:
            self.timeline.cleanup_removed_entries()

    def _ensure_timeline_consistency(self) -> None:
        """Ensure timeline consistency - prevent empty timeline when units are alive."""
        if not self.timeline.is_empty:
            return  # Timeline has entries, all good

        # Timeline is empty, check if there are still alive units
        alive_units = [unit for unit in self.game_map.units if unit and unit.is_alive]

        if not alive_units:
            return

        # Timeline is empty but there are alive units - this is inconsistent!
        self._emit_log(
            f"Timeline consistency issue: {len(alive_units)} alive units but empty timeline",
            "TIMELINE",
            "WARNING",
        )
        self._emit_log(
            "Attempting recovery by re-adding missing units", "TIMELINE", "WARNING"
        )

        # Recovery: Add all alive units back to timeline
        recovery_count = 0
        for unit in alive_units:
            self.timeline.schedule_unit(
                unit=unit,
                action_weight=0,  # Immediate action
                action_description="Recovered",
            )
            recovery_count += 1

        self._emit_log(
            f"Timeline recovery complete: {recovery_count} units restored",
            "TIMELINE",
            "WARNING",
        )

    def _execute_wait_action(self, unit: "Unit") -> ActionResult:
        """Execute a Wait action for the given unit."""
        # Ensure timeline consistency after Wait action
        self._ensure_timeline_consistency()

        # Emit unit turn ended event - PhaseManager needs this for battle phase transitions
        self.event_manager.publish(
            UnitTurnEnded(
                turn=self.timeline.current_time,
                unit_name=unit.name,
                unit_id=unit.unit_id,
                team=unit.team,
                action_taken="Wait",
            ),
            source="TimelineManager",
        )

        # Emit action executed event - this will trigger scheduling via event handler
        self.event_manager.publish(
            ActionExecuted(
                turn=self.timeline.current_time,
                unit_name=unit.name,
                unit_id=unit.unit_id,
                action_name="Wait",
                action_type="Wait",
                success=True,
            ),
            source="TimelineManager",
        )

        return ActionResult.SUCCESS

    def preview_ai_decision(self, unit: "Unit") -> Optional[str]:
        """Preview what action an AI unit would take (for UI/debugging)."""
        try:
            decision = unit.ai.make_decision(self.game_map, self.timeline)
            return f"Would {decision.action_name} (confidence: {decision.confidence:.1f}) - {decision.reasoning}"
        except Exception:
            return None
