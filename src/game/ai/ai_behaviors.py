"""AI Behavior Strategy Classes

This module implements the Strategy design pattern for AI behaviors.
Each AI behavior represents a different approach to tactical decision-making.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Any
from enum import Enum, auto


if TYPE_CHECKING:
    from ..entities.unit import Unit
    from ..map import GameMap
    from ...core.engine.timeline import Timeline


class AIType(Enum):
    """Available AI behavior types."""
    AGGRESSIVE = auto()
    INACTIVE = auto()


class AIDecision:
    """Represents an AI decision with target information."""
    
    def __init__(self, action_name: str, target: Optional[Any] = None, 
                 confidence: float = 0.5, reasoning: str = ""):
        self.action_name = action_name
        self.target = target
        self.confidence = confidence  # 0.0 = low confidence, 1.0 = high confidence
        self.reasoning = reasoning


class AIBehavior(ABC):
    """Abstract base class for AI behavior strategies."""
    
    @abstractmethod
    def choose_action(self, unit: "Unit", game_map: "GameMap", timeline: "Timeline") -> AIDecision:
        """Choose the best action for this unit given the current situation.
        
        Args:
            unit: The unit making the decision
            game_map: The current game map
            timeline: The timeline system for turn order awareness
            
        Returns:
            AIDecision with action and target information
        """
        pass
    
    @abstractmethod
    def get_behavior_name(self) -> str:
        """Get the name of this AI behavior."""
        pass


class AggressiveAI(AIBehavior):
    """Aggressive AI that seeks the closest enemy and attacks."""
    
    def choose_action(self, unit: "Unit", game_map: "GameMap", timeline: "Timeline") -> AIDecision:
        """Choose action by finding closest enemy and attacking or moving toward them."""
        # Find closest enemy
        closest_enemy = None
        closest_distance = float('inf')
        
        for other_unit in game_map.units:
            if (other_unit.unit_id != unit.unit_id and 
                other_unit.team != unit.team and 
                other_unit.is_alive):
                
                distance = unit.position.manhattan_distance_to(other_unit.position)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_enemy = other_unit
        
        # No enemies found
        if closest_enemy is None:
            return AIDecision(
                action_name="Wait",
                confidence=0.1,
                reasoning="No enemies found on battlefield"
            )
        
        # Check if we can attack the closest enemy
        if unit.can_attack(closest_enemy.position):
            return AIDecision(
                action_name="Attack",
                target=closest_enemy.position,  # Pass the position (Vector2) as expected by AttackAction
                confidence=0.9,
                reasoning=f"Attacking closest enemy {closest_enemy.name} at distance {closest_distance}"
            )
        
        # Can't attack, try to move closer
        # Find position that gets us closer to the enemy using actual movement range
        current_distance = unit.position.manhattan_distance_to(closest_enemy.position)
        best_position = None
        best_distance = current_distance
        
        # Get actual movement range from the game map
        movement_range = game_map.calculate_movement_range(unit)
        
        # Check all positions within actual movement range
        for candidate_pos in movement_range:
            # Skip positions that are already occupied
            if game_map.get_unit_at(candidate_pos) is not None:
                continue
                
            distance_to_enemy = candidate_pos.manhattan_distance_to(closest_enemy.position)
            if distance_to_enemy < best_distance:
                best_distance = distance_to_enemy
                best_position = candidate_pos
        
        # Move toward enemy if we found a better position
        if best_position is not None:
            return AIDecision(
                action_name="Move",
                target=best_position,
                confidence=0.7,
                reasoning=f"Moving closer to enemy {closest_enemy.name}"
            )
        
        # Can't move closer, just wait
        return AIDecision(
            action_name="Wait",
            confidence=0.3,
            reasoning=f"Cannot move closer to enemy {closest_enemy.name}"
        )
    
    def get_behavior_name(self) -> str:
        return "Aggressive"


class InactiveAI(AIBehavior):
    """Inactive AI that just waits every turn."""
    
    def choose_action(self, unit: "Unit", game_map: "GameMap", timeline: "Timeline") -> AIDecision:
        """Always choose to wait."""
        return AIDecision(
            action_name="Wait",
            confidence=1.0,
            reasoning="Inactive AI always waits"
        )
    
    def get_behavior_name(self) -> str:
        return "Inactive"


def create_ai_behavior(ai_type: AIType) -> AIBehavior:
    """Factory function to create AI behavior instances.
    
    Args:
        ai_type: Type of AI behavior to create
        
    Returns:
        AIBehavior instance
        
    Raises:
        ValueError: If ai_type is not supported
    """
    if ai_type == AIType.AGGRESSIVE:
        return AggressiveAI()
    elif ai_type == AIType.INACTIVE:
        return InactiveAI()
    else:
        raise ValueError(f"Unsupported AI type: {ai_type}")