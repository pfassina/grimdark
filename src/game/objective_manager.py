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

from ..core.events import GameEvent, EventType, ObjectiveContext
from ..core.game_view import GameView
from ..core.game_enums import ObjectiveStatus

if TYPE_CHECKING:
    from .objectives import Objective


class ObjectiveManager:
    """Manages event-driven objectives for a scenario.
    
    This manager:
    1. Registers objectives and tracks their interests
    2. Routes events only to subscribed objectives  
    3. Provides victory/defeat condition evaluation
    4. Manages objective lifecycle and status updates
    """
    
    def __init__(self, game_view: GameView):
        """Initialize the objective manager.
        
        Args:
            game_view: GameView adapter for objective queries
        """
        self.game_view = game_view
        self.victory_objectives: list["Objective"] = []
        self.defeat_objectives: list["Objective"] = []
        
        # Event routing optimization: map event types to interested objectives
        self._event_subscribers: dict[EventType, list["Objective"]] = defaultdict(list)
    
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
        
        # Initialize objectives with current game state
        self._initialize_objectives()
    
    def on_event(self, event: GameEvent) -> None:
        """Process a game event and route it to interested objectives.
        
        Args:
            event: The game event to process
        """
        interested_objectives = self._event_subscribers.get(event.event_type, [])
        
        if interested_objectives:
            context = ObjectiveContext(event=event, view=self.game_view)
            
            for objective in interested_objectives:
                objective.on_event(context)
    
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
            if hasattr(objective, 'recompute'):
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