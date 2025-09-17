"""Morale management system for grimdark battlefield psychology.

This manager handles all morale-related calculations, event processing,
and integration with the combat system. It implements the grimdark principle
that battles are as much about breaking the enemy's will as their bodies.
"""

from typing import TYPE_CHECKING, Optional, cast

from ..core.events import (
    MoraleChanged, UnitPanicked, UnitRouted, UnitRallied,
    UnitTookDamage, UnitDefeated, BattlePhaseChanged, LogMessage,
    EventType, GameEvent
)
from ..core.data_structures import Vector2
from .components import MoraleComponent, ActorComponent, MovementComponent

if TYPE_CHECKING:
    from ..core.components import Entity
    from ..core.game_state import GameState
    from ..core.event_manager import EventManager
    from .map import GameMap


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
        self.event_manager.subscribe(EventType.UNIT_TOOK_DAMAGE, self._on_unit_took_damage)
        
        # Subscribe to unit death events to process nearby morale effects
        self.event_manager.subscribe(EventType.UNIT_DEFEATED, self._on_unit_defeated)
        
        # Subscribe to battle phase changes for morale updates
        self.event_manager.subscribe(EventType.BATTLE_PHASE_CHANGED, self._on_battle_phase_changed)
        
    def _emit_log(self, message: str, category: str = "MORALE", level: str = "INFO") -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=self.current_turn,
                message=message,
                category=category,
                level=level,
                source="MoraleManager"
            ),
            source="MoraleManager"
        )
        
    def _on_unit_took_damage(self, event: GameEvent) -> None:
        """Handle unit took damage event for morale processing."""
        assert isinstance(event, UnitTookDamage), f"Expected UnitTookDamage, got {type(event)}"
        # Find the unit that took damage
        for unit in self.game_map.units:
            actor = unit.entity.get_component("Actor")
            assert actor is not None, f"Unit {unit.unit_id} missing Actor component"
            assert isinstance(actor, ActorComponent), f"Actor component for {unit.unit_id} is not ActorComponent"
            if actor.name == event.unit_name:
                # Process morale effects from damage
                self.process_unit_damage(unit.entity, event.damage_amount)
                break
    
    def _on_unit_defeated(self, event: GameEvent) -> None:
        """Handle unit defeated event for morale processing."""
        assert isinstance(event, UnitDefeated), f"Expected UnitDefeated, got {type(event)}"
        # Find the defeated unit
        for unit in self.game_map.units:
            actor = unit.entity.get_component("Actor")
            assert actor is not None, f"Unit {unit.unit_id} missing Actor component"
            assert isinstance(actor, ActorComponent), f"Actor component for {unit.unit_id} is not ActorComponent"
            if actor.name == event.unit_name:
                # Process morale effects from death
                self.process_unit_death(unit.entity)
                break
    
    def _on_battle_phase_changed(self, event: GameEvent) -> None:
        """Handle battle phase change for morale processing."""
        assert isinstance(event, BattlePhaseChanged), f"Expected BattlePhaseChanged, got {type(event)}"
        # Update all units' proximity modifiers when phase changes
        for unit in self.game_map.units:
            self._update_proximity_modifiers(unit.entity)
        
    def process_unit_damage(self, entity: "Entity", damage: int, attacker: Optional["Entity"] = None) -> None:
        """Process morale effects when a unit takes damage.
        
        Args:
            entity: Unit that took damage
            damage: Amount of damage taken
            attacker: Optional entity that dealt the damage
        """
        morale_component = entity.get_component("Morale")
        if not morale_component:
            return
            
        morale = cast(MoraleComponent, morale_component)
        
        # Calculate morale loss from damage
        morale_loss = int(damage * self.damage_morale_ratio)
        if morale_loss > 0:
            old_morale = morale.get_effective_morale()
            actual_change = morale.modify_morale(-morale_loss, "took_damage")
            
            # Emit morale changed event if significant
            if abs(actual_change) >= 5:
                self._emit_morale_event(entity, old_morale, morale.get_effective_morale())
        
        # Heavy damage triggers additional panic checks
        if damage >= 15:  # Heavy damage threshold
            self._check_heavy_damage_panic(entity, damage)
    
    def process_unit_death(self, deceased: "Entity", killer: Optional["Entity"] = None) -> None:
        """Process morale effects when a unit dies.
        
        Args:
            deceased: Unit that was killed
            killer: Optional entity that killed the unit
        """
        deceased_actor_component = deceased.get_component("Actor")
        deceased_position = self._get_entity_position(deceased)
        
        if not deceased_actor_component or not deceased_position:
            return
        
        deceased_actor = cast(ActorComponent, deceased_actor_component)
            
        # Find all units within proximity radius
        nearby_units = self._get_units_in_range(deceased_position, self.proximity_radius)
        
        for unit in nearby_units:
            unit_actor = unit.get_component("Actor")
            unit_morale = unit.get_component("Morale")
            
            if not unit_actor or not unit_morale:
                continue
                
            actor = cast(ActorComponent, unit_actor)
            morale = cast(MoraleComponent, unit_morale)
                
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
            morale_component = unit.entity.get_component("Morale")
            if morale_component:
                morale = cast(MoraleComponent, morale_component)
                morale.process_turn_effects()
                
                # Update proximity-based morale modifiers
                self._update_proximity_modifiers(unit.entity)
    
    def attempt_rally_unit(self, entity: "Entity", rallier: Optional["Entity"] = None) -> bool:
        """Attempt to rally a unit out of panic.
        
        Args:
            entity: Unit to attempt rallying
            rallier: Optional unit performing the rally (affects bonus)
            
        Returns:
            True if rally was successful
        """
        morale_component = entity.get_component("Morale")
        if not morale_component:
            return False
            
        morale = cast(MoraleComponent, morale_component)
        
        # Calculate rally bonus based on rallier
        rally_bonus = 15  # Base rally bonus
        if rallier:
            rallier_actor = rallier.get_component("Actor")
            if rallier_actor:
                actor = cast('ActorComponent', rallier_actor)
                # Leaders and priests get bonus to rallying
                if actor.unit_class.name in ["PRIEST", "KNIGHT"]:
                    rally_bonus += 10
        
        success = morale.attempt_rally(self.current_turn, rally_bonus)
        
        if success:
            self._emit_rally_event(entity)
        
        return success
    
    def get_morale_combat_modifiers(self, entity: "Entity") -> dict[str, int]:
        """Get combat modifiers due to morale state.
        
        Args:
            entity: Unit to get modifiers for
            
        Returns:
            Dictionary of modifier types and values
        """
        morale_component = entity.get_component("Morale")
        if not morale_component:
            return {}
            
        morale = cast(MoraleComponent, morale_component)
        return morale.get_combat_penalties()
    
    def should_unit_flee(self, entity: "Entity") -> bool:
        """Check if a unit should attempt to flee from combat.
        
        Args:
            entity: Unit to check
            
        Returns:
            True if unit should flee
        """
        morale_component = entity.get_component("Morale")
        if not morale_component:
            return False
            
        morale = cast(MoraleComponent, morale_component)
        return morale.should_flee_from_combat()
    
    def _check_heavy_damage_panic(self, entity: "Entity", damage: int) -> None:
        """Check if heavy damage triggers panic.
        
        Args:
            entity: Unit that took heavy damage
            damage: Amount of damage taken
        """
        morale_component = entity.get_component("Morale")
        if not morale_component:
            return
            
        morale = cast(MoraleComponent, morale_component)
        
        # Heavy damage can trigger immediate panic regardless of current morale
        if damage >= 20 and not morale.is_panicked:
            # Additional morale loss for traumatic damage
            trauma_penalty = -10
            morale.modify_morale(trauma_penalty, "traumatic_damage")
            
            if morale.get_effective_morale() <= morale.panic_threshold + 10:
                self._trigger_panic(entity, "heavy_damage")
    
    def _trigger_panic(self, entity: "Entity", reason: str) -> None:
        """Trigger panic state for a unit.
        
        Args:
            entity: Unit to panic
            reason: Reason for panic
        """
        morale_component = entity.get_component("Morale")
        if not morale_component:
            return
            
        morale = cast(MoraleComponent, morale_component)
        
        if not morale.is_panicked:
            morale.enter_panic_state(reason)
            self._emit_panic_event(entity, reason)
            
            # Check for immediate rout
            if morale.get_effective_morale() <= morale.rout_threshold:
                self._trigger_rout(entity)
    
    def _trigger_rout(self, entity: "Entity") -> None:
        """Trigger rout state for a unit.
        
        Args:
            entity: Unit to rout
        """
        morale_component = entity.get_component("Morale")
        if not morale_component:
            return
            
        morale = cast(MoraleComponent, morale_component)
        
        if not morale.is_routed:
            morale.enter_rout_state()
            self._emit_rout_event(entity)
    
    def _update_proximity_modifiers(self, entity: "Entity") -> None:
        """Update morale modifiers based on nearby units.
        
        Args:
            entity: Unit to update modifiers for
        """
        morale_component = entity.get_component("Morale")
        actor_component = entity.get_component("Actor")
        
        if not morale_component or not actor_component:
            return
            
        morale = cast(MoraleComponent, morale_component)
        actor = cast('ActorComponent', actor_component)
        
        position = self._get_entity_position(entity)
        if not position:
            return
        
        # Clear old proximity modifiers
        morale.remove_temporary_modifier("nearby_allies")
        morale.remove_temporary_modifier("outnumbered")
        morale.remove_temporary_modifier("surrounded")
        
        # Count nearby allies and enemies
        nearby_units = self._get_units_in_range(position, 2)  # Closer proximity for these effects
        ally_count = 0
        enemy_count = 0
        
        for unit in nearby_units:
            unit_actor = unit.get_component("Actor")
            if unit_actor and unit != entity:
                unit_actor_cast = cast('ActorComponent', unit_actor)
                if actor.is_ally_of(unit_actor_cast):
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
    
    def _get_entity_position(self, entity: "Entity") -> Optional[Vector2]:
        """Get position of an entity.
        
        Args:
            entity: Entity to get position for
            
        Returns:
            Position vector or None if not found
        """
        movement_component = entity.get_component("Movement")
        if not movement_component:
            return None
            
        movement = cast('MovementComponent', movement_component)
        return movement.get_position()
    
    def _get_units_in_range(self, center: Vector2, radius: int) -> list["Entity"]:
        """Get all units within range of a position.
        
        Args:
            center: Center position
            radius: Search radius (Manhattan distance)
            
        Returns:
            List of entities within range
        """
        units_in_range = []
        
        for unit in self.game_map.units:
            position = unit.position  # Unit objects have direct position access
            if position.manhattan_distance_to(center) <= radius:
                units_in_range.append(unit.entity)  # Return the entity for component access
        
        return units_in_range
    
    def _emit_morale_event(self, entity: "Entity", old_morale: int, new_morale: int) -> None:
        """Emit morale changed event.
        
        Args:
            entity: Entity whose morale changed
            old_morale: Previous morale value
            new_morale: New morale value
        """
        
        actor = entity.get_component("Actor")
        position = self._get_entity_position(entity)
        
        if actor and position:
            actor_cast = cast('ActorComponent', actor)
            event = MoraleChanged(
                turn=self.current_turn,
                unit_name=actor_cast.name,
                team=actor_cast.team,
                old_morale=old_morale,
                new_morale=new_morale,
                position=(position.y, position.x)
            )
            self.event_manager.publish(event, source="MoraleManager")
    
    def _emit_panic_event(self, entity: "Entity", reason: str) -> None:
        """Emit unit panicked event.
        
        Args:
            entity: Entity that panicked
            reason: Reason for panic
        """
        
        actor = entity.get_component("Actor")
        position = self._get_entity_position(entity)
        
        if actor and position:
            actor_cast = cast('ActorComponent', actor)
            event = UnitPanicked(
                turn=self.current_turn,
                unit_name=actor_cast.name,
                team=actor_cast.team,
                position=(position.y, position.x),
                trigger_reason=reason
            )
            self.event_manager.publish(event, source="MoraleManager")
            
            # Log the panic event
            self._emit_log(f"{actor_cast.name}: Panicked ({reason})", "BATTLE")
    
    def _emit_rout_event(self, entity: "Entity") -> None:
        """Emit unit routed event.
        
        Args:
            entity: Entity that routed
        """
        
        actor = entity.get_component("Actor")
        position = self._get_entity_position(entity)
        
        if actor and position:
            actor_cast = cast('ActorComponent', actor)
            event = UnitRouted(
                turn=self.current_turn,
                unit_name=actor_cast.name,
                team=actor_cast.team,
                position=(position.y, position.x)
            )
            self.event_manager.publish(event, source="MoraleManager")
            
            # Log the rout event
            self._emit_log(f"{actor_cast.name}: Routed (fleeing battlefield)", "BATTLE")
    
    def _emit_rally_event(self, entity: "Entity") -> None:
        """Emit unit rallied event.
        
        Args:
            entity: Entity that rallied
        """
        
        actor = entity.get_component("Actor")
        position = self._get_entity_position(entity)
        
        if actor and position:
            actor_cast = cast('ActorComponent', actor)
            event = UnitRallied(
                turn=self.current_turn,
                unit_name=actor_cast.name,
                team=actor_cast.team,
                position=(position.y, position.x)
            )
            self.event_manager.publish(event, source="MoraleManager")
            
            # Log the rally event
            self._emit_log(f"{actor_cast.name}: Rallied (regained courage)", "BATTLE")