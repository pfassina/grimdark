"""
Combat management system for targeting, validation, and combat orchestration.

This module handles combat UI, targeting logic, and coordinates between
combat resolution and the game state.
"""
from typing import TYPE_CHECKING, Optional

from ...core.data import VectorArray

if TYPE_CHECKING:
    from ..map import GameMap
    from ..entities.unit import Unit
    from ...core.engine.game_state import GameState
    from ...core.events.event_manager import EventManager

from ..combat import BattleCalculator
from ...core.engine import BattlePhase
from ...core.events import (
    ActionExecuted, AttackTargetingSetup, ManagerInitialized, EventType, UnitTurnEnded
)


class CombatManager:
    """Manages combat targeting, validation, and execution orchestration."""
    
    def __init__(
        self, 
        game_map: "GameMap", 
        game_state: "GameState",
        event_manager: "EventManager"
    ):
        self.game_map = game_map
        self.state = game_state
        self.event_manager = event_manager
        self.calculator = BattleCalculator()
        
        # Subscribe to cursor movement events for real-time targeting updates
        self.event_manager.subscribe(
            EventType.CURSOR_MOVED,
            self._handle_cursor_moved,
            subscriber_name="CombatManager.cursor_moved"
        )
        
        # Subscribe to action completion events to clear attack state
        self.event_manager.subscribe(
            EventType.ACTION_EXECUTED,
            self._handle_action_executed,
            subscriber_name="CombatManager.action_executed"
        )
        self.event_manager.subscribe(
            EventType.UNIT_TURN_ENDED,
            self._handle_unit_turn_ended,
            subscriber_name="CombatManager.unit_turn_ended"
        )
        
        # Emit initialization event
        self.event_manager.publish(
            ManagerInitialized(timeline_time=0, manager_name="CombatManager"),
            source="CombatManager"
        )
        
    def _handle_cursor_moved(self, event) -> None:
        """Handle cursor movement events to update targeting in real-time."""
        # Only update targeting if we're in attack targeting mode and have attack range set
        if (self.state.battle.phase in [BattlePhase.ACTION_EXECUTION, BattlePhase.ACTION_TARGETING] 
            and self.state.battle.attack_range 
            and event.context == "targeting"):
            self.update_attack_targeting()
    
    def _handle_action_executed(self, event) -> None:
        """Handle action execution completion to clear attack state."""
        assert isinstance(event, ActionExecuted), f"Expected ActionExecuted, got {type(event)}"
        
        # Clear attack state after any action is executed
        self.clear_attack_state()
    
    def _handle_unit_turn_ended(self, event) -> None:
        """Handle unit turn ending to clear attack state."""
        assert isinstance(event, UnitTurnEnded), f"Expected UnitTurnEnded, got {type(event)}"
        
        # Clear attack state when a unit's turn ends
        self.clear_attack_state()
        
    def setup_attack_targeting(self, unit: "Unit") -> None:
        """Set up attack targeting for a unit."""
        # Clear movement range when entering attack targeting and set attack range
        self.state.battle.movement_range = VectorArray()
        attack_range = self.game_map.calculate_attack_range(unit)
        self.state.battle.set_attack_range(attack_range)
        
        # Set up targetable enemies for cycling
        self.refresh_targetable_enemies(unit)
        
        # Position cursor on closest target only if enemies are available
        if self.state.battle.targetable_enemies:
            self.position_cursor_on_closest_target(unit)
        
        # Update targeting and AOE
        self.update_attack_targeting()
        
        # Emit attack targeting setup event
        timeline_time = self.state.battle.timeline.current_time if self.state.battle else 0
        self.event_manager.publish(
            AttackTargetingSetup(
                timeline_time=timeline_time,
                attacker=unit,
                attack_range_size=len(attack_range),
                targetable_enemies=len(self.state.battle.targetable_enemies)
            ),
            source="CombatManager"
        )
    
    def update_attack_targeting(self) -> None:
        """Update attack targeting based on cursor position."""
        if not self.state.battle.attack_range:
            return

        # Refresh targetable enemies list to account for unit movement
        if self.state.battle.selected_unit_id:
            attacking_unit = self.game_map.get_unit(self.state.battle.selected_unit_id)
            if attacking_unit:
                self.refresh_targetable_enemies(attacking_unit)

        cursor_pos = self.state.cursor.position

        # Check if cursor is over a valid attack target
        if cursor_pos in self.state.battle.attack_range:
            self.state.battle.selected_target = cursor_pos
        else:
            self.state.battle.selected_target = None

        # Calculate AOE tiles for any position in attack range (including empty tiles)
        if cursor_pos in self.state.battle.attack_range and self.state.battle.selected_unit_id:
            unit = self.game_map.get_unit(self.state.battle.selected_unit_id)
            if unit is None:
                raise ValueError(f"Selected unit '{self.state.battle.selected_unit_id}' not found on map. UI state inconsistent with game state.")
            aoe_pattern = unit.combat.aoe_pattern
            aoe_tiles = self.game_map.calculate_aoe_tiles(cursor_pos, aoe_pattern)
            self.state.battle.aoe_tiles = aoe_tiles
            
            # Check for friendly fire preview (UI only, no events)
            targets_in_aoe = self.game_map.get_units_in_positions(aoe_tiles)
            friendly_targets = [t for t in targets_in_aoe if t.team == unit.team and t.unit_id != unit.unit_id]
            
            # Store friendly targets for UI highlighting (renderer will display them differently)
            self.state.battle.friendly_fire_preview = VectorArray([t.position for t in friendly_targets])
        else:
            self.state.battle.aoe_tiles = VectorArray()
            self.state.battle.friendly_fire_preview = VectorArray()
    
    def _update_aoe_tiles_only(self) -> None:
        """Update AOE tiles based on cursor position without refreshing targetable enemies."""
        if not self.state.battle.attack_range:
            return

        cursor_pos = self.state.cursor.position

        # Check if cursor is over a valid attack target
        if cursor_pos in self.state.battle.attack_range:
            self.state.battle.selected_target = cursor_pos
        else:
            self.state.battle.selected_target = None

        # Calculate AOE tiles for any position in attack range (including empty tiles)
        if cursor_pos in self.state.battle.attack_range and self.state.battle.selected_unit_id:
            unit = self.game_map.get_unit(self.state.battle.selected_unit_id)
            if unit is None:
                raise ValueError(f"Selected unit '{self.state.battle.selected_unit_id}' not found on map. UI state inconsistent with game state.")
            aoe_pattern = unit.combat.aoe_pattern
            self.state.battle.aoe_tiles = self.game_map.calculate_aoe_tiles(
                cursor_pos, aoe_pattern
            )
        else:
            self.state.battle.aoe_tiles = VectorArray()
    
    
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
        """Position cursor on the closest targetable enemy unit, or within attack range if no enemies."""
        if not self.state.battle.targetable_enemies:
            # No enemies available - position cursor on first attack range tile
            if self.state.battle.attack_range:
                first_target = self.state.battle.attack_range[0]  # VectorArray supports indexing
                self.state.cursor.set_position(first_target)
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
                # Update AOE tiles for the new cursor position without refreshing enemy list
                self._update_aoe_tiles_only()
                return True
        
        return False
    
    def get_battle_forecast(self, attacker: "Unit", defender: "Unit") -> Optional[object]:
        """Get battle forecast data for UI display."""
        if not attacker or not defender:
            return None
        return self.calculator.calculate_forecast(attacker, defender)
    
    def clear_attack_state(self) -> None:
        """Clear all attack-related state data."""
        self.state.battle.attack_range = VectorArray()
        self.state.battle.aoe_tiles = VectorArray()
        self.state.battle.friendly_fire_preview = VectorArray()
        self.state.battle.targetable_enemies.clear()
        self.state.battle.current_target_index = 0
        self.state.battle.selected_target = None
