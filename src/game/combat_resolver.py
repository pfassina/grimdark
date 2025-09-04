"""
Combat resolution system for executing attacks and applying damage.

This module handles the actual combat execution and damage application,
separate from combat targeting and UI concerns.
"""
from typing import TYPE_CHECKING

from ..core.data_structures import Vector2

if TYPE_CHECKING:
    from .map import GameMap
    from .unit import Unit

from ..core.events import UnitDefeated
from ..core.game_enums import Team


class CombatResult:
    """Result of a combat action."""
    
    def __init__(self):
        self.targets_hit: list["Unit"] = []
        self.defeated_targets: list[str] = []
        self.defeated_positions: dict[str, tuple[int, int]] = {}
        self.damage_dealt: dict[str, int] = {}
        self.friendly_fire: bool = False


class CombatResolver:
    """Handles actual combat execution and damage application."""
    
    def __init__(self, game_map: "GameMap"):
        self.game_map = game_map
        
    def execute_aoe_attack(
        self, 
        attacker: "Unit", 
        center_pos: Vector2, 
        aoe_pattern: str
    ) -> CombatResult:
        """
        Execute AOE attack centered on target position.
        
        Args:
            attacker: The unit performing the attack
            center_pos: Center position (x, y) of the attack
            aoe_pattern: AOE pattern type for damage calculation
            
        Returns:
            CombatResult with details of the attack resolution
        """
        result = CombatResult()
        
        # Calculate AOE tiles based on center position
        aoe_tiles = self.game_map.calculate_aoe_tiles(center_pos, aoe_pattern)
        
        # Find all targets in AOE area (both enemy and friendly)
        for position in aoe_tiles:
            target = self.game_map.get_unit_at(position)
            if target and target.unit_id != attacker.unit_id:
                result.targets_hit.append(target)
                
                # Check if target is on the same team as attacker (friendly fire)
                if target.team == attacker.team:
                    result.friendly_fire = True
        
        # Apply damage to all targets
        if result.targets_hit:
            self._apply_damage_to_targets(attacker, result)
            
        return result
    
    def execute_single_attack(
        self, 
        attacker: "Unit", 
        target: "Unit"
    ) -> CombatResult:
        """
        Execute single-target attack.
        
        Args:
            attacker: The unit performing the attack
            target: The target unit
            
        Returns:
            CombatResult with details of the attack resolution
        """
        result = CombatResult()
        result.targets_hit = [target]
        
        # Check for friendly fire
        if target.team == attacker.team:
            result.friendly_fire = True
            
        self._apply_damage_to_targets(attacker, result)
        return result
    
    def _apply_damage_to_targets(self, attacker: "Unit", result: CombatResult) -> None:
        """Apply damage to all targets and handle defeats."""
        for target in result.targets_hit:
            # Calculate damage (simple calculation)
            damage = max(1, attacker.combat.strength - target.combat.defense // 2)
            result.damage_dealt[target.name] = damage
            
            # Apply damage
            target.hp_current = max(0, target.hp_current - damage)
            
            # Check if target is defeated
            if target.hp_current <= 0:
                target_pos = target.position
                self.game_map.remove_unit(target.unit_id)
                result.defeated_targets.append(target.name)
                result.defeated_positions[target.name] = (target_pos.x, target_pos.y)
                print(f"{attacker.name} defeats {target.name}!")
            else:
                print(f"{attacker.name} attacks {target.name} for {damage} damage!")
        
        # Show summary if multiple targets
        if len(result.targets_hit) > 1:
            print(f"{attacker.name}'s {attacker.combat.aoe_pattern} attack hits {len(result.targets_hit)} targets!")
    
    def create_defeat_event(
        self, 
        unit_name: str, 
        team: Team, 
        position: tuple[int, int], 
        turn: int
    ) -> UnitDefeated:
        """Create a unit defeated event for the objective system."""
        return UnitDefeated(
            turn=turn,
            unit_name=unit_name,
            team=team,
            position=position,
        )