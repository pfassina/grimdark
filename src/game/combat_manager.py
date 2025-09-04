"""
Combat management system for targeting, validation, and combat orchestration.

This module handles combat UI, targeting logic, and coordinates between
combat resolution and the game state.
"""
from typing import TYPE_CHECKING, Optional, Callable

from ..core.data_structures import Vector2, VectorArray

if TYPE_CHECKING:
    from .map import GameMap
    from .unit import Unit
    from ..core.game_state import GameState

from .battle_calculator import BattleCalculator
from .combat_resolver import CombatResolver, CombatResult


class CombatManager:
    """Manages combat targeting, validation, and execution orchestration."""
    
    def __init__(
        self, 
        game_map: "GameMap", 
        game_state: "GameState",
        event_emitter: Optional[Callable] = None
    ):
        self.game_map = game_map
        self.state = game_state
        self.resolver = CombatResolver(game_map)
        self.calculator = BattleCalculator()
        self.emit_event = event_emitter or (lambda _: None)
        
    def setup_attack_targeting(self, unit: "Unit") -> None:
        """Set up attack targeting for a unit."""
        # Clear movement range and set attack range
        self.state.battle.movement_range = VectorArray()
        attack_range = self.game_map.calculate_attack_range(unit)
        self.state.battle.set_attack_range(attack_range)
        
        # Set up targetable enemies for cycling
        self.refresh_targetable_enemies(unit)
        
        # Position cursor on closest target
        self.position_cursor_on_closest_target(unit)
        
        # Update targeting and AOE
        self.update_attack_targeting()
    
    def update_attack_targeting(self) -> None:
        """Update attack targeting based on cursor position."""
        if not self.state.battle.attack_range:
            return

        cursor_pos = self.state.cursor.position

        # Check if cursor is over a valid attack target
        if cursor_pos in self.state.battle.attack_range:
            self.state.battle.selected_target = cursor_pos

            # Calculate AOE tiles if we have a selected unit
            if self.state.battle.selected_unit_id:
                unit = self.game_map.get_unit(self.state.battle.selected_unit_id)
                if unit and hasattr(unit.combat, "aoe_pattern"):
                    aoe_pattern = unit.combat.aoe_pattern
                    self.state.battle.aoe_tiles = self.game_map.calculate_aoe_tiles(
                        cursor_pos, aoe_pattern
                    )
                else:
                    self.state.battle.aoe_tiles = VectorArray([cursor_pos])
        else:
            self.state.battle.selected_target = None
            self.state.battle.aoe_tiles = VectorArray()
    
    def execute_attack_at_cursor(self) -> bool:
        """
        Execute AOE attack centered on cursor position.
        
        Returns:
            True if attack was executed, False if invalid or cancelled
        """
        cursor_position = self.state.cursor.position

        if not self.state.battle.is_in_attack_range(cursor_position):
            return False

        if not self.state.battle.selected_unit_id:
            return False

        attacker = self.game_map.get_unit(self.state.battle.selected_unit_id)
        if not attacker:
            return False
        
        # Execute attack using resolver
        result = self.resolver.execute_aoe_attack(
            attacker, 
            cursor_position, 
            attacker.combat.aoe_pattern
        )
        
        # Must have at least one valid target to attack
        if not result.targets_hit:
            return False
        
        # If there are friendly units that will be hit, request confirmation
        if result.friendly_fire:
            friendly_names = [t.name for t in result.targets_hit if t.team == attacker.team]
            self._store_friendly_fire_confirmation(cursor_position, result, friendly_names)
            return False  # Wait for confirmation
        
        # No friendly fire, complete the attack
        self._complete_attack(attacker, result)
        return True
    
    def execute_confirmed_attack(self) -> bool:
        """Execute an attack that was confirmed by the player after friendly fire warning."""
        if not self.state.battle.selected_unit_id:
            return False

        attacker = self.game_map.get_unit(self.state.battle.selected_unit_id)
        if not attacker:
            return False
        
        # Get the stored attack data
        pending_attack = self.state.state_data.get("pending_attack")
        if not pending_attack:
            return False
        
        # Recreate the combat result from stored data
        result = CombatResult()
        result.targets_hit = pending_attack["targets_hit"]
        
        # Apply damage using resolver's method
        self.resolver._apply_damage_to_targets(attacker, result)
        
        # Clear the stored attack data
        self._clear_friendly_fire_data()
        
        # Complete attack processing
        self._complete_attack(attacker, result)
        return True
    
    def refresh_targetable_enemies(self, attacking_unit: "Unit") -> None:
        """Update the list of targetable enemy units (for tab cycling - only enemies)."""
        attack_range = self.game_map.calculate_attack_range(attacking_unit)
        
        targetable_ids = []
        for position in attack_range:
            target_unit = self.game_map.get_unit_at(position)
            # Only include enemy units for tab cycling, not friendlies
            if (
                target_unit
                and target_unit.unit_id != attacking_unit.unit_id
                and target_unit.team != attacking_unit.team
            ):
                targetable_ids.append(target_unit.unit_id)
        
        self.state.battle.set_targetable_enemies(targetable_ids)
    
    def position_cursor_on_closest_target(self, attacking_unit: "Unit") -> None:
        """Position cursor on the closest targetable enemy unit."""
        if not self.state.battle.targetable_enemies:
            return
        
        closest_target = None
        closest_distance = float("inf")
        
        # Find the closest targetable enemy unit
        for target_id in self.state.battle.targetable_enemies:
            target_unit = self.game_map.get_unit(target_id)
            if target_unit:
                # Calculate Manhattan distance
                distance = attacking_unit.position.manhattan_distance_to(target_unit.position)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_target = target_unit
        
        # Position cursor on closest target
        if closest_target:
            self.state.cursor.set_position(closest_target.position)

            # Update the target index to match the cursor position
            try:
                target_index = self.state.battle.targetable_enemies.index(
                    closest_target.unit_id
                )
                self.state.battle.current_target_index = target_index
            except ValueError:
                pass  # Target not in list, keep current index
    
    def cycle_targetable_enemies(self) -> bool:
        """
        Cycle through targetable enemy units (for tab cycling).
        
        Returns:
            True if cursor was moved to a new target
        """
        if not self.state.battle.selected_unit_id:
            return False
            
        unit = self.game_map.get_unit(self.state.battle.selected_unit_id)
        if not unit:
            return False
        
        # Get all targetable enemy units if not already set
        if not self.state.battle.targetable_enemies:
            self.refresh_targetable_enemies(unit)
        
        # Cycle to next target
        next_target_id = self.state.battle.cycle_targetable_enemies()
        if next_target_id:
            target_unit = self.game_map.get_unit(next_target_id)
            if target_unit:
                self.state.cursor.set_position(target_unit.position)
                return True
        
        return False
    
    def get_battle_forecast(self, attacker: "Unit", defender: "Unit") -> Optional[object]:
        """Get battle forecast data for UI display."""
        if not attacker or not defender:
            return None
        return self.calculator.calculate_forecast(attacker, defender)
    
    def _store_friendly_fire_confirmation(
        self, 
        cursor_position: Vector2, 
        result: CombatResult, 
        friendly_names: list[str]
    ) -> None:
        """Store attack data for friendly fire confirmation."""
        if len(friendly_names) == 1:
            self.state.state_data["friendly_fire_message"] = (
                f"This attack will hit your ally {friendly_names[0]}!"
            )
        else:
            self.state.state_data["friendly_fire_message"] = (
                f"This attack will hit your allies: {', '.join(friendly_names)}!"
            )
        
        # Store the attack data for later execution
        self.state.state_data["pending_attack"] = {
            "cursor_position": cursor_position,
            "targets_hit": result.targets_hit,
        }
        
        self.state.ui.open_dialog("confirm_friendly_fire")
    
    def _clear_friendly_fire_data(self) -> None:
        """Clear stored friendly fire confirmation data."""
        if "pending_attack" in self.state.state_data:
            del self.state.state_data["pending_attack"]
        if "friendly_fire_message" in self.state.state_data:
            del self.state.state_data["friendly_fire_message"]
    
    def _complete_attack(self, attacker: "Unit", result: CombatResult) -> None:
        """Complete attack processing after damage has been applied."""
        # Emit defeat events for any defeated units
        for target_name in result.defeated_targets:
            target = next((t for t in result.targets_hit if t.name == target_name), None)
            position = result.defeated_positions.get(target_name, (0, 0))
            if target:
                defeat_event = self.resolver.create_defeat_event(
                    target.name, target.team, position, self.state.battle.current_turn
                )
                self.emit_event(defeat_event)
        
        # Mark attacker as having acted and moved (can't do anything else)
        attacker.has_moved = True  # Prevent further movement after attacking
        attacker.has_acted = True  # Prevent further actions
        
    def clear_attack_state(self) -> None:
        """Clear all attack-related state data."""
        self.state.battle.attack_range = VectorArray()
        self.state.battle.aoe_tiles = VectorArray()
        self.state.battle.targetable_enemies.clear()
        self.state.battle.current_target_index = 0
        self.state.battle.selected_target = None
