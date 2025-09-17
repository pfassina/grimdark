"""Escalation and reinforcement system for creating battle time pressure.

This manager implements the grimdark principle that battles become more dangerous
over time, punishing players who take too long and forcing difficult tactical decisions.
"""

from typing import TYPE_CHECKING, Any
from dataclasses import dataclass
from enum import Enum, auto

from ..core.data_structures import Vector2
from ..core.events import (
    LogMessage, EventType
)

if TYPE_CHECKING:
    from ..core.components import Entity
    from ..core.game_state import GameState
    from ..core.event_manager import EventManager
    from ..core.events import GameEvent
    from .scenario import Scenario
    from .map import GameMap


class EscalationType(Enum):
    """Types of escalation that can occur during battle."""
    REINFORCEMENTS = auto()       # Enemy reinforcements arrive
    ENVIRONMENTAL = auto()        # Environment becomes more dangerous
    TIME_PRESSURE = auto()        # Objectives become harder/impossible
    MORALE_DECAY = auto()         # Passive morale loss over time
    HAZARD_SPREAD = auto()        # Existing hazards spread faster


class ReinforcementTrigger(Enum):
    """Conditions that can trigger reinforcement spawning."""
    TURN_BASED = auto()           # After specific number of turns
    CASUALTY_BASED = auto()       # After enemy casualties reach threshold
    OBJECTIVE_BASED = auto()      # When certain objectives are threatened
    TIME_BASED = auto()           # After specific amount of battle time
    RANDOM = auto()               # Random chance each turn


@dataclass
class EscalationEvent:
    """Configuration for a specific escalation event."""
    escalation_type: EscalationType
    trigger_condition: str        # Human-readable trigger description
    trigger_turn: int            # Turn when this event triggers
    severity: int                # Intensity of the escalation (1-10)
    description: str             # What happens when this triggers
    data: dict[str, Any]         # Event-specific configuration data
    
    def __post_init__(self):
        """Validate escalation event configuration."""
        if self.severity < 1 or self.severity > 10:
            raise ValueError(f"Escalation severity must be 1-10, got {self.severity}")


@dataclass
class ReinforcementWave:
    """Configuration for a reinforcement wave."""
    trigger_type: ReinforcementTrigger
    trigger_value: int           # Turn number, casualty count, etc.
    spawn_locations: list[Vector2]  # Where units spawn
    unit_templates: list[dict]   # Units to spawn (class, level, equipment)
    warning_turns: int = 1       # Turns of advance warning
    max_spawns: int = 5          # Maximum units to spawn
    repeating: bool = False      # Whether wave can trigger multiple times
    
    # State tracking
    has_triggered: bool = False
    warned_turn: int = -1


class EscalationManager:
    """Manager for escalation pressure and reinforcement spawning.
    
    This system creates mounting pressure during battles through:
    - Reinforcement waves that strengthen the enemy over time
    - Environmental hazards that spread and intensify
    - Morale decay that affects unit effectiveness
    - Time pressure that makes objectives harder to complete
    """
    
    def __init__(self, game_state: "GameState", game_map: "GameMap", scenario: "Scenario", 
                 event_manager: "EventManager"):
        """Initialize escalation manager.
        
        Args:
            game_state: Reference to the main game state
            game_map: Reference to the game map containing units
            scenario: Current scenario configuration
            event_manager: Event manager for publishing and subscribing to events
        """
        self.game_state = game_state
        self.game_map = game_map
        self.scenario = scenario
        self.event_manager = event_manager
        
        # Battle state tracking
        self.current_turn = 0
        self.battle_start_time = 0
        self.total_enemy_casualties = 0
        self.total_player_casualties = 0
        
        # Escalation configuration
        self.escalation_events: list[EscalationEvent] = []
        self.reinforcement_waves: list[ReinforcementWave] = []
        self.triggered_events: set[int] = set()  # Track which events have fired
        
        # Escalation intensity tracking
        self.base_escalation_rate = 1.0  # Multiplier for escalation speed
        self.current_threat_level = 1    # Overall battlefield threat level
        
        # Initialize scenario-based escalation
        self._initialize_scenario_escalation()
        
        # Set up event subscriptions
        self._setup_event_subscriptions()
        
    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for escalation manager."""
        # Subscribe to turn events to process escalation
        self.event_manager.subscribe(EventType.TURN_STARTED, self._on_turn_started)
        
        # Subscribe to unit defeat events to track casualties
        self.event_manager.subscribe(EventType.UNIT_DEFEATED, self._on_unit_defeated)
        
    def _emit_log(self, message: str, category: str = "ESCALATION", level: str = "INFO") -> None:
        """Emit a log message event."""
        self.event_manager.publish(
            LogMessage(
                turn=self.current_turn,
                message=message,
                category=category,
                level=level,
                source="EscalationManager"
            ),
            source="EscalationManager"
        )
        
    def _on_turn_started(self, event: "GameEvent") -> None:
        """Handle turn started event for escalation processing."""
        from ..core.events import TurnStarted
        assert isinstance(event, TurnStarted), f"Expected TurnStarted event, got {type(event).__name__}"
            
        # Extract turn number from game state (since TurnStarted doesn't include turn number)
        # We'll process escalation for the current game state turn
        current_turn = getattr(self.game_state, 'turn', 0)
        if hasattr(self.game_state, 'battle') and hasattr(self.game_state.battle, 'current_turn'):
            current_turn = self.game_state.battle.current_turn
        
        self.process_turn_start(current_turn)
        
    def _on_unit_defeated(self, event: "GameEvent") -> None:
        """Handle unit defeated event for casualty tracking."""
        from ..core.events import UnitDefeated
        assert isinstance(event, UnitDefeated), f"Expected UnitDefeated event, got {type(event).__name__}"
            
        # Determine if this was an enemy unit based on team
        is_enemy = event.team != getattr(self.game_state, 'player_team', None)
        
        # Find the defeated unit entity for reporting
        for unit in self.game_map.units:
            actor = unit.entity.get_component("Actor")
            if actor and actor.name == event.unit_name:
                self.report_casualty(unit.entity, is_enemy)
                break
    
    def _initialize_scenario_escalation(self) -> None:
        """Initialize escalation events based on scenario configuration."""
        # Default escalation for all scenarios
        self._add_default_escalation_events()
        
        # Scenario-specific escalation (would be loaded from scenario file)
        scenario_name = getattr(self.scenario, 'name', 'default')
        if 'fortress' in scenario_name.lower():
            self._add_fortress_escalation()
        elif 'escape' in scenario_name.lower():
            self._add_escape_escalation()
        elif 'ambush' in scenario_name.lower():
            self._add_ambush_escalation()
    
    def _add_default_escalation_events(self) -> None:
        """Add basic escalation events that apply to most scenarios."""
        # Morale decay over time
        self.escalation_events.append(EscalationEvent(
            escalation_type=EscalationType.MORALE_DECAY,
            trigger_condition="Every 5 turns after turn 10",
            trigger_turn=10,
            severity=2,
            description="Prolonged battle causes fatigue and doubt",
            data={"morale_penalty": -3, "radius": 0, "repeating": True, "interval": 5}
        ))
        
        # Environmental pressure
        self.escalation_events.append(EscalationEvent(
            escalation_type=EscalationType.HAZARD_SPREAD,
            trigger_condition="Turn 8",
            trigger_turn=8,
            severity=3,
            description="Battlefield hazards spread faster",
            data={"spread_multiplier": 1.5}
        ))
        
        # Late battle reinforcements
        self.escalation_events.append(EscalationEvent(
            escalation_type=EscalationType.REINFORCEMENTS,
            trigger_condition="Turn 15",
            trigger_turn=15,
            severity=4,
            description="Enemy reinforcements arrive from nearby positions",
            data={"unit_count": 2, "unit_type": "mixed"}
        ))
    
    def _add_fortress_escalation(self) -> None:
        """Add escalation events specific to fortress defense scenarios."""
        # Waves of attackers
        self.escalation_events.extend([
            EscalationEvent(
                escalation_type=EscalationType.REINFORCEMENTS,
                trigger_condition="Turn 6",
                trigger_turn=6,
                severity=3,
                description="First wave of fortress assault",
                data={"unit_count": 3, "unit_type": "warriors", "spawn_pattern": "siege"}
            ),
            EscalationEvent(
                escalation_type=EscalationType.REINFORCEMENTS,
                trigger_condition="Turn 12",
                trigger_turn=12,
                severity=5,
                description="Heavy assault with siege engines",
                data={"unit_count": 4, "unit_type": "siege", "spawn_pattern": "walls"}
            ),
            EscalationEvent(
                escalation_type=EscalationType.ENVIRONMENTAL,
                trigger_condition="Turn 18",
                trigger_turn=18,
                severity=6,
                description="Fortress walls begin to crumble",
                data={"wall_damage": True, "new_passages": True}
            )
        ])
    
    def _add_escape_escalation(self) -> None:
        """Add escalation events specific to escape scenarios."""
        # Pursuit forces
        self.escalation_events.extend([
            EscalationEvent(
                escalation_type=EscalationType.REINFORCEMENTS,
                trigger_condition="Turn 4",
                trigger_turn=4,
                severity=2,
                description="Pursuit forces catch up",
                data={"unit_count": 2, "unit_type": "fast", "spawn_pattern": "behind"}
            ),
            EscalationEvent(
                escalation_type=EscalationType.TIME_PRESSURE,
                trigger_condition="Turn 10",
                trigger_turn=10,
                severity=4,
                description="Escape route becomes compromised",
                data={"route_penalty": True, "movement_cost_increase": 1}
            ),
            EscalationEvent(
                escalation_type=EscalationType.REINFORCEMENTS,
                trigger_condition="Turn 15",
                trigger_turn=15,
                severity=6,
                description="Full hunting party mobilizes",
                data={"unit_count": 5, "unit_type": "mixed", "spawn_pattern": "surround"}
            )
        ])
    
    def _add_ambush_escalation(self) -> None:
        """Add escalation events specific to ambush scenarios."""
        # Hidden enemies reveal themselves
        self.escalation_events.extend([
            EscalationEvent(
                escalation_type=EscalationType.REINFORCEMENTS,
                trigger_condition="Turn 3",
                trigger_turn=3,
                severity=3,
                description="Hidden archers reveal positions",
                data={"unit_count": 2, "unit_type": "archers", "spawn_pattern": "hidden"}
            ),
            EscalationEvent(
                escalation_type=EscalationType.ENVIRONMENTAL,
                trigger_condition="Turn 6",
                trigger_turn=6,
                severity=4,
                description="Ambush site becomes a trap",
                data={"block_exits": True, "add_hazards": True}
            ),
            EscalationEvent(
                escalation_type=EscalationType.MORALE_DECAY,
                trigger_condition="Turn 8",
                trigger_turn=8,
                severity=5,
                description="Realization of being trapped causes panic",
                data={"morale_penalty": -8, "panic_chance": 0.3}
            )
        ])
    
    def process_turn_start(self, turn: int) -> None:
        """Process escalation at the start of each turn.
        
        Args:
            turn: Current turn number
        """
        self.current_turn = turn
        
        # Check for escalation events
        self._check_escalation_events()
        
        # Check for reinforcement waves
        self._check_reinforcement_waves()
        
        # Update threat level based on battle duration
        self._update_threat_level()
        
        # Apply ongoing escalation effects
        self._apply_ongoing_effects()
    
    def _check_escalation_events(self) -> None:
        """Check if any escalation events should trigger this turn."""
        for i, event in enumerate(self.escalation_events):
            # Skip already triggered non-repeating events
            if i in self.triggered_events and not event.data.get('repeating', False):
                continue
            
            should_trigger = False
            
            # Check turn-based triggers
            if event.trigger_turn == self.current_turn:
                should_trigger = True
            
            # Check repeating events
            if (event.data.get('repeating', False) and 
                self.current_turn >= event.trigger_turn and 
                (self.current_turn - event.trigger_turn) % event.data.get('interval', 1) == 0):
                should_trigger = True
            
            if should_trigger:
                self._trigger_escalation_event(event, i)
    
    def _trigger_escalation_event(self, event: EscalationEvent, event_id: int) -> None:
        """Trigger a specific escalation event.
        
        Args:
            event: The escalation event to trigger
            event_id: Unique ID for tracking triggered events
        """
        self.triggered_events.add(event_id)
        
        # Log escalation event
        self._emit_log(f"Escalation: {event.description} (Severity {event.severity})", "ESCALATION")
        
        # Apply escalation effects based on type
        if event.escalation_type == EscalationType.MORALE_DECAY:
            self._apply_morale_decay(event)
        elif event.escalation_type == EscalationType.REINFORCEMENTS:
            self._spawn_reinforcements(event)
        elif event.escalation_type == EscalationType.ENVIRONMENTAL:
            self._apply_environmental_escalation(event)
        elif event.escalation_type == EscalationType.HAZARD_SPREAD:
            self._accelerate_hazard_spread(event)
        elif event.escalation_type == EscalationType.TIME_PRESSURE:
            self._apply_time_pressure(event)
        
        # Increase threat level
        self.current_threat_level += event.severity // 3
    
    def _apply_morale_decay(self, event: EscalationEvent) -> None:
        """Apply morale decay to all units.
        
        Args:
            event: The morale decay event configuration
        """
        morale_penalty = event.data.get('morale_penalty', -2)
        
        # Apply to all units (or specific teams)
        for unit in self.game_map.units:
            morale_component = unit.entity.get_component("Morale")
            if morale_component:
                from typing import cast
                from .components import MoraleComponent
                morale = cast(MoraleComponent, morale_component)
                morale.modify_morale(morale_penalty, "prolonged_battle")
    
    def _spawn_reinforcements(self, event: EscalationEvent) -> None:
        """Spawn reinforcement units based on event configuration.
        
        Args:
            event: The reinforcement event configuration
        """
        unit_count = event.data.get('unit_count', 1)
        unit_type = event.data.get('unit_type', 'warrior')
        spawn_pattern = event.data.get('spawn_pattern', 'random')
        
        # Find spawn locations based on pattern
        spawn_locations = self._get_spawn_locations(spawn_pattern, unit_count)
        
        # Spawn units (would integrate with unit spawning system)
        for i in range(min(unit_count, len(spawn_locations))):
            location = spawn_locations[i]
            # Would create and place unit here
            # self._create_reinforcement_unit(unit_type, location)
            # For now, just log the spawn attempt
            _ = (unit_type, location)  # Mark as intentionally unused
    
    def _apply_environmental_escalation(self, event: EscalationEvent) -> None:
        """Apply environmental changes to the battlefield.
        
        Args:
            event: The environmental escalation event
        """
        if event.data.get('wall_damage', False):
            # Damage walls or create new passages
            pass
        
        if event.data.get('block_exits', False):
            # Block escape routes
            pass
        
        if event.data.get('add_hazards', False):
            # Add new environmental hazards
            pass
    
    def _accelerate_hazard_spread(self, event: EscalationEvent) -> None:
        """Increase the spread rate of existing hazards.
        
        Args:
            event: The hazard acceleration event
        """
        spread_multiplier = event.data.get('spread_multiplier', 1.5)
        
        # Would integrate with hazard manager to increase spread rates
        # self.hazard_manager.set_spread_multiplier(spread_multiplier)
        # For now, just track that we would apply this multiplier
        _ = spread_multiplier  # Mark as intentionally unused
    
    def _apply_time_pressure(self, event: EscalationEvent) -> None:
        """Apply time-based pressure effects.
        
        Args:
            event: The time pressure event
        """
        if event.data.get('route_penalty', False):
            # Make movement more expensive
            movement_penalty = event.data.get('movement_cost_increase', 1)
            # Would apply to movement system
            _ = movement_penalty  # Mark as intentionally unused
    
    def _check_reinforcement_waves(self) -> None:
        """Check if any reinforcement waves should trigger."""
        for wave in self.reinforcement_waves:
            if wave.has_triggered and not wave.repeating:
                continue
            
            should_trigger = self._check_wave_trigger(wave)
            should_warn = self._should_warn_about_wave(wave)
            
            if should_warn and wave.warned_turn == -1:
                self._warn_about_wave(wave)
                wave.warned_turn = self.current_turn
            
            if should_trigger:
                self._spawn_reinforcement_wave(wave)
                wave.has_triggered = True
    
    def _check_wave_trigger(self, wave: ReinforcementWave) -> bool:
        """Check if a reinforcement wave should trigger.
        
        Args:
            wave: The reinforcement wave to check
            
        Returns:
            True if wave should trigger this turn
        """
        if wave.trigger_type == ReinforcementTrigger.TURN_BASED:
            return self.current_turn >= wave.trigger_value
        elif wave.trigger_type == ReinforcementTrigger.CASUALTY_BASED:
            return self.total_enemy_casualties >= wave.trigger_value
        # Add other trigger types as needed
        
        return False
    
    def _should_warn_about_wave(self, wave: ReinforcementWave) -> bool:
        """Check if players should be warned about incoming wave.
        
        Args:
            wave: The reinforcement wave to check
            
        Returns:
            True if warning should be given
        """
        if wave.trigger_type == ReinforcementTrigger.TURN_BASED:
            return self.current_turn >= (wave.trigger_value - wave.warning_turns)
        
        return False
    
    def _warn_about_wave(self, wave: ReinforcementWave) -> None:
        """Issue warning about incoming reinforcement wave.
        
        Args:
            wave: The reinforcement wave to warn about
        """
        # Emit warning about incoming reinforcements
        self._emit_log(f"Warning: Reinforcements approaching (arriving in {wave.warning_turns} turns)", "WARNING")
    
    def _spawn_reinforcement_wave(self, wave: ReinforcementWave) -> None:
        """Spawn units from a reinforcement wave.
        
        Args:
            wave: The reinforcement wave to spawn
        """
        # Spawn units at designated locations
        for i, location in enumerate(wave.spawn_locations[:wave.max_spawns]):
            if i < len(wave.unit_templates):
                template = wave.unit_templates[i]
                # Would create unit from template at location
                _ = (location, template)  # Mark as intentionally unused
    
    def _get_spawn_locations(self, pattern: str, count: int) -> list[Vector2]:
        """Get spawn locations based on pattern.
        
        Args:
            pattern: Spawn pattern type
            count: Number of locations needed
            
        Returns:
            List of spawn positions
        """
        locations = []
        
        if pattern == "random":
            # Find random valid spawn locations
            # Would use game map to find empty positions
            pass
        elif pattern == "behind":
            # Spawn behind player forces
            pass
        elif pattern == "surround":
            # Spawn to surround players
            pass
        elif pattern == "siege":
            # Spawn at siege positions
            pass
        
        # Placeholder - return some default positions
        for i in range(count):
            locations.append(Vector2(i, 0))
        
        return locations
    
    def _update_threat_level(self) -> None:
        """Update the overall battlefield threat level."""
        # Base threat increases over time
        base_threat = 1 + (self.current_turn // 5)
        
        # Modify based on casualties
        casualty_modifier = (self.total_enemy_casualties - self.total_player_casualties) * 0.1
        
        # Apply escalation multiplier
        self.current_threat_level = max(1, base_threat - casualty_modifier)
    
    def _apply_ongoing_effects(self) -> None:
        """Apply ongoing escalation effects each turn."""
        # Increase hazard intensity based on threat level
        if self.current_threat_level > 3:
            # Hazards become more dangerous
            pass
        
        # Apply time pressure effects
        if self.current_turn > 20:
            # Very long battles have additional penalties
            pass
    
    def report_casualty(self, unit: "Entity", is_enemy: bool) -> None:
        """Report a unit casualty for escalation tracking.
        
        Args:
            unit: The unit that was defeated
            is_enemy: True if this was an enemy unit
        """
        if is_enemy:
            self.total_enemy_casualties += 1
        else:
            self.total_player_casualties += 1
        
        # Check for casualty-based triggers
        self._check_casualty_triggers()
    
    def _check_casualty_triggers(self) -> None:
        """Check if casualty counts trigger any escalation events."""
        # Check reinforcement waves
        for wave in self.reinforcement_waves:
            if (wave.trigger_type == ReinforcementTrigger.CASUALTY_BASED and
                not wave.has_triggered and
                self.total_enemy_casualties >= wave.trigger_value):
                
                if wave.warned_turn == -1:
                    self._warn_about_wave(wave)
                    wave.warned_turn = self.current_turn
    
    def get_current_escalation_info(self) -> dict[str, Any]:
        """Get current escalation status information.
        
        Returns:
            Dictionary containing escalation status
        """
        return {
            "threat_level": self.current_threat_level,
            "turn": self.current_turn,
            "enemy_casualties": self.total_enemy_casualties,
            "player_casualties": self.total_player_casualties,
            "active_events": len(self.triggered_events),
            "upcoming_events": [
                event for i, event in enumerate(self.escalation_events)
                if i not in self.triggered_events and event.trigger_turn <= self.current_turn + 3
            ]
        }