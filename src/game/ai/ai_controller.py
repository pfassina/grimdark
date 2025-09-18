"""
AI Controller System for Timeline-Based Combat

This module provides the core AI decision-making framework for the grimdark
timeline-based combat system. It implements tactical AI that understands
action weights, interrupts, and temporal strategy.

Design Principles:
- Timeline-aware planning with action weight consideration
- Intent generation using the hidden intent system
- Interrupt decision making based on threat assessment  
- Morale-influenced behavior adaptation
- Personality-based tactical variations
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, List, Tuple
import random

from ...core.engine.actions import get_available_actions, create_action_by_name
from ...core.data.data_structures import Vector2

if TYPE_CHECKING:
    from ..entities.unit import Unit
    from ..map import GameMap
    from ...core.engine.timeline import Timeline


class AIPersonality(Enum):
    """AI personality types that affect decision making"""
    AGGRESSIVE = auto()     # Favors heavy attacks and charges
    DEFENSIVE = auto()      # Uses prepared actions and seeks cover
    OPPORTUNISTIC = auto()  # Exploits interrupts and positioning
    BALANCED = auto()       # Adapts strategy based on situation


class ThreatLevel(Enum):
    """Assessment of current tactical situation"""
    LOW = auto()           # Safe situation, can take risks
    MODERATE = auto()      # Normal tactical pressure
    HIGH = auto()          # Under pressure, defensive actions
    CRITICAL = auto()      # Emergency situation, survival focus


@dataclass
class AIDecision:
    """Represents an AI decision with reasoning"""
    action_name: str
    target: Optional[Vector2] = None
    confidence: float = 0.5  # 0.0 = low confidence, 1.0 = high confidence
    reasoning: str = ""
    expected_outcome: str = ""


@dataclass
class TacticalAssessment:
    """Analysis of the current battlefield situation"""
    threat_level: ThreatLevel
    nearby_enemies: List[Unit] = field(default_factory=list)
    nearby_allies: List[Unit] = field(default_factory=list)
    safe_positions: List[Vector2] = field(default_factory=list)
    attack_opportunities: List[Tuple[Unit, str]] = field(default_factory=list)  # (target, action)
    interrupt_threats: List[Unit] = field(default_factory=list)
    timeline_pressure: float = 0.0  # How urgent is acting quickly (0.0-1.0)


class AIController(ABC):
    """Abstract base class for AI controllers"""
    
    def __init__(self, personality: AIPersonality = AIPersonality.BALANCED):
        self.personality = personality
        self.memory: dict = {}  # For learning and adaptation
        
    @abstractmethod
    def choose_action(self, unit: Unit, game_map: GameMap, timeline: Timeline) -> AIDecision:
        """Choose the best action for this unit given the current situation"""
        pass
        
    @abstractmethod
    def assess_situation(self, unit: Unit, game_map: GameMap, timeline: Timeline) -> TacticalAssessment:
        """Analyze the current tactical situation"""
        pass
        
    def should_use_interrupt(self, unit: Unit, assessment: TacticalAssessment) -> bool:
        """Determine if the unit should prepare an interrupt action"""
        # Defensive personalities use interrupts more often
        if self.personality == AIPersonality.DEFENSIVE:
            return len(assessment.interrupt_threats) > 0 or assessment.threat_level.value >= ThreatLevel.MODERATE.value
            
        # Opportunistic personalities use interrupts tactically
        elif self.personality == AIPersonality.OPPORTUNISTIC:
            return len(assessment.interrupt_threats) > 1 or assessment.timeline_pressure > 0.7
            
        # Aggressive personalities rarely use interrupts
        elif self.personality == AIPersonality.AGGRESSIVE:
            return assessment.threat_level == ThreatLevel.CRITICAL
            
        # Balanced approach
        else:
            return len(assessment.interrupt_threats) > 0 and assessment.threat_level.value >= ThreatLevel.MODERATE.value
            
    def calculate_action_priority(self, action_name: str, unit: Unit, assessment: TacticalAssessment) -> float:
        """Calculate priority score for an action (higher = better)"""
        base_priority = 0.5
        action = create_action_by_name(action_name)
        if not action:
            return 0.0
            
        # Factor in action weight (lighter actions are better when under pressure)
        weight_factor = 1.0 - (action.weight / 200.0)  # Normalize to 0-1
        if assessment.timeline_pressure > 0.5:
            base_priority += weight_factor * 0.3
            
        # Factor in personality preferences
        if self.personality == AIPersonality.AGGRESSIVE:
            if "Power" in action_name or "Charge" in action_name:
                base_priority += 0.3
        elif self.personality == AIPersonality.DEFENSIVE:
            if "Shield" in action_name or "Overwatch" in action_name:
                base_priority += 0.3
        elif self.personality == AIPersonality.OPPORTUNISTIC:
            if "Quick" in action_name and len(assessment.attack_opportunities) > 1:
                base_priority += 0.2
                
        # Factor in morale state
        try:
            morale = unit.morale.get_effective_morale()
            if morale < 40:  # Panicked units prefer quick, safe actions
                if "Quick" in action_name and "Move" in action_name:
                    base_priority += 0.4
                elif "Attack" in action_name:
                    base_priority -= 0.3
        except (AttributeError, KeyError):
            # Morale component might not exist on all units
            pass
                    
        return max(0.0, min(1.0, base_priority))


class BasicAI(AIController):
    """Basic AI implementation for general purpose units"""
    
    def choose_action(self, unit: Unit, game_map: GameMap, timeline: Timeline) -> AIDecision:
        """Choose action using basic tactical AI"""
        assessment = self.assess_situation(unit, game_map, timeline)
        available_actions = get_available_actions(unit)
        
        # Check if we should use an interrupt
        if self.should_use_interrupt(unit, assessment):
            interrupt_actions = [action for action in available_actions if "Overwatch" in action.name or "Shield" in action.name]
            if interrupt_actions:
                best_interrupt = max(interrupt_actions, 
                                   key=lambda a: self.calculate_action_priority(a.name, unit, assessment))
                return AIDecision(
                    action_name=best_interrupt.name,
                    confidence=0.7,
                    reasoning=f"Preparing interrupt due to {len(assessment.interrupt_threats)} threats",
                    expected_outcome="Defensive positioning with interrupt ready"
                )
        
        # Look for attack opportunities
        if assessment.attack_opportunities:
            target, best_attack_name = max(assessment.attack_opportunities,
                                         key=lambda x: self.calculate_action_priority(x[1], unit, assessment))
            
            return AIDecision(
                action_name=best_attack_name,
                target=target.position,
                confidence=0.8,
                reasoning=f"Attacking {target.name} with {best_attack_name}",
                expected_outcome=f"Deal damage to {target.name}"
            )
            
        # Move to a better position if no immediate threats
        if assessment.safe_positions and assessment.threat_level.value <= ThreatLevel.MODERATE.value:
            move_actions = [action for action in available_actions if "Move" in action.name]
            if move_actions:
                best_move = max(move_actions,
                              key=lambda a: self.calculate_action_priority(a.name, unit, assessment))
                target_pos = random.choice(assessment.safe_positions)
                
                return AIDecision(
                    action_name=best_move.name,
                    target=target_pos,
                    confidence=0.6,
                    reasoning="Moving to better tactical position",
                    expected_outcome="Improved positioning for next turn"
                )
        
        # Default to a standard attack if available
        attack_actions = [action for action in available_actions if "Attack" in action.name]
        if attack_actions and assessment.nearby_enemies:
            attack_action = random.choice(attack_actions)
            target = random.choice(assessment.nearby_enemies)
            
            return AIDecision(
                action_name=attack_action.name,
                target=target.position,
                confidence=0.4,
                reasoning="No clear tactical advantage, attacking randomly",
                expected_outcome="Deal damage to nearby enemy"
            )
            
        # Last resort - find any move action
        move_actions = [action for action in available_actions if "Move" in action.name]
        if move_actions:
            move_action = move_actions[0]  # Use first available move
            return AIDecision(
                action_name=move_action.name,
                target=Vector2(unit.position.y + random.randint(-1, 1), 
                              unit.position.x + random.randint(-1, 1)),
                confidence=0.3,
                reasoning="No good options available, moving randomly",
                expected_outcome="Reposition for future opportunities"
            )
        
        # Absolute last resort - wait
        return AIDecision(
            action_name="Wait",
            confidence=0.1,
            reasoning="No actions available",
            expected_outcome="Skip turn"
        )
        
    def assess_situation(self, unit: Unit, game_map: GameMap, timeline: Timeline) -> TacticalAssessment:
        """Analyze the tactical situation around the unit"""
        # Use Unit's direct component access
        if not unit.is_alive:
            return TacticalAssessment(ThreatLevel.LOW)
            
        nearby_enemies = []
        nearby_allies = []
        attack_opportunities = []
        interrupt_threats = []
        safe_positions = []
        
        # Scan nearby units (within 4 tiles)
        for other_unit in game_map.units:
            if other_unit.unit_id == unit.unit_id:
                continue
                
            distance = unit.position.manhattan_distance_to(other_unit.position)
            if distance <= 4 and other_unit.is_alive:
                if other_unit.team != unit.team:
                    nearby_enemies.append(other_unit)
                    
                    # Check if we can attack this enemy
                    if distance <= 2:  # Within attack range
                        attack_opportunities.append((other_unit, "Attack"))
                        if distance == 1:  # Adjacent enemies are interrupt threats
                            interrupt_threats.append(other_unit)
                else:
                    nearby_allies.append(other_unit)
        
        # Find safe positions (not adjacent to enemies)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                pos = Vector2(unit.position.y + dy, unit.position.x + dx)
                if game_map.is_valid_position(pos) and not game_map.get_unit_at(pos):
                    # Check if position is safe from enemies
                    is_safe = True
                    for enemy in nearby_enemies:
                        if pos.manhattan_distance_to(enemy.position) <= 1:
                            is_safe = False
                            break
                    if is_safe:
                        safe_positions.append(pos)
        
        # Determine threat level
        threat_level = ThreatLevel.LOW
        if len(nearby_enemies) >= 3:
            threat_level = ThreatLevel.CRITICAL
        elif len(nearby_enemies) >= 2:
            threat_level = ThreatLevel.HIGH
        elif len(nearby_enemies) >= 1:
            threat_level = ThreatLevel.MODERATE
            
        # Calculate timeline pressure based on upcoming enemy actions
        timeline_pressure = 0.0
        try:
            preview = timeline.get_preview(5)  # Look at next 5 timeline entries
            enemy_actions_soon = 0
            for entry in preview:
                if entry.entity_type == "unit":
                    entry_unit = game_map.get_unit(entry.entity_id)
                    assert entry_unit is not None, f"Timeline entry references non-existent unit: {entry.entity_id}"
                    if entry_unit.team != unit.team:
                        enemy_actions_soon += 1
                        
            timeline_pressure = min(1.0, enemy_actions_soon / 3.0)
        except (AttributeError, IndexError):
            # Timeline preview might not be available
            timeline_pressure = 0.0
        
        return TacticalAssessment(
            threat_level=threat_level,
            nearby_enemies=nearby_enemies,
            nearby_allies=nearby_allies,
            safe_positions=safe_positions,
            attack_opportunities=attack_opportunities,
            interrupt_threats=interrupt_threats,
            timeline_pressure=timeline_pressure
        )


def create_ai_for_unit(unit: Unit, personality: Optional[AIPersonality] = None) -> AIController:
    """Factory function to create appropriate AI for a unit"""
    if personality is None:
        # Assign personality based on unit class
        unit_class_name = unit.actor.unit_class.name
        if unit_class_name in ["KNIGHT", "WARRIOR"]:
            personality = AIPersonality.AGGRESSIVE
        elif unit_class_name in ["ARCHER", "MAGE"]:
            personality = AIPersonality.OPPORTUNISTIC
        elif unit_class_name == "PRIEST":
            personality = AIPersonality.DEFENSIVE
        else:
            personality = AIPersonality.BALANCED
            
    return BasicAI(personality)