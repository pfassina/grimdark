"""
Hazard Manager - Manages environmental hazards on the battlefield

This module handles hazard lifecycle, spreading, timeline integration,
and coordination with other game systems.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass, field
import random

from src.core.hazards import (
    Hazard, HazardType, HazardAction, HazardEffect,
    create_hazard
)
from src.core.data_structures import Vector2
from src.core.events import (
    UnitMoved, TurnStarted, LogMessage, EventType, GameEvent
)

if TYPE_CHECKING:
    from src.game.unit import Unit
    from src.core.game_state import GameState
    from src.core.events import GameEvent
    from src.game.map import GameMap
    from ..core.event_manager import EventManager


@dataclass
class HazardInstance:
    """Tracks a hazard instance on the battlefield"""
    hazard: Hazard
    timeline_entry_id: Optional[str] = None
    positions: set[tuple[int, int]] = field(default_factory=set)
    
    def contains_position(self, position: Vector2) -> bool:
        """Check if hazard affects a position"""
        return (position.y, position.x) in self.positions


class HazardManager:
    """
    Manages all environmental hazards on the battlefield
    
    Responsibilities:
    - Create and remove hazards
    - Process hazard ticks and spreading
    - Apply hazard effects to units
    - Integrate with timeline system
    - Handle hazard combinations
    """
    
    def __init__(self, game_state: GameState, game_map: "GameMap", event_manager: "EventManager"):
        """
        Initialize hazard manager
        
        Args:
            game_state: Reference to game state for accessing units, timeline
            game_map: Reference to the game map
            event_manager: Event manager for publishing and subscribing to events
        """
        self.game_state = game_state
        self.game_map = game_map
        self.event_manager = event_manager
        self.active_hazards: dict[str, HazardInstance] = {}  # hazard_id -> instance
        self.position_hazards: dict[tuple[int, int], list[str]] = {}  # position -> hazard_ids
        self.next_hazard_id = 1
        
        # Set up event subscriptions
        self._setup_event_subscriptions()
        
    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for hazard manager."""
        # Subscribe to unit movement to trigger hazard effects
        self.event_manager.subscribe(EventType.UNIT_MOVED, self._on_unit_moved)
        
        # Subscribe to turn start for hazard processing
        self.event_manager.subscribe(EventType.TURN_STARTED, self._on_turn_started)
        
    def _emit_log(self, message: str, category: str = "HAZARD", level: str = "INFO") -> None:
        """Emit a log message event."""
        current_turn = getattr(self.game_state, 'turn', 0)
        if hasattr(self.game_state, 'battle') and hasattr(self.game_state.battle, 'current_turn'):
            current_turn = self.game_state.battle.current_turn
            
        self.event_manager.publish(
            LogMessage(
                turn=current_turn,
                message=message,
                category=category,
                level=level,
                source="HazardManager"
            ),
            source="HazardManager"
        )
        
    def _on_unit_moved(self, event: GameEvent) -> None:
        """Handle unit moved event to trigger hazard effects."""
        assert isinstance(event, UnitMoved), f"Expected UnitMoved, got {type(event)}"
        # Check for hazards at the destination position
        position = Vector2(event.to_position[0], event.to_position[1])  # Convert (y,x) to Vector2(y,x)
        self.check_hazard_triggers("unit_moved", position=position)
        
    def _on_turn_started(self, event: GameEvent) -> None:
        """Handle turn started event for hazard processing."""
        assert isinstance(event, TurnStarted), f"Expected TurnStarted, got {type(event)}"
        # Process all active hazards for spreading, decay, etc.
        self.process_hazard_turn()
        
    def create_hazard(self, hazard_type: HazardType, position: Vector2,
                     intensity: int = 1, source_unit: Optional[Unit] = None,
                     **kwargs) -> str:
        """
        Create a new hazard on the battlefield
        
        Args:
            hazard_type: Type of hazard to create
            position: Initial position
            intensity: Hazard strength
            source_unit: Unit that created it
            **kwargs: Additional hazard-specific parameters
            
        Returns:
            Hazard ID for tracking
        """
        # Check for existing hazards at position for combination
        existing_hazards = self.get_hazards_at_position(position)
        
        # Create the hazard
        hazard = create_hazard(hazard_type, position, intensity, source_unit, **kwargs)
        hazard.creation_time = self.game_state.battle.timeline.current_time
        
        # Check for combinations with existing hazards
        for existing_id in existing_hazards:
            existing = self.active_hazards[existing_id].hazard
            combined = hazard.combine_with(existing)
            if combined:
                # Replace both hazards with combined one
                self.remove_hazard(existing_id)
                hazard = combined
                break
        
        # Register the hazard
        hazard_id = f"hazard_{self.next_hazard_id}"
        self.next_hazard_id += 1
        
        instance = HazardInstance(
            hazard=hazard,
            positions={(position.y, position.x)}
        )
        self.active_hazards[hazard_id] = instance
        
        # Update position mapping
        pos_key = (position.y, position.x)
        if pos_key not in self.position_hazards:
            self.position_hazards[pos_key] = []
        self.position_hazards[pos_key].append(hazard_id)
        
        # Add to timeline if it acts
        if hazard.properties.ticks_per_action > 0:
            self._add_to_timeline(hazard_id, hazard)
        
        # Log hazard creation
        hazard_name = hazard.properties.hazard_type.name.title()
        self._emit_log(f"{hazard_name} appears at [{position.y},{position.x}]", "BATTLE")
        
        return hazard_id
    
    def _add_to_timeline(self, hazard_id: str, hazard: Hazard) -> None:
        """Add hazard to timeline for periodic actions"""
        next_time = self.game_state.battle.timeline.current_time + hazard.properties.ticks_per_action
        entry_id = self.game_state.battle.timeline.add_entry(
            time=next_time,
            entity_id=hazard_id,
            entity_type="hazard",
            action_description=f"{hazard.properties.name} acts"
        )
        self.active_hazards[hazard_id].timeline_entry_id = entry_id
    
    def process_hazard_tick(self, hazard_id: str) -> list[GameEvent]:
        """
        Process one tick of a hazard's behavior
        
        Args:
            hazard_id: ID of hazard to process
            
        Returns:
            List of game events generated
        """
        events = []
        
        if hazard_id not in self.active_hazards:
            return events
            
        instance = self.active_hazards[hazard_id]
        hazard = instance.hazard
        
        # Get hazard actions
        actions = hazard.tick(self.game_map, self.game_state.battle.timeline.current_time)
        
        # Process each action
        for action in actions:
            events.extend(self._process_hazard_action(hazard_id, action))
        
        # Check if hazard expired
        if hazard.is_expired():
            self.remove_hazard(hazard_id)
        else:
            # Re-schedule on timeline
            if hazard.properties.ticks_per_action > 0:
                self._add_to_timeline(hazard_id, hazard)
        
        return events
    
    def _process_hazard_action(self, hazard_id: str, action: HazardAction) -> list[GameEvent]:
        """Process a single hazard action"""
        events = []
        
        if action.action_type == "damage":
            unit = action.data.get("unit")
            effect = action.data.get("effect")
            if unit and effect:
                self._apply_damage_to_unit(unit, effect, hazard_id)
                events.append(self._create_damage_event(unit, effect, hazard_id))
                
        elif action.action_type == "spread":
            intensity = action.data.get("intensity", 1)
            source_hazard = self.active_hazards[hazard_id].hazard
            
            # Create new hazard at spread position
            self.create_hazard(
                source_hazard.properties.hazard_type,
                action.position,
                intensity,
                source_hazard.source_unit
            )
            
            # Link to parent hazard's affected positions
            self.active_hazards[hazard_id].positions.add((action.position.y, action.position.x))
            
            # Log the spread event
            hazard_name = source_hazard.properties.hazard_type.name.title()
            self._emit_log(f"{hazard_name} spreads to [{action.position.y},{action.position.x}]", "BATTLE")
            
        elif action.action_type == "transform_terrain":
            new_terrain = action.data.get("new_terrain")
            if new_terrain:
                self._transform_terrain(action.position, new_terrain)
                
                # Log terrain transformation
                self._emit_log(f"Terrain changed: [{action.position.y},{action.position.x}] now {new_terrain}", "BATTLE")
                
        elif action.action_type == "apply_effect":
            unit = action.data.get("unit")
            effect = action.data.get("effect")
            if unit and effect:
                self._apply_effect_to_unit(unit, effect)
                # TODO: Create proper effect application event type when needed
                
        elif action.action_type == "force_move":
            unit = action.data.get("unit")
            new_position = action.data.get("new_position")
            message = action.data.get("message", "")
            if unit and new_position:
                self._force_unit_move(unit, new_position)
                move_event = self._create_move_event(unit, new_position, message)
                if move_event:
                    events.append(move_event)
                
                # Log the forced movement
                if message:
                    self._emit_log(f"{unit.name}: Forced move to [{new_position.y},{new_position.x}] ({message})", "BATTLE")
                else:
                    self._emit_log(f"{unit.name}: Forced move to [{new_position.y},{new_position.x}]", "BATTLE")
                
        elif action.action_type == "warning":
            message = action.data.get("message", "")
            warning_event = self._create_warning_event(action.position, message)
            if warning_event:
                events.append(warning_event)
            
            # Log the warning
            if message:
                self._emit_log(f"Warning at [{action.position.y},{action.position.x}]: {message}", "WARNING")
            else:
                self._emit_log(f"Hazard warning at [{action.position.y},{action.position.x}]", "WARNING")
        
        return events
    
    def _apply_damage_to_unit(self, unit: Unit, effect: HazardEffect, hazard_id: str) -> None:
        """Apply hazard damage to a unit"""
        if effect.damage > 0:
            # Apply damage variance for chaos
            damage = effect.damage + random.randint(-2, 2)
            damage = max(1, damage)  # Minimum 1 damage
            
            unit.take_damage(damage)
            
            # Log hazard damage
            hazard = self.active_hazards[hazard_id].hazard
            hazard_name = hazard.properties.hazard_type.name.title()
            self._emit_log(f"{unit.name}: {hazard_name} damage ({damage})", "BATTLE")
            
            # Track source for kill attribution
            hazard = self.active_hazards[hazard_id].hazard
            # Kill tracking could be added here in the future if needed
    
    def _apply_effect_to_unit(self, unit: Unit, effect: HazardEffect) -> None:
        """Apply non-damage effects to a unit"""
        # Apply stat modifiers
        for stat, modifier in effect.stat_modifiers.items():
            if hasattr(unit, stat):
                current = getattr(unit, stat)
                setattr(unit, stat, current + modifier)
        
        # Apply status effects
        # Status effects application will be implemented when status system is added
        # for status in effect.status_effects:
        #     if status not in unit.status_effects:
        #         unit.status_effects.append(status)
    
    def _transform_terrain(self, position: Vector2, new_terrain: str) -> None:
        """Transform terrain at position"""
        if self.game_map.is_valid_position(position):
            tile = self.game_map.get_tile(position)
            # Convert string terrain name to TerrainType enum
            from ..core.game_enums import TerrainType
            from ..core.game_info import TERRAIN_DATA
            new_terrain_type = TerrainType[new_terrain.upper()]
            tile.terrain_type = new_terrain_type
            # Trigger recalculation of properties by resetting _info
            tile._info = TERRAIN_DATA[new_terrain_type]
    
    def _force_unit_move(self, unit: Unit, new_position: Vector2) -> None:
        """Force a unit to move (e.g., slipping on ice)"""
        if self.game_map.is_valid_position(new_position):
            if not self.game_map.is_position_blocked(new_position, unit.team):
                # Move unit using map method which handles both position and tracking
                self.game_map.move_unit(unit.unit_id, new_position)
    
    def remove_hazard(self, hazard_id: str) -> None:
        """Remove a hazard from the battlefield"""
        if hazard_id not in self.active_hazards:
            return
            
        instance = self.active_hazards[hazard_id]
        
        # Remove from position mapping
        for pos in instance.positions:
            if pos in self.position_hazards:
                self.position_hazards[pos] = [
                    hid for hid in self.position_hazards[pos] if hid != hazard_id
                ]
                if not self.position_hazards[pos]:
                    del self.position_hazards[pos]
        
        # Remove from timeline if scheduled
        if instance.timeline_entry_id and self.game_state.battle:
            self.game_state.battle.timeline.remove_entry(instance.timeline_entry_id)
        
        # Log hazard removal
        hazard_name = instance.hazard.properties.hazard_type.name.title()
        self._emit_log(f"{hazard_name} dissipates", "BATTLE")
        
        # Remove instance
        del self.active_hazards[hazard_id]
    
    def get_hazards_at_position(self, position: Vector2) -> list[str]:
        """Get all hazard IDs affecting a position"""
        pos_key = (position.y, position.x)
        return self.position_hazards.get(pos_key, [])
    
    def get_hazard_effects_at_position(self, position: Vector2) -> list[HazardEffect]:
        """Get all hazard effects at a position"""
        effects = []
        for hazard_id in self.get_hazards_at_position(position):
            if hazard_id in self.active_hazards:
                hazard = self.active_hazards[hazard_id].hazard
                # Get the appropriate effect based on hazard state
                if hazard.is_expired() and hazard.properties.final_effect:
                    effects.append(hazard.properties.final_effect)
                else:
                    effects.append(hazard.properties.recurring_effect)
        return effects
    
    def check_hazard_triggers(self, event_type: str, **event_data) -> list[GameEvent]:
        """
        Check if an event triggers any hazard creation
        
        Args:
            event_type: Type of event (e.g., "explosion", "spell_cast")
            **event_data: Event-specific data
            
        Returns:
            List of triggered events
        """
        events = []
        
        # Example triggers
        if event_type == "explosion":
            position = event_data.get("position")
            radius = event_data.get("radius", 1)
            if position:
                # Create fire hazards in explosion area
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        if abs(dy) + abs(dx) <= radius:  # Diamond pattern
                            fire_pos = Vector2(position.x + dx, position.y + dy)
                            if self.game_map.is_valid_position(fire_pos):
                                self.create_hazard(
                                    HazardType.FIRE,
                                    fire_pos,
                                    intensity=2,
                                    source_unit=event_data.get("source_unit")
                                )
                                # TODO: Create proper hazard creation event type when needed
        
        elif event_type == "poison_spell":
            position = event_data.get("position")
            if position:
                # Create poison cloud
                self.create_hazard(
                    HazardType.POISON_CLOUD,
                    position,
                    intensity=3,
                    source_unit=event_data.get("caster"),
                    wind_direction=event_data.get("wind_direction", (0, 1))
                )
                # TODO: Create proper hazard creation event type when needed
        
        elif event_type == "ice_spell":
            position = event_data.get("position")
            radius = event_data.get("radius", 2)
            if position:
                # Create ice field
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        if dy * dy + dx * dx <= radius * radius:  # Circular pattern
                            ice_pos = Vector2(position.x + dx, position.y + dy)
                            if self.game_map.is_valid_position(ice_pos):
                                tile = self.game_map.get_tile(ice_pos)
                                if tile.terrain_type in ["water", "stone", "grass"]:
                                    self.create_hazard(
                                        HazardType.ICE,
                                        ice_pos,
                                        intensity=1,
                                        source_unit=event_data.get("caster")
                                    )
                                    # TODO: Create proper hazard creation event type when needed
        
        elif event_type == "heavy_impact":
            position = event_data.get("position")
            if position and self.game_map.is_valid_position(position):
                # Might cause terrain to collapse
                tile = self.game_map.get_tile(position)
                if tile.terrain_type in ["bridge", "wood_floor", "old_stone"]:
                    self.create_hazard(
                        HazardType.COLLAPSING_TERRAIN,
                        position,
                        intensity=1,
                        source_unit=event_data.get("source_unit")
                    )
                    # TODO: Create proper hazard creation event type when needed
        
        return events
    
    def get_all_hazard_positions(self) -> set[tuple[int, int]]:
        """Get all positions affected by any hazard"""
        all_positions = set()
        for instance in self.active_hazards.values():
            all_positions.update(instance.positions)
        return all_positions
    
    def clear_all_hazards(self) -> None:
        """Remove all hazards from battlefield"""
        hazard_ids = list(self.active_hazards.keys())
        for hazard_id in hazard_ids:
            self.remove_hazard(hazard_id)
    
    # Event creation helpers
    
    def _create_damage_event(self, unit: Unit, effect: HazardEffect, hazard_id: str) -> GameEvent:
        """Create damage event"""
        from src.core.events import UnitTookDamage
        return UnitTookDamage(
            turn=getattr(self.game_state, 'turn_count', 0),
            unit_name=unit.name,
            team=unit.team,
            damage_amount=effect.damage,
            position=(unit.position.y, unit.position.x)
        )
    
    def _create_spread_event(self, parent_id: str, new_id: str, position: Vector2) -> None:
        """Create spread event (hazard-specific event, not part of main event system)"""
        # Hazard spread events are handled through logging only
        return None
    
    def _create_terrain_event(self, position: Vector2, new_terrain: str) -> None:
        """Create terrain transformation event (hazard-specific event, not part of main event system)"""
        # Terrain transformation events are handled through logging only
        return None
    
    def _create_effect_event(self, unit: Unit, effect: HazardEffect) -> None:
        """Create effect application event (hazard-specific event, not part of main event system)"""
        # Effect application events are handled through logging only
        return None
    
    def _create_move_event(self, unit: Unit, new_position: Vector2, message: str) -> GameEvent:
        """Create forced move event using standard UnitMoved event"""
        from src.core.events import UnitMoved
        return UnitMoved(
            turn=getattr(self.game_state, 'turn_count', 0),
            unit_name=unit.name,
            unit_id=unit.unit_id,
            team=unit.team,
            from_position=(unit.position.y, unit.position.x),
            to_position=(new_position.y, new_position.x)
        )
    
    def _create_warning_event(self, position: Vector2, message: str) -> None:
        """Create warning event (hazard-specific event, not part of main event system)"""
        # Warning events are handled through logging only
        return None
    
    def _create_hazard_event(self, hazard_id: str, position: Vector2) -> None:
        """Create hazard creation event (hazard-specific event, not part of main event system)"""
        # Hazard creation events are handled through logging only
        return None
        
    def process_hazard_turn(self) -> None:
        """Process all active hazards for turn-based effects like spreading and decay."""
        # Process turn-based hazard effects for all active hazards
        hazard_ids = list(self.active_hazards.keys())  # Create a copy to avoid modification during iteration
        
        for hazard_id in hazard_ids:
            if hazard_id not in self.active_hazards:
                continue  # Hazard may have been removed during processing
                
            instance = self.active_hazards[hazard_id]
            hazard = instance.hazard
            
            # Process hazard effects using the tick method
            current_time = self.game_state.battle.timeline.current_time if self.game_state.battle else 0
            actions = hazard.tick(self.game_map, current_time)
            
            # Process each action returned by the hazard
            for action in actions:
                if action.action_type != "spread":
                    continue
                    
                pos = action.position
                if not self.game_map.is_valid_position(pos):
                    continue
                    
                # Create spread hazard
                self.create_hazard(
                    hazard.properties.hazard_type,
                    pos,
                    max(1, hazard.intensity - 1),  # Reduced intensity for spread
                    hazard.source_unit
                )
            
            # Check if hazard has expired
            if hazard.is_expired():
                self.remove_hazard(hazard_id)