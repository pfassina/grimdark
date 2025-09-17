"""
Combat resolution system for executing attacks and applying damage.

This module handles the actual combat execution and damage application,
separate from combat targeting and UI concerns.
"""
from typing import TYPE_CHECKING, Optional

import numpy as np

from ..core.data_structures import Vector2
from ..core.wounds import create_wound_from_damage, Wound
from ..core.events import EventType, UnitAttacked

if TYPE_CHECKING:
    from .map import GameMap
    from .unit import Unit
    from .morale_manager import MoraleManager
    from ..core.event_manager import EventManager

from ..core.events import UnitDefeated, LogMessage
from ..core.game_enums import Team


class CombatResult:
    """Result of a combat action."""
    
    def __init__(self):
        self.targets_hit: list["Unit"] = []
        self.defeated_targets: list[str] = []
        self.defeated_positions: dict[str, tuple[int, int]] = {}
        self.damage_dealt: dict[str, int] = {}
        self.wounds_inflicted: dict[str, list[Wound]] = {}  # unit_name -> list of wounds
        self.friendly_fire: bool = False


class CombatResolver:
    """Handles actual combat execution and damage application."""
    
    def __init__(
        self, 
        game_map: "GameMap", 
        event_manager: "EventManager",
        morale_manager: Optional["MoraleManager"] = None
    ):
        self.game_map = game_map
        self.event_manager = event_manager
        self.morale_manager = morale_manager
        
        # Subscribe to UnitAttacked events for proper combat processing
        self.event_manager.subscribe(
            EventType.UNIT_ATTACKED,
            self._handle_unit_attacked,
            subscriber_name="CombatResolver.unit_attacked"
        )
        self._emit_log("CombatResolver subscribed to UnitAttacked events", "COMBAT", "INFO")
    
    def _handle_unit_attacked(self, event) -> None:
        """Handle UnitAttacked events by processing damage and checking for defeats."""
        self._emit_log(f"CombatResolver received UnitAttacked event: {event.attacker_name} -> {event.target_name}", "COMBAT", "INFO")
        
        if not isinstance(event, UnitAttacked):
            return
            
        # Get the attacker and target units
        attacker = self.game_map.get_unit(event.attacker_id)
        target = self.game_map.get_unit(event.target_id)
        
        self._emit_log(f"Looking up units: attacker={attacker is not None}, target={target is not None}", "COMBAT", "INFO")

        if not attacker or not target:
            self._emit_log("UnitAttacked event references missing units", "COMBAT", "WARNING")
            return

        self._emit_log(f"Base damage: {event.base_damage}, multiplier: {event.damage_multiplier}", "COMBAT", "INFO")

        # Create a CombatResult and process the attack using proper combat mechanics
        result = CombatResult()
        result.targets_hit = [target]
        
        self._emit_log(f"About to apply damage to {target.name} using combat mechanics", "COMBAT", "INFO")

        # Apply damage using vectorized processing (this will calculate proper damage)
        self._apply_damage_to_targets(attacker, result)
        
        self._emit_log("Damage applied successfully", "COMBAT", "INFO")

        # Log the attack
        final_damage = int(event.base_damage * event.damage_multiplier)
        self._emit_log(
            f"{event.attacker_name} → {event.target_name} ({final_damage} damage, {event.attack_type})"
        )

    def _emit_log(self, message: str, category: str = "BATTLE", level: str = "INFO") -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=0,  # TODO: Get actual turn from game state
                message=message,
                category=category,
                level=level,
                source="CombatResolver"
            ),
            source="CombatResolver"
        )
        
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
            
            # Only apply damage if no friendly fire (damage will be applied later after confirmation)
            if not result.friendly_fire:
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
        
        # Only apply damage if no friendly fire (damage will be applied later after confirmation)
        if not result.friendly_fire:
            self._apply_damage_to_targets(attacker, result)
        return result
    
    def _apply_damage_to_targets(self, attacker: "Unit", result: CombatResult) -> None:
        """Apply damage to all targets and handle defeats using vectorized operations."""
        if not result.targets_hit:
            return
            
        # Vectorized damage calculation for all targets with variance
        target_defenses = np.array([t.combat.defense for t in result.targets_hit], dtype=np.int16)
        base_damages = np.maximum(1, attacker.combat.strength - target_defenses // 2)
        
        # Add damage variance (±25% of base damage, minimum 1)
        # This creates the chaos-from-damage-variance mentioned in design doc
        variance_ranges = np.maximum(1, base_damages // 4)  # 25% variance per target
        variances = np.random.randint(-variance_ranges, variance_ranges + 1)  # +1 for inclusive upper bound
        damages = np.maximum(1, base_damages + variances)
        
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
            
            # Generate wounds from damage dealt
            wound = create_wound_from_damage(
                damage=int(damage),
                damage_type="physical",  # TODO: Get actual damage type from weapon/attack
                target_unit=target,
                source_unit=attacker
            )
            if wound:
                # Store wound on the unit through its WoundComponent
                target.wound.add_wound(wound)
                
                # Also track in result for reporting
                if target.name not in result.wounds_inflicted:
                    result.wounds_inflicted[target.name] = []
                result.wounds_inflicted[target.name].append(wound)
                # Log wound information without stat penalty details for now
                self._emit_log(f"{target.name}: {wound.properties.wound_type.name.lower()} wound ({wound.properties.body_part.name.lower()})")
            
            # Process morale effects from taking damage
            if self.morale_manager:
                self.morale_manager.process_unit_damage(target.entity, int(damage), attacker.entity)
                
            self._emit_log(f"{attacker.name} → {target.name} ({damage} damage)")
        
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
                
                # Generate wounds from fatal damage (likely severe/critical wounds)
                wound = create_wound_from_damage(
                    damage=int(damage),
                    damage_type="physical",  # TODO: Get actual damage type from weapon/attack
                    target_unit=target,
                    source_unit=attacker
                )
                if wound:
                    # Store wound on the unit through its WoundComponent (even if defeated)
                    target.wound.add_wound(wound)
                    
                    # Also track in result for reporting
                    if target.name not in result.wounds_inflicted:
                        result.wounds_inflicted[target.name] = []
                    result.wounds_inflicted[target.name].append(wound)
                    self._emit_log(f"{target.name}: Fatal {wound.properties.wound_type.name.lower()} wound")
                
                # Process morale effects from taking fatal damage and dying
                if self.morale_manager:
                    self.morale_manager.process_unit_damage(target.entity, int(damage), attacker.entity)
                    self.morale_manager.process_unit_death(target.entity, attacker.entity)
                
                self._emit_log(f"{target.name}: Defeated")
                
                # Emit unit defeated event
                self.event_manager.publish(
                    UnitDefeated(
                        turn=0,  # TODO: Get actual turn
                        unit_name=target.name,
                        unit_id=target.unit_id,
                        team=target.team,
                        position=(target.position.x, target.position.y)
                    ),
                    source="CombatResolver"
                )
            
            # Batch remove all defeated units in a single operation
            self.game_map.remove_units_batch(defeated_unit_ids)
        
        # Show summary if multiple targets
        if len(result.targets_hit) > 1:
            self._emit_log(f"{attacker.name}: {attacker.combat.aoe_pattern} → {len(result.targets_hit)} targets")
    
    def create_defeat_event(
        self, 
        unit_name: str, 
        unit_id: str,
        team: Team, 
        position: tuple[int, int], 
        turn: int
    ) -> UnitDefeated:
        """Create a unit defeated event for the objective system."""
        return UnitDefeated(
            turn=turn,
            unit_name=unit_name,
            unit_id=unit_id,
            team=team,
            position=position,
        )