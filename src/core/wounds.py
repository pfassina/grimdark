"""
Wound & Scarring System - Persistent battle consequences

This module defines the wound system where units can receive temporary and
permanent injuries that affect their performance. Wounds persist across
battles and can become permanent scars that never heal.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.game.unit import Unit


class WoundSeverity(Enum):
    """Severity levels for wounds"""
    MINOR = auto()      # Heals naturally over time
    MODERATE = auto()   # Requires treatment, may scar
    SEVERE = auto()     # Likely to scar, serious penalties
    CRITICAL = auto()   # Permanent disability, massive penalties
    MORTAL = auto()     # Unit will die without immediate aid


class WoundType(Enum):
    """Types of wounds that can be inflicted"""
    SLASH = auto()          # Blade wounds, bleeding
    PIERCE = auto()         # Puncture wounds, internal damage
    CRUSH = auto()          # Blunt trauma, broken bones
    BURN = auto()           # Fire/heat damage, permanent scarring
    FROST = auto()          # Cold damage, tissue death
    POISON = auto()         # Toxin damage, ongoing effects
    PSYCHIC = auto()        # Mental trauma, morale damage
    DISEASE = auto()        # Infection, spreads to others
    AMPUTATION = auto()     # Loss of limb, permanent


class BodyPart(Enum):
    """Body parts that can be wounded"""
    HEAD = auto()
    TORSO = auto()
    LEFT_ARM = auto()
    RIGHT_ARM = auto()
    LEFT_LEG = auto()
    RIGHT_LEG = auto()
    EYES = auto()
    INTERNAL = auto()  # Internal organs


@dataclass
class WoundEffect:
    """Effects that a wound applies to a unit"""
    # Stat modifiers (negative values are penalties)
    hp_max_modifier: int = 0
    attack_modifier: int = 0
    defense_modifier: int = 0
    speed_modifier: int = 0
    accuracy_modifier: int = 0
    evasion_modifier: int = 0
    
    # Action limitations
    cannot_use_items: bool = False
    cannot_use_abilities: bool = False
    cannot_counter: bool = False
    cannot_move: bool = False
    
    # Ongoing effects
    bleeding_damage: int = 0  # Damage per turn
    infection_chance: float = 0.0  # Chance to worsen each turn
    morale_penalty: int = 0  # Reduces unit and nearby ally morale
    
    # Status conditions
    status_effects: list[str] = field(default_factory=list)
    
    def combine_with(self, other: WoundEffect) -> WoundEffect:
        """Combine multiple wound effects"""
        return WoundEffect(
            hp_max_modifier=self.hp_max_modifier + other.hp_max_modifier,
            attack_modifier=self.attack_modifier + other.attack_modifier,
            defense_modifier=self.defense_modifier + other.defense_modifier,
            speed_modifier=self.speed_modifier + other.speed_modifier,
            accuracy_modifier=self.accuracy_modifier + other.accuracy_modifier,
            evasion_modifier=self.evasion_modifier + other.evasion_modifier,
            cannot_use_items=self.cannot_use_items or other.cannot_use_items,
            cannot_use_abilities=self.cannot_use_abilities or other.cannot_use_abilities,
            cannot_counter=self.cannot_counter or other.cannot_counter,
            cannot_move=self.cannot_move or other.cannot_move,
            bleeding_damage=self.bleeding_damage + other.bleeding_damage,
            infection_chance=max(self.infection_chance, other.infection_chance),
            morale_penalty=self.morale_penalty + other.morale_penalty,
            status_effects=list(set(self.status_effects + other.status_effects))
        )


@dataclass
class WoundProperties:
    """Configuration for a wound's behavior"""
    wound_type: WoundType
    severity: WoundSeverity
    body_part: BodyPart
    name: str
    description: str
    
    # Healing properties
    base_healing_time: int = 100  # Ticks to heal naturally
    requires_treatment: bool = False  # Needs medical attention
    can_worsen: bool = True  # Can deteriorate if untreated
    scar_chance: float = 0.0  # Probability of permanent scarring
    
    # Effects
    immediate_effect: WoundEffect = field(default_factory=WoundEffect)
    ongoing_effect: WoundEffect = field(default_factory=WoundEffect)
    scar_effect: Optional[WoundEffect] = None  # Permanent effect if scarred
    
    # Visuals
    icon: str = "🩹"
    color_hint: str = "red"


class Wound(ABC):
    """Base class for all wounds"""
    
    def __init__(self, properties: WoundProperties, 
                 source_damage: int = 0,
                 source_unit: Optional[Unit] = None):
        """
        Initialize a wound
        
        Args:
            properties: Configuration for wound behavior
            source_damage: Amount of damage that caused the wound
            source_unit: Unit that inflicted the wound
        """
        self.properties = properties
        self.source_damage = source_damage
        self.source_unit = source_unit
        
        # Wound state
        self.healing_progress: int = 0
        self.is_treated: bool = False
        self.is_infected: bool = False
        self.is_scarred: bool = False
        self.time_since_injury: int = 0
        
    @abstractmethod
    def tick(self, unit: Unit, current_time: int) -> list[WoundEvent]:
        """
        Process one tick of wound behavior
        
        Returns list of wound events (bleeding, infection, etc)
        """
        pass
    
    @abstractmethod
    def apply_treatment(self, treatment_quality: int) -> bool:
        """
        Apply medical treatment to the wound
        
        Args:
            treatment_quality: Quality of treatment (0-100)
            
        Returns:
            True if treatment was successful
        """
        pass
    
    @abstractmethod
    def get_current_effect(self) -> WoundEffect:
        """Get the current effect of this wound"""
        pass
    
    def can_heal_naturally(self) -> bool:
        """Check if wound can heal without treatment"""
        return not self.properties.requires_treatment or self.is_treated
    
    def is_healed(self) -> bool:
        """Check if wound is fully healed"""
        return self.healing_progress >= self.properties.base_healing_time and not self.is_scarred
    
    def worsen(self) -> None:
        """Make the wound worse (infection, reopening, etc)"""
        self.healing_progress = max(0, self.healing_progress - 20)
        if not self.is_infected and self.properties.ongoing_effect.infection_chance > 0:
            import random
            if random.random() < self.properties.ongoing_effect.infection_chance:
                self.is_infected = True


@dataclass
class WoundEvent:
    """Event generated by wound processing"""
    event_type: str  # "bleeding", "infection", "healed", "scarred", etc
    wound: Wound
    data: dict = field(default_factory=dict)


# Concrete Wound Implementations

class SlashWound(Wound):
    """Bleeding cuts from bladed weapons"""
    
    @classmethod
    def get_default_properties(cls, body_part: BodyPart, severity: WoundSeverity) -> WoundProperties:
        severity_effects = {
            WoundSeverity.MINOR: WoundEffect(
                hp_max_modifier=-2,
                bleeding_damage=1,
                status_effects=["bleeding"]
            ),
            WoundSeverity.MODERATE: WoundEffect(
                hp_max_modifier=-5,
                attack_modifier=-2,
                bleeding_damage=2,
                status_effects=["bleeding"]
            ),
            WoundSeverity.SEVERE: WoundEffect(
                hp_max_modifier=-10,
                attack_modifier=-5,
                defense_modifier=-3,
                bleeding_damage=3,
                cannot_use_items=True,
                status_effects=["bleeding", "weakened"]
            ),
            WoundSeverity.CRITICAL: WoundEffect(
                hp_max_modifier=-15,
                attack_modifier=-8,
                defense_modifier=-5,
                speed_modifier=-20,
                bleeding_damage=5,
                cannot_use_abilities=True,
                cannot_counter=True,
                status_effects=["bleeding", "crippled"]
            )
        }
        
        return WoundProperties(
            wound_type=WoundType.SLASH,
            severity=severity,
            body_part=body_part,
            name=f"{severity.name.title()} {body_part.name.title()} Gash",
            description="Deep laceration causing bleeding",
            base_healing_time=100 + (severity.value * 50),
            requires_treatment=severity.value >= WoundSeverity.MODERATE.value,
            scar_chance=0.1 * severity.value,
            immediate_effect=severity_effects.get(severity, WoundEffect()),
            ongoing_effect=WoundEffect(bleeding_damage=1),
            scar_effect=WoundEffect(hp_max_modifier=-2) if severity.value >= WoundSeverity.SEVERE.value else None,
            icon="🩸",
            color_hint="red"
        )
    
    def __init__(self, body_part: BodyPart, severity: WoundSeverity, 
                 source_damage: int = 0, source_unit: Optional[Unit] = None):
        super().__init__(
            self.get_default_properties(body_part, severity),
            source_damage,
            source_unit
        )
        
    def tick(self, unit: Unit, current_time: int) -> list[WoundEvent]:
        events = []
        self.time_since_injury += 1
        
        # Apply bleeding damage
        if self.properties.ongoing_effect.bleeding_damage > 0 and not self.is_treated:
            events.append(WoundEvent(
                "bleeding",
                self,
                {"damage": self.properties.ongoing_effect.bleeding_damage}
            ))
        
        # Natural healing if possible
        if self.can_heal_naturally():
            self.healing_progress += 1
            if self.is_healed():
                events.append(WoundEvent("healed", self))
        
        # Check for scarring
        if self.healing_progress >= self.properties.base_healing_time and not self.is_scarred:
            import random
            if random.random() < self.properties.scar_chance:
                self.is_scarred = True
                events.append(WoundEvent("scarred", self))
        
        return events
    
    def apply_treatment(self, treatment_quality: int) -> bool:
        if self.is_treated:
            return False
            
        self.is_treated = True
        # Better treatment reduces bleeding and speeds healing
        self.healing_progress += treatment_quality // 2
        self.properties.ongoing_effect.bleeding_damage = max(0, 
            self.properties.ongoing_effect.bleeding_damage - (treatment_quality // 30))
        return True
    
    def get_current_effect(self) -> WoundEffect:
        if self.is_scarred and self.properties.scar_effect:
            return self.properties.scar_effect
        if self.is_infected:
            # Infection worsens effects
            base = self.properties.immediate_effect
            return WoundEffect(
                hp_max_modifier=base.hp_max_modifier * 2,
                attack_modifier=base.attack_modifier * 2,
                defense_modifier=base.defense_modifier * 2,
                infection_chance=0.3,
                status_effects=base.status_effects + ["infected"]
            )
        return self.properties.immediate_effect


class BrokenBone(Wound):
    """Fractures and breaks from crushing damage"""
    
    @classmethod
    def get_default_properties(cls, body_part: BodyPart, severity: WoundSeverity) -> WoundProperties:
        # Broken bones have severe movement/action penalties
        if body_part in [BodyPart.LEFT_LEG, BodyPart.RIGHT_LEG]:
            effect = WoundEffect(
                speed_modifier=-50 if severity.value >= WoundSeverity.MODERATE.value else -20,
                evasion_modifier=-20,
                cannot_move=severity.value >= WoundSeverity.SEVERE.value,
                status_effects=["hobbled"]
            )
        elif body_part in [BodyPart.LEFT_ARM, BodyPart.RIGHT_ARM]:
            effect = WoundEffect(
                attack_modifier=-10 if severity.value >= WoundSeverity.MODERATE.value else -5,
                cannot_use_items=True,
                cannot_counter=severity.value >= WoundSeverity.SEVERE.value,
                status_effects=["maimed"]
            )
        else:  # Torso, ribs
            effect = WoundEffect(
                hp_max_modifier=-10,
                defense_modifier=-5,
                status_effects=["broken_ribs"]
            )
        
        return WoundProperties(
            wound_type=WoundType.CRUSH,
            severity=severity,
            body_part=body_part,
            name=f"Broken {body_part.name.title()}",
            description="Fractured bones causing severe impairment",
            base_healing_time=300,  # Bones take long to heal
            requires_treatment=True,  # Always needs setting
            scar_chance=0.2,  # May heal improperly
            immediate_effect=effect,
            scar_effect=WoundEffect(
                speed_modifier=-10 if body_part in [BodyPart.LEFT_LEG, BodyPart.RIGHT_LEG] else 0,
                attack_modifier=-5 if body_part in [BodyPart.LEFT_ARM, BodyPart.RIGHT_ARM] else 0
            ),
            icon="🦴",
            color_hint="white"
        )
    
    def __init__(self, body_part: BodyPart, severity: WoundSeverity,
                 source_damage: int = 0, source_unit: Optional[Unit] = None):
        super().__init__(
            self.get_default_properties(body_part, severity),
            source_damage,
            source_unit
        )
        self.is_set_properly = False  # Bone needs to be set by treatment
        
    def tick(self, unit: Unit, current_time: int) -> list[WoundEvent]:
        events = []
        self.time_since_injury += 1
        
        # Bones only heal if properly set
        if self.is_set_properly:
            self.healing_progress += 1
            if self.healing_progress >= self.properties.base_healing_time:
                if not self.is_scarred:
                    import random
                    # Improper healing chance
                    if random.random() < self.properties.scar_chance:
                        self.is_scarred = True
                        events.append(WoundEvent("scarred", self, 
                            {"message": "Bone healed improperly"}))
                    else:
                        events.append(WoundEvent("healed", self))
        elif self.time_since_injury > 50:
            # Untreated broken bones get worse
            self.worsen()
            
        return events
    
    def apply_treatment(self, treatment_quality: int) -> bool:
        if self.is_set_properly:
            return False
            
        # Quality determines if bone sets properly
        import random
        success_chance = treatment_quality / 100.0
        if random.random() < success_chance:
            self.is_set_properly = True
            self.is_treated = True
            return True
        return False
    
    def get_current_effect(self) -> WoundEffect:
        if self.is_scarred and self.properties.scar_effect:
            return self.properties.scar_effect
        return self.properties.immediate_effect


class Burn(Wound):
    """Burns from fire and heat that often scar permanently"""
    
    @classmethod
    def get_default_properties(cls, severity: WoundSeverity) -> WoundProperties:
        severity_effects = {
            WoundSeverity.MINOR: WoundEffect(
                hp_max_modifier=-3,
                status_effects=["burned"]
            ),
            WoundSeverity.MODERATE: WoundEffect(
                hp_max_modifier=-7,
                defense_modifier=-3,
                morale_penalty=5,
                status_effects=["burned", "pain"]
            ),
            WoundSeverity.SEVERE: WoundEffect(
                hp_max_modifier=-12,
                defense_modifier=-5,
                evasion_modifier=-10,
                morale_penalty=10,
                status_effects=["burned", "agony", "disfigured"]
            ),
            WoundSeverity.CRITICAL: WoundEffect(
                hp_max_modifier=-20,
                attack_modifier=-10,
                defense_modifier=-10,
                speed_modifier=-30,
                morale_penalty=20,
                cannot_use_abilities=True,
                status_effects=["burned", "agony", "horrific_scars"]
            )
        }
        
        return WoundProperties(
            wound_type=WoundType.BURN,
            severity=severity,
            body_part=BodyPart.TORSO,  # Burns affect general area
            name=f"{severity.name.title()} Burns",
            description="Painful burns that will likely scar",
            base_healing_time=200,
            requires_treatment=severity.value >= WoundSeverity.MODERATE.value,
            scar_chance=0.8,  # Burns almost always scar
            immediate_effect=severity_effects.get(severity, WoundEffect()),
            scar_effect=WoundEffect(
                hp_max_modifier=-3 * severity.value,
                morale_penalty=5 * severity.value,
                status_effects=["scarred"]
            ),
            icon="🔥",
            color_hint="orange"
        )
    
    def __init__(self, severity: WoundSeverity,
                 source_damage: int = 0, source_unit: Optional[Unit] = None):
        super().__init__(
            self.get_default_properties(severity),
            source_damage,
            source_unit
        )
        
    def tick(self, unit: Unit, current_time: int) -> list[WoundEvent]:
        events = []
        self.time_since_injury += 1
        
        # Burns heal slowly and painfully
        if self.can_heal_naturally():
            self.healing_progress += 1
            
            # Check for scarring (very likely with burns)
            if self.healing_progress >= self.properties.base_healing_time // 2:
                if not self.is_scarred:
                    import random
                    if random.random() < self.properties.scar_chance:
                        self.is_scarred = True
                        events.append(WoundEvent("scarred", self,
                            {"message": "Burns have left permanent scars"}))
            
            if self.healing_progress >= self.properties.base_healing_time:
                events.append(WoundEvent("healed", self))
        
        return events
    
    def apply_treatment(self, treatment_quality: int) -> bool:
        if self.is_treated:
            return False
            
        self.is_treated = True
        # Good treatment reduces scarring chance
        self.properties.scar_chance *= (1.0 - treatment_quality / 200.0)
        self.healing_progress += treatment_quality // 4
        return True
    
    def get_current_effect(self) -> WoundEffect:
        if self.is_scarred and self.properties.scar_effect:
            # Burned scars are particularly debilitating
            return self.properties.scar_effect
        return self.properties.immediate_effect


class Amputation(Wound):
    """Permanent loss of limb - cannot be healed"""
    
    @classmethod
    def get_default_properties(cls, body_part: BodyPart) -> WoundProperties:
        if body_part == BodyPart.LEFT_ARM or body_part == BodyPart.RIGHT_ARM:
            effect = WoundEffect(
                hp_max_modifier=-10,
                attack_modifier=-15,
                defense_modifier=-10,
                cannot_use_items=True,
                cannot_counter=True,
                morale_penalty=30,
                status_effects=["amputee", "one_armed"]
            )
        elif body_part == BodyPart.LEFT_LEG or body_part == BodyPart.RIGHT_LEG:
            effect = WoundEffect(
                hp_max_modifier=-10,
                speed_modifier=-75,
                evasion_modifier=-30,
                cannot_move=False,  # Can still hobble
                morale_penalty=30,
                status_effects=["amputee", "one_legged"]
            )
        else:
            # Shouldn't happen but handle gracefully
            effect = WoundEffect(
                hp_max_modifier=-20,
                morale_penalty=50,
                status_effects=["amputee", "mutilated"]
            )
        
        return WoundProperties(
            wound_type=WoundType.AMPUTATION,
            severity=WoundSeverity.CRITICAL,
            body_part=body_part,
            name=f"Lost {body_part.name.title()}",
            description="Permanent loss of limb",
            base_healing_time=100,  # Stump heals but limb never returns
            requires_treatment=True,
            scar_chance=1.0,  # Always permanent
            immediate_effect=effect,
            scar_effect=effect,  # Effect never goes away
            icon="🦾",
            color_hint="dark_red"
        )
    
    def __init__(self, body_part: BodyPart,
                 source_damage: int = 0, source_unit: Optional[Unit] = None):
        super().__init__(
            self.get_default_properties(body_part),
            source_damage,
            source_unit
        )
        self.is_scarred = True  # Always permanent
        
    def tick(self, unit: Unit, current_time: int) -> list[WoundEvent]:
        events = []
        
        # Stump needs to heal to prevent infection
        if not self.is_healed() and self.is_treated:
            self.healing_progress += 1
            if self.healing_progress >= self.properties.base_healing_time:
                events.append(WoundEvent("stump_healed", self,
                    {"message": "Amputation site has healed"}))
        elif not self.is_treated and self.time_since_injury > 20:
            # Untreated amputation leads to death
            events.append(WoundEvent("mortal", self,
                {"message": "Bleeding out from amputation"}))
        
        self.time_since_injury += 1
        return events
    
    def apply_treatment(self, treatment_quality: int) -> bool:
        if self.is_treated:
            return False
            
        # Treatment stops bleeding and starts healing
        self.is_treated = True
        self.healing_progress += treatment_quality // 2
        return True
    
    def get_current_effect(self) -> WoundEffect:
        # Amputation effects are always active
        return self.properties.immediate_effect


# Wound Factory

def create_wound_from_damage(damage: int, damage_type: str, 
                            target_unit: Optional[Unit] = None,
                            source_unit: Optional[Unit] = None) -> Optional[Wound]:
    """
    Create an appropriate wound based on damage dealt
    
    Args:
        damage: Amount of damage dealt
        damage_type: Type of damage (physical, fire, etc)
        target_unit: Unit receiving the wound
        source_unit: Unit causing the wound
        
    Returns:
        Wound instance or None if no wound inflicted
    """
    import random
    
    # Determine if wound is inflicted based on damage
    wound_chance = min(0.8, damage / 30.0)  # Max 80% chance
    if random.random() > wound_chance:
        return None
    
    # Determine severity based on damage
    if damage < 10:
        severity = WoundSeverity.MINOR
    elif damage < 20:
        severity = WoundSeverity.MODERATE
    elif damage < 30:
        severity = WoundSeverity.SEVERE
    elif damage < 40:
        severity = WoundSeverity.CRITICAL
    else:
        severity = WoundSeverity.MORTAL
    
    # Determine body part
    body_parts = list(BodyPart)
    body_part = random.choice(body_parts)
    
    # Create wound based on damage type
    if damage_type == "fire":
        return Burn(severity, damage, source_unit)
    elif damage_type == "crushing":
        return BrokenBone(body_part, severity, damage, source_unit)
    elif damage_type in ["slashing", "physical"]:
        return SlashWound(body_part, severity, damage, source_unit)
    elif damage >= 50 and random.random() < 0.1:  # 10% chance on massive damage
        # Amputation on limbs only
        limbs = [BodyPart.LEFT_ARM, BodyPart.RIGHT_ARM, BodyPart.LEFT_LEG, BodyPart.RIGHT_LEG]
        if body_part in limbs:
            return Amputation(body_part, damage, source_unit)
    
    # Default to slash wound
    return SlashWound(body_part, severity, damage, source_unit)