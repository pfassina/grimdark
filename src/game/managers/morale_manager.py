"""Morale management system for grimdark battlefield psychology.

This manager handles all morale-related calculations, event processing,
and integration with the combat system. It implements the grimdark principle
that battles are as much about breaking the enemy's will as their bodies.
"""

from typing import TYPE_CHECKING, Optional

from ...core.events import (
    MoraleChanged, UnitPanicked, UnitRouted, UnitRallied,
    UnitDamaged, UnitDefeated, BattlePhaseChanged, LogMessage,
    EventType, GameEvent
)
from ...core.data import Vector2, PanicTrigger, ComponentType
from .log_manager import LogLevel

if TYPE_CHECKING:
    from ...core.engine.game_state import GameState
    from ...core.events.event_manager import EventManager
    from ..map import GameMap
    from ..entities.unit import Unit


class MoraleManager:
    """Manager for morale and panic system integration.
    
    This manager coordinates morale effects across the battlefield,
    handles morale events, and integrates with other game systems
    to create realistic battlefield psychology.
    """
    
    def __init__(self, game_state: "GameState", game_map: "GameMap", event_manager: "EventManager"):
        """Initialize morale manager.
        
        Args:
            game_state: Reference to the main game state
            game_map: Reference to the game map containing units
            event_manager: Event manager for publishing and subscribing to events
        """
        self.game_state = game_state
        self.game_map = game_map
        self.event_manager = event_manager
        self.current_turn = 0
        
        # Set up event subscriptions
        self._setup_event_subscriptions()
        
        # Morale effect configurations
        self.damage_morale_ratio = 0.5  # Morale loss per damage point
        self.ally_death_penalty = -15   # Morale loss when ally dies nearby
        self.enemy_death_bonus = 5      # Morale gain when enemy dies nearby
        self.proximity_radius = 3       # Range for ally/enemy death effects
        
    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for morale manager."""
        # Subscribe to damage events to trigger morale effects
        self.event_manager.subscribe(EventType.UNIT_DAMAGED, self._on_unit_damaged)
        
        # Subscribe to unit death events to process nearby morale effects
        self.event_manager.subscribe(EventType.UNIT_DEFEATED, self._on_unit_defeated)
        
        # Subscribe to battle phase changes for morale updates
        self.event_manager.subscribe(EventType.BATTLE_PHASE_CHANGED, self._on_battle_phase_changed)
        
    def _emit_log(self, message: str, category: str = "MORALE", level: str = "INFO") -> None:
        """Emit a log message event."""
        # Map string level to LogLevel enum
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR
        }
        log_level = level_map.get(level, LogLevel.INFO)
        
        self.event_manager.publish(
            LogMessage(
                timeline_time=self.game_state.battle.timeline.current_time,
                message=message,
                category=category,
                level=log_level,
                source="MoraleManager"
            ),
            source="MoraleManager"
        )
        
    def _on_unit_damaged(self, event: GameEvent) -> None:
        """Handle unit damaged event for morale processing."""
        assert isinstance(event, UnitDamaged), f"Expected UnitDamaged, got {type(event)}"
        # The event already has the unit that took damage
        unit = event.unit
        # Process morale effects from damage
        self.process_unit_damage(unit, event.damage)
    
    def _on_unit_defeated(self, event: GameEvent) -> None:
        """Handle unit defeated event for morale processing."""
        assert isinstance(event, UnitDefeated), f"Expected UnitDefeated, got {type(event)}"
        # Process morale effects from death using the unit directly from the event
        self.process_unit_death(event.unit)
    
    def _on_battle_phase_changed(self, event: GameEvent) -> None:
        """Handle battle phase change for morale processing."""
        assert isinstance(event, BattlePhaseChanged), f"Expected BattlePhaseChanged, got {type(event)}"
        # Update all units' proximity modifiers when phase changes
        for unit in self.game_map.units:
            self._update_proximity_modifiers(unit)
        
    def process_unit_damage(self, unit: "Unit", damage: int, attacker: Optional["Unit"] = None) -> None:
        """Process morale effects when a unit takes damage.
        
        Args:
            unit: Unit that took damage
            damage: Amount of damage taken
            attacker: Optional unit that dealt the damage
        """
        morale = unit.morale
        
        # Calculate morale loss from damage
        morale_loss = int(damage * self.damage_morale_ratio)
        if morale_loss > 0:
            old_morale = morale.get_effective_morale()
            actual_change = morale.modify_morale(-morale_loss, "took_damage")
            
            # Emit morale changed event if significant
            if abs(actual_change) >= 5:
                self._emit_morale_event(unit, old_morale, morale.get_effective_morale())
        
        # Heavy damage triggers additional panic checks
        if damage >= 15:  # Heavy damage threshold
            self._check_heavy_damage_panic(unit, damage)
    
    def process_unit_death(self, deceased: "Unit", killer: Optional["Unit"] = None) -> None:
        """Process morale effects when a unit dies.
        
        Args:
            deceased: Unit that was killed
            killer: Optional unit that killed the unit
        """
        deceased_actor = deceased.actor
        deceased_position = deceased.position
            
        # Find all units within proximity radius
        nearby_units = self._get_units_in_range(deceased_position, self.proximity_radius)
        
        for unit in nearby_units:
            actor = unit.actor
            morale = unit.morale
                
            # Skip if this is the unit that died
            if unit == deceased:
                continue
            
            old_morale = morale.get_effective_morale()
            
            # Ally death causes morale loss
            if actor.is_ally_of(deceased_actor):
                actual_change = morale.modify_morale(self.ally_death_penalty, "ally_death")
                
                # Check for panic from witnessing ally death
                if morale.get_effective_morale() <= morale.panic_threshold:
                    self._trigger_panic(unit, "ally_death")
                    
            # Enemy death causes morale gain
            else:
                actual_change = morale.modify_morale(self.enemy_death_bonus, "enemy_death")
            
            # Emit morale event if significant change
            if abs(actual_change) >= 3:
                self._emit_morale_event(unit, old_morale, morale.get_effective_morale())
    
    def process_turn_start(self, turn: int) -> None:
        """Process morale effects at the start of each turn.
        
        Args:
            turn: Current turn number
        """
        self.current_turn = turn
        
        # Process ongoing morale effects for all units
        for unit in self.game_map.units:
            if unit.has_component(ComponentType.MORALE):
                unit.morale.process_turn_effects()
                
                # Update proximity-based morale modifiers
                self._update_proximity_modifiers(unit)
    
    def attempt_rally_unit(self, unit: "Unit", rallier: Optional["Unit"] = None) -> bool:
        """Attempt to rally a unit out of panic.
        
        Args:
            unit: Unit to attempt rallying
            rallier: Optional unit performing the rally (affects bonus)
            
        Returns:
            True if rally was successful
        """
        if not unit.has_component(ComponentType.MORALE):
            return False
            
        morale = unit.morale
        
        # Calculate rally bonus based on rallier
        rally_bonus = 15  # Base rally bonus
        if rallier:
            rallier_actor = rallier.actor
            # Leaders and priests get bonus to rallying
            if rallier_actor.unit_class.name in ["PRIEST", "KNIGHT"]:
                rally_bonus += 10
        
        success = morale.attempt_rally(self.current_turn, rally_bonus)
        
        if success:
            self._emit_rally_event(unit)
        
        return success
    
    def get_morale_combat_modifiers(self, unit: "Unit") -> dict[str, int]:
        """Get combat modifiers due to morale state.
        
        Args:
            unit: Unit to get modifiers for
            
        Returns:
            Dictionary of modifier types and values
        """
        if not unit.has_component(ComponentType.MORALE):
            return {}
            
        return unit.morale.get_combat_penalties()
    
    def should_unit_flee(self, unit: "Unit") -> bool:
        """Check if a unit should attempt to flee from combat.
        
        Args:
            unit: Unit to check
            
        Returns:
            True if unit should flee
        """
        if not unit.has_component(ComponentType.MORALE):
            return False
            
        return unit.morale.should_flee_from_combat()
    
    def _check_heavy_damage_panic(self, unit: "Unit", damage: int) -> None:
        """Check if heavy damage triggers panic.
        
        Args:
            unit: Unit that took heavy damage
            damage: Amount of damage taken
        """
        if not unit.has_component(ComponentType.MORALE):
            return
            
        morale = unit.morale
        
        # Heavy damage can trigger immediate panic regardless of current morale
        if damage >= 20 and not morale.is_panicked:
            # Additional morale loss for traumatic damage
            trauma_penalty = -10
            morale.modify_morale(trauma_penalty, "traumatic_damage")
            
            if morale.get_effective_morale() <= morale.panic_threshold + 10:
                self._trigger_panic(unit, "heavy_damage")
    
    def _trigger_panic(self, unit: "Unit", reason: str) -> None:
        """Trigger panic state for a unit.
        
        Args:
            unit: Unit to panic
            reason: Reason for panic
        """
        if not unit.has_component(ComponentType.MORALE):
            return
            
        morale = unit.morale
        
        if not morale.is_panicked:
            morale.enter_panic_state(reason)
            self._emit_panic_event(unit, reason)
            
            # Check for immediate rout
            if morale.get_effective_morale() <= morale.rout_threshold:
                self._trigger_rout(unit)
    
    def _trigger_rout(self, unit: "Unit") -> None:
        """Trigger rout state for a unit.
        
        Args:
            unit: Unit to rout
        """
        if not unit.has_component(ComponentType.MORALE):
            return
            
        morale = unit.morale
        
        if not morale.is_routed:
            morale.enter_rout_state()
            self._emit_rout_event(unit)
    
    def _update_proximity_modifiers(self, unit: "Unit") -> None:
        """Update morale modifiers based on nearby units.
        
        Args:
            unit: Unit to update modifiers for
        """
        if not unit.has_component(ComponentType.MORALE):
            return
            
        morale = unit.morale
        actor = unit.actor
        position = unit.position
        
        # Clear old proximity modifiers
        morale.remove_temporary_modifier("nearby_allies")
        morale.remove_temporary_modifier("outnumbered")
        morale.remove_temporary_modifier("surrounded")
        
        # Count nearby allies and enemies
        nearby_units = self._get_units_in_range(position, 2)  # Closer proximity for these effects
        ally_count = 0
        enemy_count = 0
        
        for nearby_unit in nearby_units:
            if nearby_unit != unit and nearby_unit.has_component(ComponentType.ACTOR):
                nearby_actor = nearby_unit.actor
                if actor.is_ally_of(nearby_actor):
                    ally_count += 1
                else:
                    enemy_count += 1
        
        # Apply proximity modifiers
        if ally_count >= 2:
            morale.add_temporary_modifier("nearby_allies", 5)
        
        if enemy_count >= ally_count + 2:
            morale.add_temporary_modifier("outnumbered", -5)
        
        if enemy_count >= 3 and ally_count == 0:
            morale.add_temporary_modifier("surrounded", -10)
    
    
    def _get_units_in_range(self, center: Vector2, radius: int) -> list["Unit"]:
        """Get all units within range of a position.
        
        Args:
            center: Center position
            radius: Search radius (Manhattan distance)
            
        Returns:
            List of units within range
        """
        units_in_range = []
        
        for unit in self.game_map.units:
            position = unit.position  # Unit objects have direct position access
            if position.manhattan_distance_to(center) <= radius:
                units_in_range.append(unit)  # Return the unit directly
        
        return units_in_range
    
    def _emit_morale_event(self, unit: "Unit", old_morale: int, new_morale: int) -> None:
        """Emit morale changed event.
        
        Args:
            unit: Unit whose morale changed
            old_morale: Previous morale value
            new_morale: New morale value
        """
        
        event = MoraleChanged(
            timeline_time=self.game_state.battle.timeline.current_time,
            unit=unit,
            old_morale=old_morale,
            new_morale=new_morale
        )
        self.event_manager.publish(event, source="MoraleManager")
    
    def _emit_panic_event(self, unit: "Unit", reason: str) -> None:
        """Emit unit panicked event.
        
        Args:
            unit: Unit that panicked
            reason: Reason for panic
        """
        
        # Map reason string to PanicTrigger enum
        trigger_map = {
            "low morale": PanicTrigger.LOW_MORALE,
            "ally death": PanicTrigger.ALLY_DEATH,
            "heavy damage": PanicTrigger.HEAVY_DAMAGE,
            "overwhelming odds": PanicTrigger.OVERWHELMING_ODDS
        }
        trigger = trigger_map.get(reason.lower(), PanicTrigger.LOW_MORALE)
        
        event = UnitPanicked(
            timeline_time=self.game_state.battle.timeline.current_time,
            unit=unit,
            trigger=trigger
        )
        self.event_manager.publish(event, source="MoraleManager")
        
        # Log the panic event
        self._emit_log(f"{unit.name}: Panicked ({reason})", "BATTLE")
    
    def _emit_rout_event(self, unit: "Unit") -> None:
        """Emit unit routed event.
        
        Args:
            unit: Unit that routed
        """
        
        event = UnitRouted(
            timeline_time=self.game_state.battle.timeline.current_time,
            unit=unit
        )
        self.event_manager.publish(event, source="MoraleManager")
        
        # Log the rout event
        self._emit_log(f"{unit.name}: Routed (fleeing battlefield)", "BATTLE")
    
    def _emit_rally_event(self, unit: "Unit") -> None:
        """Emit unit rallied event.
        
        Args:
            unit: Unit that rallied
        """
        
        event = UnitRallied(
            timeline_time=self.game_state.battle.timeline.current_time,
            unit=unit
        )
        self.event_manager.publish(event, source="MoraleManager")
        
        # Log the rally event
        self._emit_log(f"{unit.name}: Rallied (regained courage)", "BATTLE")