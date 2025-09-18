"""AI system components.

This package contains AI controller logic and behavior definitions:
- ai_controller.py: Timeline-aware AI with personality types and tactical assessment
- ai_behaviors.py: AI behavior patterns and decision-making logic
"""

from .ai_controller import AIController
from .ai_behaviors import AIBehavior, AggressiveAI, InactiveAI, AIType, create_ai_behavior

__all__ = [
    "AIController",
    "AIBehavior",
    "AggressiveAI", 
    "InactiveAI",
    "AIType",
    "create_ai_behavior",
]