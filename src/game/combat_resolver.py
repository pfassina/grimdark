"""
Combat resolution system for executing attacks and applying damage.

This module handles the actual combat execution and damage application,
separate from combat targeting and UI concerns.
"""
from typing import TYPE_CHECKING

import numpy as np

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
        Execute AOE attack centered on target position using vectorized operations.
        
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
        
        # Find all targets in AOE area using vectorized operations
        targets_in_aoe = self.game_map.get_units_in_positions(aoe_tiles)
        
        # Filter out the attacker and build target list
        result.targets_hit = [t for t in targets_in_aoe if t.unit_id != attacker.unit_id]
        
        # Vectorized friendly fire detection using team comparison
        if result.targets_hit:
            target_teams = np.array([t.team.value for t in result.targets_hit], dtype=np.int8)
            result.friendly_fire = bool(np.any(target_teams == attacker.team.value))
            
            # Apply damage to all targets
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
        """Apply damage to all targets and handle defeats using vectorized operations."""
        if not result.targets_hit:
            return
            
        # Vectorized damage calculation for all targets
        target_defenses = np.array([t.combat.defense for t in result.targets_hit], dtype=np.int16)
        damages = np.maximum(1, attacker.combat.strength - target_defenses // 2)
        
        # Vectorized HP updates
        current_hps = np.array([t.hp_current for t in result.targets_hit], dtype=np.int16)
        new_hps = np.maximum(0, current_hps - damages)
        
        # Boolean mask for defeated units
        defeated_mask = new_hps <= 0
        surviving_mask = ~defeated_mask
        
        # Process surviving units first (batch HP update)
        surviving_indices = np.where(surviving_mask)[0]
        for idx in surviving_indices:
            target = result.targets_hit[idx]
            damage = damages[idx]
            target.hp_current = new_hps[idx]
            result.damage_dealt[target.name] = int(damage)
            print(f"{attacker.name} attacks {target.name} for {damage} damage!")
        
        # Process defeated units in batch
        defeated_indices = np.where(defeated_mask)[0]
        if len(defeated_indices) > 0:
            # Collect all defeated unit info before removal
            defeated_unit_ids = []
            for idx in defeated_indices:
                target = result.targets_hit[idx]
                damage = damages[idx]
                target.hp_current = 0  # Ensure HP is 0
                result.damage_dealt[target.name] = int(damage)
                result.defeated_targets.append(target.name)
                result.defeated_positions[target.name] = (target.position.x, target.position.y)
                defeated_unit_ids.append(target.unit_id)
                print(f"{attacker.name} defeats {target.name}!")
            
            # Batch remove all defeated units in a single operation
            self.game_map.remove_units_batch(defeated_unit_ids)
        
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