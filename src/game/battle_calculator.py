"""
Battle calculation system for damage prediction and forecasting.

This module provides battle forecast calculations separate from actual combat resolution,
allowing the UI to show damage/hit/crit predictions without affecting game state.
"""
import random

from ..core.renderable import BattleForecastRenderData
from .unit import Unit


class BattleCalculator:
    """Calculates battle forecasts for damage prediction."""
    
    @staticmethod
    def calculate_forecast(attacker: Unit, defender: Unit, weapon_range: int = 1) -> BattleForecastRenderData:
        """
        Calculate complete battle forecast between two units.
        
        Args:
            attacker: The attacking unit
            defender: The defending unit  
            weapon_range: Range of the attack (affects counter-attack possibility)
            
        Returns:
            BattleForecastRenderData with all prediction values
        """
        # Basic damage calculation (average)
        damage = BattleCalculator._calculate_average_damage(attacker, defender)
        
        # Damage range calculation
        min_damage, max_damage = BattleCalculator._calculate_damage_range(attacker, defender)
        
        # No hit chance calculation - all attacks hit in new system
        # Critical hit chance calculation
        crit_chance = BattleCalculator._calculate_crit_chance(attacker, defender)
        
        # Counter-attack possibility
        can_counter = BattleCalculator._can_counter_attack(defender, weapon_range)
        counter_damage = 0
        counter_min_damage = 0
        counter_max_damage = 0
        if can_counter:
            counter_damage = BattleCalculator._calculate_average_damage(defender, attacker)
            counter_min_damage, counter_max_damage = BattleCalculator._calculate_damage_range(defender, attacker)
        
        return BattleForecastRenderData(
            x=0, y=0,  # Position will be set by renderer
            attacker_name=f"{attacker.actor.get_class_name()}",
            defender_name=f"{defender.actor.get_class_name()}",
            damage=damage,
            hit_chance=100,  # All attacks hit in new system
            crit_chance=crit_chance,
            can_counter=can_counter,
            counter_damage=counter_damage,
            min_damage=min_damage,
            max_damage=max_damage,
            counter_min_damage=counter_min_damage,
            counter_max_damage=counter_max_damage
        )
    
    @staticmethod
    def _calculate_damage(attacker: Unit, defender: Unit) -> int:
        """Calculate expected damage from attacker to defender with variance."""
        
        # Basic formula: Strength - Defense/2, minimum 1 (matches combat_resolver.py)
        base_damage = max(1, attacker.combat.strength - defender.combat.defense // 2)
        
        # Add damage variance (±25% of base damage, minimum 1)
        # This creates the "6-10 instead of flat 8" variance mentioned in design
        variance_range = max(1, base_damage // 4)  # 25% variance
        variance = random.randint(-variance_range, variance_range)
        final_damage = max(1, base_damage + variance)
        
        return final_damage
    
    @staticmethod
    def _calculate_average_damage(attacker: Unit, defender: Unit) -> int:
        """Calculate average damage without variance for forecast display."""
        # Basic formula: Strength - Defense/2, minimum 1
        base_damage = max(1, attacker.combat.strength - defender.combat.defense // 2)
        return base_damage
    
    @staticmethod
    def _calculate_damage_range(attacker: Unit, defender: Unit) -> tuple[int, int]:
        """Calculate min and max damage range for forecast display."""
        # Get base damage (no variance)
        base_damage = max(1, attacker.combat.strength - defender.combat.defense // 2)
        
        # Calculate variance range (±25% of base damage, minimum 1)
        variance_range = max(1, base_damage // 4)  # 25% variance
        
        min_damage = max(1, base_damage - variance_range)
        max_damage = base_damage + variance_range
        
        return min_damage, max_damage
    
    @staticmethod
    def _calculate_crit_chance(attacker: Unit, defender: Unit) -> int:
        """Calculate critical hit chance percentage (0-100)."""
        # Formula based on speed difference between attacker and defender
        base_crit = 5  # Base crit rate
        speed_diff = attacker.status.speed - defender.status.speed
        speed_bonus = max(0, speed_diff * 2)  # 2% per point of speed advantage
        
        crit_chance = base_crit + speed_bonus
        
        # Clamp between 0% and 30%
        return max(0, min(30, crit_chance))
    
    @staticmethod
    def _can_counter_attack(defender: Unit, weapon_range: int) -> bool:
        """Determine if the defender can counter-attack."""
        # Simple rule: can counter if both units are adjacent (range 1)
        # and defender is still alive and can act
        return (weapon_range == 1 and 
                defender.hp_current > 0 and 
                defender.can_act)
    
    @staticmethod
    def position_forecast_popup(forecast: BattleForecastRenderData, cursor_x: int, cursor_y: int,
                              viewport_width: int, viewport_height: int) -> BattleForecastRenderData:
        """
        Position the forecast popup near the cursor, ensuring it stays on screen.
        
        Args:
            forecast: The forecast data to position
            cursor_x, cursor_y: Current cursor position (screen coordinates)
            viewport_width, viewport_height: Size of the viewport
            
        Returns:
            Updated forecast with proper x, y positioning
        """
        # Try to position popup to the right of cursor
        popup_x = cursor_x + 2
        popup_y = cursor_y
        
        # If it would go off the right edge, position to the left
        if popup_x + forecast.width > viewport_width:
            popup_x = max(0, cursor_x - forecast.width - 1)
        
        # If it would go off the bottom edge, move up
        if popup_y + forecast.height > viewport_height:
            popup_y = max(0, viewport_height - forecast.height)
        
        # Update forecast position
        forecast.x = popup_x
        forecast.y = popup_y
        
        return forecast