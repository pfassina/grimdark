"""Objective manager for event-driven objective system.

This module provides the central ObjectiveManager that routes events to objectives,
manages their lifecycle, and aggregates victory/defeat conditions.

Design Principles:
- Event routing based on objective interests (only relevant events delivered)
- Synchronous processing for deterministic behavior
- Single entry point for objective lifecycle management
- Efficient aggregation of victory/defeat states
"""

from typing import TYPE_CHECKING
from collections import defaultdict

from ...core.events.events import GameEvent, EventType, ObjectiveContext, UnitDefeated, LogMessage, GameEnded
from ...core.game_view import GameView
from ...core.data.game_enums import ObjectiveStatus, Team
from ..scenarios.objectives import Objective, DefeatAllEnemiesObjective

if TYPE_CHECKING:
    from ...core.events.event_manager import EventManager


class ObjectiveManager:
    """Manages event-driven objectives for a scenario.
    
    This manager:
    1. Registers objectives and tracks their interests
    2. Routes events only to subscribed objectives  
    3. Provides victory/defeat condition evaluation
    4. Manages objective lifecycle and status updates
    """
    
    def __init__(self, game_view: GameView, event_manager: "EventManager"):
        """Initialize the objective manager.
        
        Args:
            game_view: GameView adapter for objective queries
            event_manager: Event manager for event publishing and logging
        """
        self.game_view = game_view
        self.event_manager = event_manager
        self.victory_objectives: list["Objective"] = []
        self.defeat_objectives: list["Objective"] = []
        
        # Event routing optimization: map event types to interested objectives
        self._event_subscribers: dict[EventType, list["Objective"]] = defaultdict(list)
        
        # ObjectiveManager now auto-subscribes to events that objectives care about
    
    def _emit_log(self, message: str, category: str = "OBJECTIVE", level: str = "DEBUG") -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=0,  # TODO: Get current turn from game state
                message=message,
                category=category,
                level=level,
                source="ObjectiveManager"
            ),
            source="ObjectiveManager"
        )
    
    def register_objectives(self, 
                          victory_objectives: list["Objective"], 
                          defeat_objectives: list["Objective"]) -> None:
        """Register victory and defeat objectives with the manager.
        
        Args:
            victory_objectives: List of objectives required for victory
            defeat_objectives: List of objectives that cause defeat when failed
        """
        self.victory_objectives = victory_objectives.copy()
        self.defeat_objectives = defeat_objectives.copy()
        
        # Build event subscription map for efficient routing
        self._event_subscribers.clear()
        
        for objective in victory_objectives + defeat_objectives:
            interests = objective.interests
            for event_type in interests:
                self._event_subscribers[event_type].append(objective)
        
        # Auto-subscribe to all event types that any objective cares about
        for event_type in self._event_subscribers.keys():
            self.event_manager.subscribe(
                event_type=event_type,
                subscriber=self._on_event,
                subscriber_name=f"ObjectiveManager.{event_type.name.lower()}",
            )
        
        # Initialize objectives with current game state
        self._initialize_objectives()
    
    def _on_event(self, event: GameEvent) -> None:
        """Process a game event and route it to interested objectives.
        
        Args:
            event: The game event to process
        """
        
        # Log enemy defeat events for debugging
        if isinstance(event, UnitDefeated) and event.team == Team.ENEMY:
            self._emit_log(f"Processing enemy defeat: {event.unit_name}", level="INFO")
        
        interested_objectives = self._event_subscribers.get(event.event_type, [])
        if not interested_objectives:
            return
            
        context = ObjectiveContext(event=event, view=self.game_view)
        
        for objective in interested_objectives:
            objective.on_event(context)
            
            # Log if victory was triggered
            if objective.status.name != "COMPLETED":
                continue
                
            if isinstance(objective, DefeatAllEnemiesObjective):
                self._emit_log(f"*** VICTORY TRIGGERED *** Enemy count: {objective._enemy_count}", level="INFO")
        
        # Automatically check victory/defeat conditions after processing events
        self.check_objectives()
    
    def check_victory(self) -> bool:
        """Check if all victory objectives are completed.
        
        Returns:
            True if all victory objectives are completed
        """
        if not self.victory_objectives:
            return False
            
        return all(obj.status == ObjectiveStatus.COMPLETED 
                  for obj in self.victory_objectives)
    
    def check_defeat(self) -> bool:
        """Check if any defeat objective has failed.
        
        Returns:
            True if any defeat objective has failed
        """
        return any(obj.status == ObjectiveStatus.FAILED 
                  for obj in self.defeat_objectives)
    
    def check_objectives(self) -> None:
        """Check victory and defeat conditions and emit appropriate events."""
        # Check victory conditions
        if self.check_victory():
            self._emit_log("Victory conditions met!", level="INFO")
            self.event_manager.publish(
                GameEnded(
                    turn=0,  # TODO: Get current turn from game state
                    result="victory",
                ),
                source="ObjectiveManager",
            )
            return

        # Check defeat conditions
        if self.check_defeat():
            self._emit_log("Defeat conditions met!", level="INFO")
            self.event_manager.publish(
                GameEnded(
                    turn=0,  # TODO: Get current turn from game state
                    result="defeat",
                ),
                source="ObjectiveManager",
            )
    
    
    def get_active_objectives(self) -> list["Objective"]:
        """Get all objectives that are still in progress.
        
        Returns:
            List of objectives with IN_PROGRESS status
        """
        active = []
        
        for obj in self.victory_objectives:
            if obj.status == ObjectiveStatus.IN_PROGRESS:
                active.append(obj)
                
        for obj in self.defeat_objectives:
            if obj.status == ObjectiveStatus.IN_PROGRESS:
                active.append(obj)
        
        return active
    
    def get_victory_objectives(self) -> list["Objective"]:
        """Get all victory objectives.
        
        Returns:
            List of victory objectives
        """
        return self.victory_objectives.copy()
    
    def get_defeat_objectives(self) -> list["Objective"]:
        """Get all defeat objectives.
        
        Returns:
            List of defeat objectives
        """
        return self.defeat_objectives.copy()
    
    def _initialize_objectives(self) -> None:
        """Initialize objectives with current game state.
        
        This allows objectives to align their state with the current game
        situation when they are first registered.
        """
        for objective in self.victory_objectives + self.defeat_objectives:
            # All objectives should implement recompute if they need state synchronization
            objective.recompute(self.game_view)
    
    def get_event_stats(self) -> dict[str, int]:
        """Get statistics about event subscriptions (for debugging).
        
        Returns:
            Dictionary mapping event type names to subscriber counts
        """
        stats = {}
        for event_type, subscribers in self._event_subscribers.items():
            stats[event_type.name] = len(subscribers)
        return stats