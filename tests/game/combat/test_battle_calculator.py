"""
Unit tests for the BattleCalculator system.

Tests damage prediction, critical hit calculation, counter-attack detection,
and battle forecast generation for the UI system.
"""

from unittest.mock import Mock, patch

from src.game.combat import BattleCalculator
from src.core.entities.renderable import BattleForecastRenderData


class MockActor:
    """Mock actor component for testing."""
    
    def __init__(self, unit_class_name="Knight"):
        self.unit_class_name = unit_class_name
        
    def get_class_name(self):
        return self.unit_class_name


class MockUnit:
    """Mock unit for testing battle calculator."""
    
    def __init__(self, strength=10, defense=2, speed=5, hp_current=25, can_act=True, unit_class_name="Knight"):
        # Mock components
        self.combat = Mock()
        self.combat.strength = strength
        self.combat.defense = defense
        
        self.status = Mock()
        self.status.speed = speed
        
        self.actor = MockActor(unit_class_name)
        
        # Basic properties
        self.hp_current = hp_current
        self.can_act = can_act


class TestDamageCalculation:
    """Test damage calculation methods."""
    
    def test_calculate_average_damage_basic(self):
        """Test basic average damage calculation."""
        attacker = MockUnit(strength=15, defense=0)
        defender = MockUnit(strength=0, defense=4)  # defense = 4, so defense//2 = 2
        
        damage = BattleCalculator._calculate_average_damage(attacker, defender)  # type: ignore[arg-type]
        
        # Expected: 15 - 4//2 = 15 - 2 = 13
        assert damage == 13
        
    def test_calculate_average_damage_minimum(self):
        """Test that average damage has minimum of 1."""
        weak_attacker = MockUnit(strength=1, defense=0)
        heavily_armored = MockUnit(strength=0, defense=20)  # defense//2 = 10
        
        damage = BattleCalculator._calculate_average_damage(weak_attacker, heavily_armored)  # type: ignore[arg-type]
        
        # Expected: max(1, 1 - 10) = 1
        assert damage == 1
        
    def test_calculate_damage_range_basic(self):
        """Test damage range calculation."""
        attacker = MockUnit(strength=20, defense=0)
        defender = MockUnit(strength=0, defense=6)  # defense//2 = 3
        
        min_damage, max_damage = BattleCalculator._calculate_damage_range(attacker, defender)  # type: ignore[arg-type]
        
        # Base damage: 20 - 3 = 17
        # Variance: 17//4 = 4 (25% variance)
        # Range: 17-4 to 17+4 = 13 to 21
        # But min clamped to 1: max(1, 13) = 13
        assert min_damage == 13
        assert max_damage == 21
        
    def test_calculate_damage_range_minimum_base(self):
        """Test damage range with very low base damage."""
        weak_attacker = MockUnit(strength=2, defense=0)
        armored_defender = MockUnit(strength=0, defense=10)  # defense//2 = 5
        
        min_damage, max_damage = BattleCalculator._calculate_damage_range(weak_attacker, armored_defender)  # type: ignore[arg-type]
        
        # Base damage: max(1, 2 - 5) = 1
        # Variance: max(1, 1//4) = max(1, 0) = 1
        # Range: 1-1 to 1+1 = 0 to 2
        # Min clamped: max(1, 0) = 1
        assert min_damage == 1
        assert max_damage == 2
        
    @patch('random.randint')
    def test_calculate_damage_with_variance(self, mock_randint):
        """Test damage calculation with variance."""
        mock_randint.return_value = 2  # Fixed variance for testing
        
        attacker = MockUnit(strength=12, defense=0)
        defender = MockUnit(strength=0, defense=4)  # defense//2 = 2
        
        damage = BattleCalculator._calculate_damage(attacker, defender)  # type: ignore[arg-type]
        
        # Base damage: 12 - 2 = 10
        # Variance range: 10//4 = 2
        # With variance +2: 10 + 2 = 12
        assert damage == 12
        
        # Verify randint was called with correct range
        mock_randint.assert_called_once_with(-2, 2)
        
    @patch('random.randint')
    def test_calculate_damage_variance_minimum(self, mock_randint):
        """Test damage calculation maintains minimum of 1 even with negative variance."""
        mock_randint.return_value = -3  # Large negative variance
        
        attacker = MockUnit(strength=5, defense=0)
        defender = MockUnit(strength=0, defense=6)  # defense//2 = 3
        
        damage = BattleCalculator._calculate_damage(attacker, defender)  # type: ignore[arg-type]
        
        # Base damage: max(1, 5 - 3) = 2
        # With large negative variance: max(1, 2 - 3) = 1
        assert damage == 1


class TestCriticalHitCalculation:
    """Test critical hit chance calculations."""
    
    def test_calculate_crit_chance_base(self):
        """Test base critical hit chance."""
        attacker = MockUnit(speed=10)
        defender = MockUnit(speed=10)  # Same speed
        
        crit_chance = BattleCalculator._calculate_crit_chance(attacker, defender)  # type: ignore[arg-type]
        
        # Expected: 5% base crit (no speed advantage)
        assert crit_chance == 5
        
    def test_calculate_crit_chance_speed_advantage(self):
        """Test critical hit chance with speed advantage."""
        fast_attacker = MockUnit(speed=15)
        slow_defender = MockUnit(speed=10)  # 5 speed difference
        
        crit_chance = BattleCalculator._calculate_crit_chance(fast_attacker, slow_defender)  # type: ignore[arg-type]
        
        # Expected: 5% base + (5 * 2%) = 15%
        assert crit_chance == 15
        
    def test_calculate_crit_chance_speed_disadvantage(self):
        """Test critical hit chance with speed disadvantage."""
        slow_attacker = MockUnit(speed=8)
        fast_defender = MockUnit(speed=12)  # -4 speed difference
        
        crit_chance = BattleCalculator._calculate_crit_chance(slow_attacker, fast_defender)  # type: ignore[arg-type]
        
        # Expected: 5% base + max(0, -4 * 2%) = 5% (no negative crit)
        assert crit_chance == 5
        
    def test_calculate_crit_chance_maximum_cap(self):
        """Test that critical hit chance is capped at 30%."""
        very_fast_attacker = MockUnit(speed=30)
        very_slow_defender = MockUnit(speed=5)  # 25 speed difference
        
        crit_chance = BattleCalculator._calculate_crit_chance(very_fast_attacker, very_slow_defender)  # type: ignore[arg-type]
        
        # Expected: 5% base + (25 * 2%) = 55%, but capped at 30%
        assert crit_chance == 30
        
    def test_calculate_crit_chance_zero_minimum(self):
        """Test that critical hit chance doesn't go below 0%."""
        # This test is somewhat redundant since we never subtract from base crit,
        # but ensures the max(0, ...) logic works correctly
        attacker = MockUnit(speed=5)
        defender = MockUnit(speed=20)  # Large speed disadvantage
        
        crit_chance = BattleCalculator._calculate_crit_chance(attacker, defender)  # type: ignore[arg-type]
        
        # Expected: 5% base + max(0, -15 * 2%) = 5%
        assert crit_chance == 5


class TestCounterAttackDetection:
    """Test counter-attack possibility detection."""
    
    def test_can_counter_attack_valid(self):
        """Test valid counter-attack scenario."""
        defender = MockUnit(hp_current=15, can_act=True)
        weapon_range = 1  # Adjacent attack
        
        can_counter = BattleCalculator._can_counter_attack(defender, weapon_range)  # type: ignore[arg-type]
        
        assert can_counter
        
    def test_can_counter_attack_out_of_range(self):
        """Test counter-attack with ranged weapon."""
        defender = MockUnit(hp_current=15, can_act=True)
        weapon_range = 2  # Ranged attack
        
        can_counter = BattleCalculator._can_counter_attack(defender, weapon_range)  # type: ignore[arg-type]
        
        assert not can_counter
        
    def test_can_counter_attack_dead_defender(self):
        """Test counter-attack with dead defender."""
        dead_defender = MockUnit(hp_current=0, can_act=True)
        weapon_range = 1
        
        can_counter = BattleCalculator._can_counter_attack(dead_defender, weapon_range)  # type: ignore[arg-type]
        
        assert not can_counter
        
    def test_can_counter_attack_cannot_act(self):
        """Test counter-attack when defender cannot act."""
        stunned_defender = MockUnit(hp_current=15, can_act=False)
        weapon_range = 1
        
        can_counter = BattleCalculator._can_counter_attack(stunned_defender, weapon_range)  # type: ignore[arg-type]
        
        assert not can_counter
        
    def test_can_counter_attack_multiple_conditions(self):
        """Test counter-attack with multiple failing conditions."""
        dead_stunned_defender = MockUnit(hp_current=0, can_act=False)
        weapon_range = 2  # Also ranged
        
        can_counter = BattleCalculator._can_counter_attack(dead_stunned_defender, weapon_range)  # type: ignore[arg-type]
        
        assert not can_counter


class TestBattleForecast:
    """Test complete battle forecast generation."""
    
    def test_calculate_forecast_basic(self):
        """Test basic battle forecast calculation."""
        attacker = MockUnit(strength=12, defense=2, speed=10, unit_class_name="Knight")
        defender = MockUnit(strength=8, defense=4, speed=8, can_act=True, unit_class_name="Orc")
        
        forecast = BattleCalculator.calculate_forecast(attacker, defender, weapon_range=1)  # type: ignore[arg-type]
        
        assert isinstance(forecast, BattleForecastRenderData)
        assert forecast.attacker_name == "Knight"
        assert forecast.defender_name == "Orc"
        assert forecast.hit_chance == 100  # All attacks hit
        assert forecast.damage > 0  # Should deal some damage
        assert forecast.can_counter  # Adjacent attack, defender can act
        assert forecast.counter_damage > 0  # Defender can hit back
        
    def test_calculate_forecast_no_counter(self):
        """Test battle forecast with no counter-attack."""
        attacker = MockUnit(strength=15, defense=2, speed=12, unit_class_name="Archer")
        defender = MockUnit(strength=10, defense=3, speed=6, can_act=True, unit_class_name="Soldier")
        
        forecast = BattleCalculator.calculate_forecast(attacker, defender, weapon_range=2)  # type: ignore[arg-type]
        
        assert not forecast.can_counter  # Ranged attack
        assert forecast.counter_damage == 0
        assert forecast.counter_min_damage == 0
        assert forecast.counter_max_damage == 0
        
    def test_calculate_forecast_damage_ranges(self):
        """Test that forecast includes proper damage ranges."""
        attacker = MockUnit(strength=20, defense=0, speed=15, unit_class_name="Mage")
        defender = MockUnit(strength=12, defense=8, speed=10, can_act=True, unit_class_name="Guard")
        
        forecast = BattleCalculator.calculate_forecast(attacker, defender, weapon_range=1)  # type: ignore[arg-type]
        
        # Verify damage range is logical
        assert forecast.min_damage <= forecast.damage <= forecast.max_damage
        assert forecast.min_damage >= 1  # Minimum damage
        assert forecast.max_damage > forecast.min_damage  # Should have variance
        
        # Verify counter-attack damage range if applicable
        if forecast.can_counter:
            assert forecast.counter_min_damage <= forecast.counter_damage <= forecast.counter_max_damage
            assert forecast.counter_min_damage >= 1
            
    def test_calculate_forecast_crit_chance(self):
        """Test that forecast includes critical hit calculations."""
        fast_attacker = MockUnit(strength=10, speed=20, unit_class_name="Rogue")
        slow_defender = MockUnit(strength=10, speed=5, can_act=True, unit_class_name="Tank")
        
        forecast = BattleCalculator.calculate_forecast(fast_attacker, slow_defender)  # type: ignore[arg-type]
        
        # Fast attacker should have higher crit chance
        assert forecast.crit_chance > 5  # More than base crit
        assert forecast.crit_chance <= 30  # But capped at maximum
        
    def test_calculate_forecast_weak_vs_strong(self):
        """Test forecast with very weak attacker vs strong defender."""
        weak_attacker = MockUnit(strength=3, defense=1, speed=5, unit_class_name="Peasant")
        strong_defender = MockUnit(strength=18, defense=12, speed=8, can_act=True, unit_class_name="Champion")
        
        forecast = BattleCalculator.calculate_forecast(weak_attacker, strong_defender)  # type: ignore[arg-type]
        
        # Weak attacker should still deal minimum damage
        assert forecast.damage >= 1
        assert forecast.min_damage == 1
        
        # Strong defender should deal significant counter damage
        if forecast.can_counter:
            assert forecast.counter_damage > forecast.damage


class TestForecastPositioning:
    """Test forecast popup positioning logic."""
    
    def test_position_forecast_popup_basic(self):
        """Test basic popup positioning to the right of cursor."""
        forecast = BattleForecastRenderData(
            x=0, y=0,
            attacker_name="Knight", defender_name="Orc",
            damage=10, hit_chance=100, crit_chance=5,
            can_counter=True, counter_damage=8,
            min_damage=8, max_damage=12,
            counter_min_damage=6, counter_max_damage=10
        )
        forecast.width = 20
        forecast.height = 8
        
        positioned = BattleCalculator.position_forecast_popup(
            forecast, cursor_x=10, cursor_y=5, viewport_width=80, viewport_height=24
        )
        
        # Should position to the right of cursor
        assert positioned.x == 12  # cursor_x + 2
        assert positioned.y == 5   # cursor_y
        
    def test_position_forecast_popup_right_edge(self):
        """Test popup positioning when it would go off the right edge."""
        forecast = BattleForecastRenderData(
            x=0, y=0,
            attacker_name="Knight", defender_name="Orc",
            damage=10, hit_chance=100, crit_chance=5,
            can_counter=True, counter_damage=8,
            min_damage=8, max_damage=12,
            counter_min_damage=6, counter_max_damage=10
        )
        forecast.width = 25
        forecast.height = 8
        
        positioned = BattleCalculator.position_forecast_popup(
            forecast, cursor_x=70, cursor_y=10, viewport_width=80, viewport_height=24
        )
        
        # Should position to the left of cursor
        # cursor_x - width - 1 = 70 - 25 - 1 = 44
        assert positioned.x == 44
        assert positioned.y == 10
        
    def test_position_forecast_popup_bottom_edge(self):
        """Test popup positioning when it would go off the bottom edge."""
        forecast = BattleForecastRenderData(
            x=0, y=0,
            attacker_name="Knight", defender_name="Orc",
            damage=10, hit_chance=100, crit_chance=5,
            can_counter=True, counter_damage=8,
            min_damage=8, max_damage=12,
            counter_min_damage=6, counter_max_damage=10
        )
        forecast.width = 20
        forecast.height = 10
        
        positioned = BattleCalculator.position_forecast_popup(
            forecast, cursor_x=30, cursor_y=20, viewport_width=80, viewport_height=24
        )
        
        # Should move up to fit on screen
        # viewport_height - height = 24 - 10 = 14
        assert positioned.x == 32  # cursor_x + 2 (fits horizontally)
        assert positioned.y == 14  # Moved up to fit
        
    def test_position_forecast_popup_corner_case(self):
        """Test popup positioning at screen corner."""
        forecast = BattleForecastRenderData(
            x=0, y=0,
            attacker_name="Knight", defender_name="Orc",
            damage=10, hit_chance=100, crit_chance=5,
            can_counter=True, counter_damage=8,
            min_damage=8, max_damage=12,
            counter_min_damage=6, counter_max_damage=10
        )
        forecast.width = 30
        forecast.height = 12
        
        positioned = BattleCalculator.position_forecast_popup(
            forecast, cursor_x=75, cursor_y=20, viewport_width=80, viewport_height=24
        )
        
        # Should handle both horizontal and vertical constraints
        # Horizontal: max(0, 75 - 30 - 1) = 44
        # Vertical: max(0, 24 - 12) = 12
        assert positioned.x == 44
        assert positioned.y == 12
        
    def test_position_forecast_popup_zero_minimum(self):
        """Test that popup positioning doesn't go below 0,0."""
        forecast = BattleForecastRenderData(
            x=0, y=0,
            attacker_name="Knight", defender_name="Orc",
            damage=10, hit_chance=100, crit_chance=5,
            can_counter=True, counter_damage=8,
            min_damage=8, max_damage=12,
            counter_min_damage=6, counter_max_damage=10
        )
        forecast.width = 50  # Very wide
        forecast.height = 30  # Very tall
        
        positioned = BattleCalculator.position_forecast_popup(
            forecast, cursor_x=5, cursor_y=5, viewport_width=40, viewport_height=20
        )
        
        # Should clamp to 0,0 minimum
        assert positioned.x >= 0
        assert positioned.y >= 0


class TestBattleCalculatorEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_strength_attacker(self):
        """Test calculations with zero strength attacker."""
        zero_str_attacker = MockUnit(strength=0, defense=0, speed=5)
        defender = MockUnit(strength=10, defense=0, speed=5)
        
        forecast = BattleCalculator.calculate_forecast(zero_str_attacker, defender)  # type: ignore[arg-type]
        
        # Should still deal minimum damage
        assert forecast.damage == 1
        assert forecast.min_damage == 1
        
    def test_massive_defense_defender(self):
        """Test calculations with extremely high defense."""
        attacker = MockUnit(strength=10, defense=0, speed=5)
        tank_defender = MockUnit(strength=5, defense=100, speed=5)  # defense//2 = 50
        
        forecast = BattleCalculator.calculate_forecast(attacker, tank_defender)  # type: ignore[arg-type]
        
        # Should still deal minimum damage
        assert forecast.damage == 1
        assert forecast.min_damage == 1
        
    def test_extreme_speed_differences(self):
        """Test calculations with extreme speed differences."""
        sonic_attacker = MockUnit(strength=10, defense=0, speed=100)
        statue_defender = MockUnit(strength=10, defense=0, speed=1)
        
        forecast = BattleCalculator.calculate_forecast(sonic_attacker, statue_defender)  # type: ignore[arg-type]
        
        # Crit chance should be capped at 30%
        assert forecast.crit_chance == 30
        
    def test_forecast_render_data_integrity(self):
        """Test that forecast data structure is properly populated."""
        attacker = MockUnit(strength=15, defense=3, speed=12, unit_class_name="Paladin")
        defender = MockUnit(strength=12, defense=5, speed=8, can_act=True, unit_class_name="Bandit")
        
        forecast = BattleCalculator.calculate_forecast(attacker, defender, weapon_range=1)  # type: ignore[arg-type]
        
        # Verify all fields are populated
        assert forecast.attacker_name is not None
        assert forecast.defender_name is not None
        assert isinstance(forecast.damage, int)
        assert isinstance(forecast.hit_chance, int)
        assert isinstance(forecast.crit_chance, int)
        assert isinstance(forecast.can_counter, bool)
        assert isinstance(forecast.counter_damage, int)
        assert isinstance(forecast.min_damage, int)
        assert isinstance(forecast.max_damage, int)
        assert isinstance(forecast.counter_min_damage, int)
        assert isinstance(forecast.counter_max_damage, int)
        
        # Verify logical relationships
        assert forecast.hit_chance == 100  # All attacks hit
        assert forecast.min_damage <= forecast.max_damage
        if forecast.can_counter:
            assert forecast.counter_min_damage <= forecast.counter_max_damage
        else:
            assert forecast.counter_damage == 0
            assert forecast.counter_min_damage == 0
            assert forecast.counter_max_damage == 0