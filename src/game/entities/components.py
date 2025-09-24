"""Game-specific components for units and other game entities.

This module contains the concrete component implementations for the Grimdark SRPG,
including the 5 core unit components: Actor, Health, Movement, Combat, and Status.
"""

from typing import TYPE_CHECKING, cast

from ...core.entities import Component
from ...core.data import UnitClass, Team, UNIT_CLASS_NAMES, UNIT_CLASS_DATA, Vector2, AOEPattern
from ...core.wounds import WoundEffect

if TYPE_CHECKING:
    from ...core.entities.components import Entity
    from ...core.data.game_info import UnitClassInfo
    from ..systems.interrupt_system import PreparedAction
    from ...core.wounds import Wound
    from ..ai.ai_behaviors import AIBehavior, AIDecision
    from ..map import GameMap
    from ...core.engine.timeline import Timeline


class ActorComponent(Component):
    """Component for identity and classification.
    
    Handles who the unit is in the game world - their name, class, team affiliation,
    and display information. This component provides the core identity that other
    components may reference for class-specific behaviors in the future.
    """
    
    def __init__(self, entity: "Entity", name: str, unit_class: UnitClass, team: Team):
        """Initialize actor component.
        
        Args:
            entity: The entity this component belongs to
            name: Display name of the unit
            unit_class: Unit class enum (Knight, Archer, etc.)
            team: Team affiliation enum (Player, Enemy, etc.)
        """
        super().__init__(entity)
        self.name = name
        self.unit_class = unit_class
        self.team = team
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Actor"
    
    def get_display_name(self) -> str:
        """Get the display name for this unit."""
        return self.name
    
    def get_class_name(self) -> str:
        """Get the human-readable class name."""
        return UNIT_CLASS_NAMES[self.unit_class]
    
    def get_class_info(self) -> "UnitClassInfo":
        """Get the class information for this unit's class."""
        return UNIT_CLASS_DATA[self.unit_class]
    
    def is_ally_of(self, other: "ActorComponent") -> bool:
        """Check if this unit is an ally of another unit.
        
        Args:
            other: The other unit's ActorComponent to check against
            
        Returns:
            True if units are on the same team, False otherwise
        """
        return self.team == other.team
    
    def get_symbol(self) -> str:
        """Get the display symbol for this unit's class."""
        return self.get_class_info().symbol


class HealthComponent(Component):
    """Component for life and death management.
    
    Handles the unit's vitality, including current and maximum hit points,
    damage and healing operations, and life/death state tracking.
    """
    
    def __init__(self, entity: "Entity", hp_max: int):
        """Initialize health component.
        
        Args:
            entity: The entity this component belongs to
            hp_max: Maximum hit points for this unit
        """
        super().__init__(entity)
        self.hp_max = hp_max
        self.hp_current = hp_max  # Start at full health
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Health"
    
    def is_alive(self) -> bool:
        """Check if the unit is alive.
        
        Returns:
            True if hp_current > 0, False otherwise
        """
        return self.hp_current > 0
    
    def get_hp_percent(self) -> float:
        """Get current health as a percentage of maximum.
        
        Returns:
            Health percentage from 0.0 to 1.0
        """
        if self.hp_max <= 0:
            return 0.0
        return self.hp_current / self.hp_max
    
    def take_damage(self, amount: int) -> int:
        """Apply damage to this unit.
        
        Args:
            amount: Amount of damage to apply
            
        Returns:
            Actual damage dealt (may be less due to overkill prevention)
        """
        if amount < 0:
            raise ValueError("Damage amount cannot be negative")
        
        old_hp = self.hp_current
        self.hp_current = max(0, self.hp_current - amount)
        return old_hp - self.hp_current
    
    def heal(self, amount: int) -> int:
        """Apply healing to this unit.
        
        Args:
            amount: Amount of healing to apply
            
        Returns:
            Actual healing done (may be less due to max hp cap)
        """
        if amount < 0:
            raise ValueError("Healing amount cannot be negative")
        
        old_hp = self.hp_current
        self.hp_current = min(self.hp_max, self.hp_current + amount)
        return self.hp_current - old_hp
    
    def set_max_hp(self, new_max: int) -> None:
        """Set a new maximum HP value.
        
        Args:
            new_max: New maximum HP value
        """
        if new_max < 0:
            raise ValueError("Maximum HP cannot be negative")
        
        self.hp_max = new_max
        # If current HP exceeds new max, reduce it
        if self.hp_current > self.hp_max:
            self.hp_current = self.hp_max
    
    def restore_full_health(self) -> None:
        """Restore unit to full health."""
        self.hp_current = self.hp_max


class MovementComponent(Component):
    """Component for position and movement capabilities.
    
    Handles the unit's spatial location, facing direction, and movement-related
    functionality including position tracking and orientation management.
    """
    
    def __init__(self, entity: "Entity", position: Vector2, movement_points: int):
        """Initialize movement component.
        
        Args:
            entity: The entity this component belongs to
            position: Initial position vector
            movement_points: Base movement points per turn
        """
        super().__init__(entity)
        self.position = position
        self.facing = "south"  # Default facing direction
        self.movement_points = movement_points
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Movement"
    
    def get_position(self) -> Vector2:
        """Get the current position vector.
        
        Returns:
            Vector2 position
        """
        return self.position
    
    def set_position(self, position: Vector2) -> None:
        """Set the position directly without movement logic.
        
        Args:
            position: New position vector
        """
        self.position = position
    
    def update_facing_from_movement(self, old_position: Vector2, new_position: Vector2) -> None:
        """Update facing direction based on movement between positions.
        
        Args:
            old_position: Previous position vector
            new_position: New position vector
        """
        dx = new_position.x - old_position.x
        dy = new_position.y - old_position.y
        
        if dx > 0:
            self.facing = "east"
        elif dx < 0:
            self.facing = "west"
        elif dy > 0:
            self.facing = "south"
        elif dy < 0:
            self.facing = "north"
        # If dx == 0 and dy == 0, keep current facing
    
    def face_direction(self, direction: str) -> None:
        """Set the facing direction explicitly.
        
        Args:
            direction: Direction to face ("north", "south", "east", "west")
        """
        if direction not in ["north", "south", "east", "west"]:
            raise ValueError(f"Invalid facing direction: {direction}")
        self.facing = direction
    
    def face_towards(self, target: Vector2) -> None:
        """Face towards a target position.
        
        Args:
            target: Position vector to face towards
        """
        dx = target.x - self.position.x
        dy = target.y - self.position.y
        
        # Face the direction with the largest absolute difference
        if abs(dx) > abs(dy):
            self.facing = "east" if dx > 0 else "west"
        elif dy != 0:
            self.facing = "south" if dy > 0 else "north"
        # If both are 0, keep current facing


class CombatComponent(Component):
    """Component for combat statistics and abilities.
    
    Handles combat-related data including attack and defense values,
    attack range, and damage calculations. This component focuses purely
    on combat mechanics and statistics.
    """
    
    def __init__(self, entity: "Entity", strength: int, defense: int, 
                 attack_range_min: int, attack_range_max: int, 
                 aoe_pattern: AOEPattern = AOEPattern.SINGLE):
        """Initialize combat component.
        
        Args:
            entity: The entity this component belongs to
            strength: Attack strength value
            defense: Defense value
            attack_range_min: Minimum attack range
            attack_range_max: Maximum attack range
            aoe_pattern: Area of effect pattern enum
        """
        super().__init__(entity)
        self.strength = strength
        self.defense = defense
        self.attack_range_min = attack_range_min
        self.attack_range_max = attack_range_max
        self.aoe_pattern = aoe_pattern
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Combat"
    
    def calculate_damage_to(self, target_combat: "CombatComponent") -> int:
        """Calculate damage this unit would deal to a target.
        
        Args:
            target_combat: The target's CombatComponent
            
        Returns:
            Damage amount (minimum 1)
        """
        base_damage = self.strength
        mitigation = target_combat.defense
        return max(1, base_damage - mitigation)
    
    def can_attack(self, target: Vector2) -> bool:
        """Check if this unit can attack a position based on range.
        
        Args:
            target: Target position vector
            
        Returns:
            True if position is within attack range, False otherwise
        """
        # Get position from movement component
        movement_component = self.entity.get_component("Movement")
        if movement_component is None:
            return False
        
        # Cast to MovementComponent to access position attribute
        movement = cast('MovementComponent', movement_component)
        
        # Calculate Manhattan distance
        distance = movement.position.manhattan_distance_to(target)
        
        return self.attack_range_min <= distance <= self.attack_range_max
    
    def get_attack_range(self) -> tuple[int, int]:
        """Get the attack range as a tuple.
        
        Returns:
            Tuple of (min_range, max_range)
        """
        return (self.attack_range_min, self.attack_range_max)


class StatusComponent(Component):
    """Component for turn state and action availability.
    
    Manages the unit's state within the turn-based system, including
    movement and action availability, turn initialization/cleanup,
    and speed/initiative tracking.
    """
    
    def __init__(self, entity: "Entity", speed: int):
        """Initialize status component.
        
        Args:
            entity: The entity this component belongs to
            speed: Speed/initiative value for turn order
        """
        super().__init__(entity)
        self.speed = speed
        self.has_moved = False
        self.has_acted = False
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Status"
    
    def can_move(self) -> bool:
        """Check if the unit can move this turn.
        
        Returns:
            True if unit is alive and hasn't moved yet, False otherwise
        """
        # Check if unit is alive
        health_component = self.entity.get_component("Health")
        if health_component is None:
            return False
        
        health = cast('HealthComponent', health_component)
        if not health.is_alive():
            return False
        
        return not self.has_moved
    
    def can_act(self) -> bool:
        """Check if the unit can perform an action this turn.
        
        Returns:
            True if unit is alive and hasn't acted yet, False otherwise
        """
        # Check if unit is alive
        health_component = self.entity.get_component("Health")
        if health_component is None:
            return False
        
        health = cast('HealthComponent', health_component)
        if not health.is_alive():
            return False
        
        return not self.has_acted
    
    def mark_moved(self) -> None:
        """Mark that the unit has moved this turn."""
        self.has_moved = True
    
    def mark_acted(self) -> None:
        """Mark that the unit has acted this turn."""
        self.has_acted = True
    
    def start_turn(self) -> None:
        """Initialize the unit for a new turn."""
        self.has_moved = False
        self.has_acted = False
    
    def end_turn(self) -> None:
        """Clean up the unit at the end of their turn."""
        # Currently same as start_turn, but kept separate for future expansion
        self.has_moved = False
        self.has_acted = False
    
    def get_turn_priority(self) -> int:
        """Get the turn priority for initiative order.
        
        Returns:
            Speed value for determining turn order (higher = earlier)
        """
        return self.speed


class InterruptComponent(Component):
    """Component for interrupt and prepared action management.
    
    This component tracks prepared actions that can be triggered by specific
    conditions during combat. It enables tactical depth through reactive
    abilities like overwatch, shield wall, and ambush attacks.
    """
    
    def __init__(self, entity: "Entity"):
        """Initialize interrupt component.
        
        Args:
            entity: The entity this component belongs to
        """
        super().__init__(entity)
        self.prepared_actions: list["PreparedAction"] = []
        self.max_prepared_actions = 1  # Limit to prevent complexity overload
        
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Interrupt"
    
    def can_prepare_action(self) -> bool:
        """Check if the unit can prepare another action.
        
        Returns:
            True if unit has available interrupt slots
        """
        return len(self.prepared_actions) < self.max_prepared_actions
    
    def add_prepared_action(self, prepared: "PreparedAction") -> bool:
        """Add a prepared action to this unit.
        
        Args:
            prepared: The prepared action to add
            
        Returns:
            True if action was added successfully
        """
        if not self.can_prepare_action():
            return False
            
        self.prepared_actions.append(prepared)
        return True
    
    def remove_prepared_action(self, prepared: "PreparedAction") -> bool:
        """Remove a specific prepared action.
        
        Args:
            prepared: The prepared action to remove
            
        Returns:
            True if action was found and removed
        """
        try:
            self.prepared_actions.remove(prepared)
            return True
        except ValueError:
            return False
    
    def clear_prepared_actions(self) -> int:
        """Clear all prepared actions.
        
        Returns:
            Number of actions that were cleared
        """
        count = len(self.prepared_actions)
        self.prepared_actions.clear()
        return count
    
    def get_prepared_actions(self) -> list["PreparedAction"]:
        """Get all current prepared actions.
        
        Returns:
            List of prepared actions (copy to prevent modification)
        """
        return self.prepared_actions.copy()
    
    def has_prepared_action_type(self, action_name: str) -> bool:
        """Check if unit has a specific type of prepared action.
        
        Args:
            action_name: Name of the action type to check for
            
        Returns:
            True if unit has this type of prepared action
        """
        return any(prep.action.name == action_name for prep in self.prepared_actions)
    
    def get_interrupt_stance_description(self) -> str:
        """Get a description of the unit's current interrupt stance.
        
        Returns:
            Human-readable description of prepared actions
        """
        if not self.prepared_actions:
            return "Ready"
            
        if len(self.prepared_actions) == 1:
            prep = self.prepared_actions[0]
            return f"{prep.action.name} ({prep.trigger.trigger_type.name})"
            
        return f"Multiple Interrupts ({len(self.prepared_actions)})"


class MoraleComponent(Component):
    """Component for morale and panic management.
    
    This component tracks a unit's psychological state, including courage,
    fear, and panic responses. It enables grimdark battlefield psychology
    where units can break under pressure and flee from hopeless situations.
    """
    
    def __init__(self, entity: "Entity", base_morale: int = 100, 
                 panic_threshold: int = 30, rout_threshold: int = 10):
        """Initialize morale component.
        
        Args:
            entity: The entity this component belongs to
            base_morale: Base morale value (default 100)
            panic_threshold: Morale level that triggers panic (default 30)
            rout_threshold: Morale level that triggers routing/fleeing (default 10)
        """
        super().__init__(entity)
        self.base_morale = base_morale
        self.current_morale = base_morale
        self.panic_threshold = panic_threshold
        self.rout_threshold = rout_threshold
        
        # State tracking
        self.is_panicked = False
        self.is_routed = False
        self.panic_duration = 0  # Turns spent in panic
        self.last_rally_attempt = -1  # Turn of last rally attempt
        
        # Morale modifiers
        self.temporary_modifiers = {}  # str -> int (modifier_name -> value)
        
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Morale"
    
    def get_effective_morale(self) -> int:
        """Get current morale including all modifiers.
        
        Returns:
            Effective morale value (clamped to 0-150 range)
        """
        effective = self.current_morale + sum(self.temporary_modifiers.values())
        return max(0, min(150, effective))
    
    def get_morale_state(self) -> str:
        """Get the unit's current morale state description.
        
        Returns:
            Human-readable morale state
        """
        if self.is_routed:
            return "Routed"
        elif self.is_panicked:
            return "Panicked"
        
        morale = self.get_effective_morale()
        if morale >= 90:
            return "Heroic"
        elif morale >= 70:
            return "Confident" 
        elif morale >= 50:
            return "Steady"
        elif morale >= 35:
            return "Shaken"
        elif morale >= 20:
            return "Afraid"
        else:
            return "Terrified"
    
    def modify_morale(self, amount: int, reason: str = "") -> int:
        """Modify current morale by the given amount.
        
        Args:
            amount: Amount to change morale by (positive or negative)
            reason: Optional reason for the morale change
            
        Returns:
            Actual morale change applied
        """
        old_morale = self.current_morale
        self.current_morale = max(0, min(150, self.current_morale + amount))
        actual_change = self.current_morale - old_morale
        
        # Check for state changes
        effective = self.get_effective_morale()
        
        # Check for panic entry
        if not self.is_panicked and effective <= self.panic_threshold:
            self.enter_panic_state(reason)
        
        # Check for rout entry
        if not self.is_routed and effective <= self.rout_threshold:
            self.enter_rout_state()
        
        # Check for recovery from panic (need higher threshold due to panic penalty)
        if self.is_panicked and not self.is_routed and effective >= self.panic_threshold + 15:
            self.exit_panic_state()
            
        return actual_change
    
    def add_temporary_modifier(self, name: str, value: int) -> None:
        """Add a temporary morale modifier.
        
        Args:
            name: Name of the modifier (e.g., "nearby_ally", "leader_present")
            value: Modifier value (positive or negative)
        """
        self.temporary_modifiers[name] = value
    
    def remove_temporary_modifier(self, name: str) -> bool:
        """Remove a temporary morale modifier.
        
        Args:
            name: Name of the modifier to remove
            
        Returns:
            True if modifier was found and removed
        """
        return self.temporary_modifiers.pop(name, None) is not None
    
    def clear_temporary_modifiers(self) -> None:
        """Clear all temporary morale modifiers."""
        self.temporary_modifiers.clear()
    
    def enter_panic_state(self, reason: str = "morale_collapse") -> None:
        """Enter panic state due to low morale.
        
        Args:
            reason: Reason for entering panic state
        """
        if not self.is_panicked:
            self.is_panicked = True
            self.panic_duration = 0
            # Panic causes immediate morale penalties
            self.add_temporary_modifier("panic_penalty", -10)
    
    def enter_rout_state(self) -> None:
        """Enter rout state - unit will attempt to flee battlefield."""
        if not self.is_routed:
            self.is_routed = True
            self.is_panicked = True  # Routed units are always panicked
            self.add_temporary_modifier("rout_penalty", -20)
    
    def exit_panic_state(self) -> None:
        """Exit panic state due to morale recovery."""
        if self.is_panicked and not self.is_routed:
            self.is_panicked = False
            self.panic_duration = 0
            self.remove_temporary_modifier("panic_penalty")
    
    def attempt_rally(self, turn: int, rally_bonus: int = 15) -> bool:
        """Attempt to rally unit out of panic state.
        
        Args:
            turn: Current turn number
            rally_bonus: Morale bonus if rally succeeds
            
        Returns:
            True if rally was successful
        """
        # Prevent spam rallying
        if turn - self.last_rally_attempt < 2:
            return False
        
        self.last_rally_attempt = turn
        
        # Rally chance based on current effective morale
        # Rally chance: 10-80% based on effective morale
        
        # Apply rally bonus first, then check if it's enough to recover
        self.modify_morale(rally_bonus, "rally_success")
        
        # Rally succeeds if the bonus brought morale above panic threshold
        rally_success = self.get_effective_morale() > self.panic_threshold + 5
        
        if rally_success and not self.is_routed:
            # The modify_morale call above should have already triggered exit_panic_state
            # if morale is high enough, but call it explicitly for certainty
            if self.is_panicked:
                self.exit_panic_state()
            return True
        
        return False
    
    def process_turn_effects(self) -> None:
        """Process ongoing morale effects at the start/end of turn."""
        if self.is_panicked:
            self.panic_duration += 1
            
            # Panic naturally wears off over time (slowly)
            if self.panic_duration > 3:
                recovery_amount = max(1, self.panic_duration // 2)
                self.modify_morale(recovery_amount, "panic_recovery")
    
    def get_combat_penalties(self) -> dict[str, int]:
        """Get combat penalties due to morale state.
        
        Returns:
            Dictionary of penalty types and values
        """
        penalties = {}
        
        if self.is_routed:
            penalties['attack'] = -3
            penalties['defense'] = -2
            penalties['movement'] = 1  # Actually a bonus - they move faster when fleeing
        elif self.is_panicked:
            penalties['attack'] = -2
            penalties['accuracy'] = -15  # Percentage penalty
        
        effective = self.get_effective_morale()
        if effective < 40:
            penalties['defense'] = penalties.get('defense', 0) - 1
        
        return penalties
    
    def should_flee_from_combat(self) -> bool:
        """Check if unit should avoid combat due to low morale.
        
        Returns:
            True if unit should avoid engaging in combat
        """
        return self.is_routed or (self.is_panicked and self.get_effective_morale() < 25)


class WoundComponent(Component):
    """Component for wound and injury management.
    
    This component tracks persistent injuries that affect unit performance
    and persist across battles. Wounds can heal over time or become permanent
    scars that never fully recover.
    """
    
    def __init__(self, entity: "Entity"):
        """Initialize wound component.
        
        Args:
            entity: The entity this component belongs to
        """
        super().__init__(entity)
        self.active_wounds: list[Wound] = []
        self.permanent_scars: list[Wound] = []
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "Wound"
    
    def add_wound(self, wound: "Wound") -> None:
        """Add a new wound to the unit.
        
        Args:
            wound: The wound to add
        """
        self.active_wounds.append(wound)
    
    def get_active_wounds(self) -> list["Wound"]:
        """Get all currently active wounds.
        
        Returns:
            List of active wounds
        """
        return self.active_wounds.copy()
    
    def remove_wound(self, wound: "Wound") -> bool:
        """Remove a wound (when it heals).
        
        Args:
            wound: The wound to remove
            
        Returns:
            True if wound was found and removed
        """
        if wound in self.active_wounds:
            self.active_wounds.remove(wound)
            return True
        return False
    
    def get_total_wound_effects(self) -> "WoundEffect":
        """Calculate combined effects of all wounds and scars.
        
        Returns:
            Combined wound effect
        """
        
        if not self.active_wounds and not self.permanent_scars:
            return WoundEffect()
        
        total_effect = WoundEffect()
        for wound in self.active_wounds + self.permanent_scars:
            total_effect = total_effect.combine_with(wound.get_current_effect())
        
        return total_effect
    
    def get_wound_penalties(self) -> dict[str, int]:
        """Get combat penalties from wounds.
        
        Returns:
            Dictionary of stat penalties
        """
        effects = self.get_total_wound_effects()
        return {
            'attack': effects.attack_modifier,
            'defense': effects.defense_modifier,
            'speed': effects.speed_modifier,
            'accuracy': effects.accuracy_modifier,
            'evasion': effects.evasion_modifier,
        }
    
    def has_wounds(self) -> bool:
        """Check if unit has any active wounds.
        
        Returns:
            True if unit has wounds
        """
        return len(self.active_wounds) > 0
    
    def get_wound_count(self) -> int:
        """Get total number of active wounds.
        
        Returns:
            Number of active wounds
        """
        return len(self.active_wounds)
    
    def process_wound_turn(self, turn: int) -> list[str]:
        """Process wound healing and effects for a turn.
        
        Args:
            turn: Current turn number
            
        Returns:
            List of messages about wound changes
        """
        messages = []
        wounds_to_remove = []
        wounds_to_scar = []
        
        for wound in self.active_wounds:
            # TODO: Integrate wound tick system properly with component architecture
            # wound.tick requires Unit but component only has Entity - needs design review
            
            # Check if wound has healed
            if wound.is_healed():
                wounds_to_remove.append(wound)
                messages.append(f"{wound.properties.body_part.name.title()} {wound.properties.wound_type.name.lower()} wound has healed")
            
            # Check if wound becomes permanent scar
            elif wound.is_scarred:
                wounds_to_scar.append(wound)
                messages.append(f"{wound.properties.body_part.name.title()} {wound.properties.wound_type.name.lower()} wound has become a permanent scar")
        
        # Remove healed wounds
        for wound in wounds_to_remove:
            self.remove_wound(wound)
        
        # Move scarred wounds to permanent list
        for wound in wounds_to_scar:
            self.remove_wound(wound)
            wound.make_permanent()
            self.permanent_scars.append(wound)
        
        return messages


class AIComponent(Component):
    """Component for AI decision-making and behavior.
    
    This component manages AI behavior for units, using the Strategy pattern
    to allow different types of AI behaviors to be plugged in dynamically.
    """
    
    def __init__(self, entity: "Entity", ai_behavior: "AIBehavior"):
        """Initialize AI component.
        
        Args:
            entity: The entity this component belongs to
            ai_behavior: The AI behavior strategy to use
        """
        super().__init__(entity)
        self.behavior: AIBehavior = ai_behavior
        self.memory: dict = {}  # For learning and adaptation in future
    
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        return "AI"
    
    def make_decision(self, game_map: "GameMap", timeline: "Timeline") -> "AIDecision":
        """Make a decision for the current turn.
        
        Args:
            game_map: The current game map
            timeline: The timeline system for turn order awareness
            
        Returns:
            AIDecision with action and target information
        """
        # Get the unit from our entity (assumes Unit wraps Entity)
        # This is a bit of a hack but maintains backward compatibility
        unit = None
        for map_unit in game_map.units:
            if map_unit.unit_id == self.entity.entity_id:
                unit = map_unit
                break
        
        if unit is None:
            return AIDecision(
                action_name="Wait",
                confidence=0.0,
                reasoning="Unit not found on game map"
            )
        
        return self.behavior.choose_action(unit, game_map, timeline)
    
    def set_behavior(self, new_behavior: "AIBehavior") -> None:
        """Change the AI behavior strategy.
        
        Args:
            new_behavior: The new AI behavior to use
        """
        self.behavior = new_behavior
    
    def get_behavior_name(self) -> str:
        """Get the name of the current AI behavior."""
        return self.behavior.get_behavior_name()