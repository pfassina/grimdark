"""Combat system components.

This package contains the core combat logic with clear separation of concerns:
- battle_calculator.py: Damage prediction and read-only calculations  
- combat_resolver.py: Actual damage application and wound generation
"""

from .battle_calculator import BattleCalculator
from .combat_resolver import CombatResolver, CombatResult

__all__ = [
    "BattleCalculator",
    "CombatResolver",
    "CombatResult",
]