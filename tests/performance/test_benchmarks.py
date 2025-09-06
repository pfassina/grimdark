"""
Performance benchmarking tests for the grimdark game engine.

Tests performance of critical game systems including pathfinding,
combat calculations, and rendering context generation.
"""
import pytest

from src.game.map import GameMap
from src.game.combat_resolver import CombatResolver
from src.game.battle_calculator import BattleCalculator
from src.game.render_builder import RenderBuilder
from src.core.game_state import GameState
from src.core.data_structures import Vector2, VectorArray
from src.core.game_enums import Team, UnitClass
from tests.conftest import TestDataBuilder
from tests.test_utils import MapTestBuilder, MockFactory
from tests.test_constants import (
    LARGE_MAP_SIZE
)


@pytest.mark.performance
class TestPathfindingPerformance:
    """Benchmark pathfinding and movement calculations."""
    
    @pytest.fixture
    def large_map_with_units(self):
        """Create large map with many units for performance testing."""
        width, height = LARGE_MAP_SIZE
        map_builder = MapTestBuilder(width, height)
        
        # Add obstacles
        obstacles = [(i, j) for i in range(5, 15) for j in range(5, 15) if (i + j) % 3 == 0]
        
        game_map = (map_builder
                   .with_mountains(obstacles[:20])  # Limit obstacles
                   .with_forest(obstacles[20:40])
                   .build())
        
        # Add multiple units
        for i in range(10):
            unit_name = f"Unit_{i}"
            x, y = i * 2, i * 2
            if x < width and y < height:
                team = Team.PLAYER if i % 2 == 0 else Team.ENEMY
                unit_class = [UnitClass.KNIGHT, UnitClass.ARCHER, UnitClass.MAGE][i % 3]
                map_builder.with_unit(unit_name, unit_class, team, x, y)
        
        # MapTestBuilder returns the map directly, no build() method needed
        return game_map
    
    def test_movement_range_calculation_performance(self, benchmark, large_map_with_units):
        """Benchmark movement range calculation performance."""
        game_map = large_map_with_units
        
        # Get a unit for testing
        test_unit = None
        for unit in game_map.units.values():
            test_unit = unit
            break
        
        assert test_unit is not None
        
        # Benchmark movement calculation
        result = benchmark(game_map.calculate_movement_range, test_unit)
        
        assert isinstance(result, VectorArray)
        assert len(result) > 0
    
    def test_attack_range_calculation_performance(self, benchmark, large_map_with_units):
        """Benchmark attack range calculation performance."""
        game_map = large_map_with_units
        
        # Get an archer for longer range testing
        archer = None
        for unit in game_map.units.values():
            if unit.actor.unit_class == UnitClass.ARCHER:
                archer = unit
                break
        
        # If no archer, use any unit
        if archer is None:
            archer = list(game_map.units.values())[0]
        
        # Benchmark attack range calculation
        result = benchmark(game_map.calculate_attack_range, archer)
        
        assert isinstance(result, VectorArray)
    
    def test_pathfinding_performance(self, benchmark, large_map_with_units):
        """Benchmark pathfinding algorithm performance."""
        game_map = large_map_with_units
        
        # Test pathfinding if available
        if hasattr(game_map, 'find_path'):
            start = Vector2(1, 1)
            end = Vector2(15, 15)
            
            result = benchmark(game_map.find_path, start, end)
            
            # Result could be None if no path exists
            assert result is None or isinstance(result, list)
        else:
            pytest.skip("Pathfinding not implemented")
    
    def test_multiple_unit_movement_calculation(self, benchmark, large_map_with_units):
        """Benchmark calculating movement for multiple units."""
        game_map = large_map_with_units
        units = list(game_map.units.values())[:5]  # Test with 5 units
        
        def calculate_all_movement():
            results = []
            for unit in units:
                movement_range = game_map.calculate_movement_range(unit)
                results.append(movement_range)
            return results
        
        result = benchmark(calculate_all_movement)
        
        assert len(result) == len(units)
        for movement_range in result:
            assert isinstance(movement_range, VectorArray)
    
    @pytest.mark.parametrize("map_size", [(10, 10), (20, 20), (30, 30)])
    def test_movement_scaling_with_map_size(self, benchmark, map_size):
        """Test how movement calculation scales with map size."""
        width, height = map_size
        game_map = GameMap(width, height)
        
        # Add test unit in center
        center_x, center_y = width // 2, height // 2
        test_unit = TestDataBuilder.unit("Scaler", UnitClass.KNIGHT, Team.PLAYER, Vector2(center_y, center_x))
        game_map.add_unit(test_unit)
        
        # Benchmark
        result = benchmark(game_map.calculate_movement_range, test_unit)
        
        assert isinstance(result, VectorArray)


@pytest.mark.performance
class TestCombatPerformance:
    """Benchmark combat system performance."""
    
    @pytest.fixture
    def combat_scenario(self):
        """Create combat scenario for performance testing."""
        map_builder = MapTestBuilder(15, 15)
        
        # Create many units for mass combat testing
        game_map = map_builder.build()
        
        units = []
        for i in range(20):
            x, y = i % 15, i // 15
            team = Team.PLAYER if i < 10 else Team.ENEMY
            unit_class = [UnitClass.KNIGHT, UnitClass.ARCHER, UnitClass.MAGE, UnitClass.WARRIOR][i % 4]
            unit = TestDataBuilder.unit(f"Unit_{i}", unit_class, team, Vector2(y, x))
            game_map.add_unit(unit)
            units.append(unit)
        
        return game_map, units
    
    def test_single_combat_resolution_performance(self, benchmark, combat_scenario):
        """Benchmark single combat resolution."""
        game_map, units = combat_scenario
        resolver = CombatResolver(game_map)
        
        attacker = units[0]  # Player unit
        target = units[10]  # Enemy unit
        
        result = benchmark(resolver.execute_single_attack, attacker, target)
        
        assert result is not None
    
    def test_aoe_combat_performance(self, benchmark, combat_scenario):
        """Benchmark AOE combat performance."""
        game_map, units = combat_scenario
        resolver = CombatResolver(game_map)
        
        # Find a mage for AOE testing
        mage = None
        for unit in units:
            if unit.actor.unit_class == UnitClass.MAGE:
                mage = unit
                break
        
        if mage is None:
            mage = units[0]  # Use any unit
        
        center_pos = Vector2(7, 7)  # Center of unit cluster
        
        result = benchmark(resolver.execute_aoe_attack, mage, center_pos, "cross")
        
        assert result is not None
    
    def test_damage_calculation_performance(self, benchmark, combat_scenario):
        """Benchmark damage calculation performance."""
        game_map, units = combat_scenario
        calculator = BattleCalculator()
        
        attacker = units[0]
        target = units[10]
        
        # BattleCalculator has calculate_forecast method, not calculate_damage
        result = benchmark(calculator.calculate_forecast, attacker, target)
        assert result is not None
    
    def test_mass_combat_simulation(self, benchmark, combat_scenario):
        """Benchmark mass combat simulation."""
        game_map, units = combat_scenario
        resolver = CombatResolver(game_map)
        
        def simulate_mass_combat():
            results = []
            # Simulate 10 attacks
            for i in range(10):
                attacker = units[i % 10]  # Player units
                target_pos = units[10 + (i % 10)].position  # Enemy units
                target = units[10 + (i % 10)]  # Enemy unit
                result = resolver.execute_single_attack(attacker, target)
                results.append(result)
            return results
        
        results = benchmark(simulate_mass_combat)
        
        assert len(results) == 10
        for result in results:
            assert result is not None
    
    def test_combat_with_many_units_in_range(self, benchmark):
        """Benchmark combat with many units in attack range."""
        # Create dense unit placement
        game_map = GameMap(10, 10)
        
        # Place attacker in center
        attacker = TestDataBuilder.unit("Attacker", UnitClass.ARCHER, Team.PLAYER, Vector2(5, 5))
        game_map.add_unit(attacker)
        
        # Place many enemies around attacker
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx != 0 or dy != 0:  # Skip attacker position
                    x, y = 5 + dx, 5 + dy
                    if 0 <= x < 10 and 0 <= y < 10:
                        enemy = TestDataBuilder.unit(f"Enemy_{dx}_{dy}", UnitClass.WARRIOR, Team.ENEMY, Vector2(x, y))
                        # Give enemies high HP so they survive benchmark iterations
                        enemy.hp_current = 100
                        enemy.health.hp_max = 100
                        game_map.add_unit(enemy)
        
        resolver = CombatResolver(game_map)
        
        # First, test that the attack works correctly (single execution)
        test_result = resolver.execute_aoe_attack(attacker, Vector2(5, 5), "square")
        assert test_result is not None
        # Should have hit multiple targets
        assert len(test_result.targets_hit) > 1
        
        # Now benchmark the performance (result doesn't matter, just timing)
        result = benchmark(resolver.execute_aoe_attack, attacker, Vector2(5, 5), "square")


@pytest.mark.performance
class TestRenderingPerformance:
    """Benchmark rendering system performance."""
    
    @pytest.fixture
    def complex_render_scenario(self):
        """Create complex scenario for render performance testing."""
        width, height = LARGE_MAP_SIZE
        map_builder = MapTestBuilder(width, height)
        
        # Add varied terrain
        forests = [(i, j) for i in range(0, width, 3) for j in range(0, height, 3)]
        mountains = [(i, j) for i in range(1, width, 4) for j in range(1, height, 4)]
        
        game_map = (map_builder
                   .with_forest(forests[:50])
                   .with_mountains(mountains[:30])
                   .build())
        
        # Add many units
        for i in range(50):
            x, y = i % width, i // width
            if y < height:
                team = [Team.PLAYER, Team.ENEMY, Team.ALLY, Team.NEUTRAL][i % 4]
                unit_class = [UnitClass.KNIGHT, UnitClass.ARCHER, UnitClass.MAGE, UnitClass.WARRIOR, UnitClass.PRIEST][i % 5]
                unit = TestDataBuilder.unit(f"Unit_{i}", unit_class, team, Vector2(y, x))
                game_map.add_unit(unit)
        
        return game_map
    
    def test_render_context_building_performance(self, benchmark, complex_render_scenario):
        """Benchmark render context building."""
        game_map = complex_render_scenario
        game_state = GameState()
        
        mock_renderer = MockFactory.create_mock_renderer()
        render_builder = RenderBuilder(game_map, game_state, mock_renderer)
        
        result = benchmark(render_builder.build_render_context)
        
        assert result is not None
        assert hasattr(result, 'tiles')
        assert hasattr(result, 'units')
    
    def test_large_map_render_performance(self, benchmark):
        """Benchmark rendering very large maps."""
        # Create very large map
        large_map = GameMap(100, 100)
        
        # Add units across the map
        for i in range(100):
            x, y = i % 100, i // 100
            if y < 100:
                unit = TestDataBuilder.unit(f"Unit_{i}", UnitClass.KNIGHT, Team.PLAYER, Vector2(x, y))
                large_map.add_unit(unit)
        
        game_state = GameState()
        mock_renderer = MockFactory.create_mock_renderer()
        render_builder = RenderBuilder(large_map, game_state, mock_renderer)
        
        result = benchmark(render_builder.build_render_context)
        
        assert result is not None
    
    def test_render_context_with_combat_data(self, benchmark):
        """Benchmark render context building with combat data."""
        game_map, player, enemy = self._create_combat_render_scenario()
        game_state = GameState()
        
        # Setup combat state
        from src.game.combat_manager import CombatManager
        combat_manager = CombatManager(game_map, game_state)
        if player is not None:
            combat_manager.setup_attack_targeting(player)
        
        mock_renderer = MockFactory.create_mock_renderer()
        render_builder = RenderBuilder(game_map, game_state, mock_renderer)
        
        result = benchmark(render_builder.build_render_context)
        
        assert result is not None
    
    def _create_combat_render_scenario(self):
        """Helper to create combat rendering scenario."""
        map_builder = MapTestBuilder(8, 8)
        game_map = (map_builder
                   .with_player_knight("Player", 3, 3)
                   .with_enemy_warrior("Enemy", 5, 5)
                   .build())
        
        player = game_map.get_unit_at(Vector2(3, 3))
        enemy = game_map.get_unit_at(Vector2(5, 5))
        
        return game_map, player, enemy
    
    @pytest.mark.parametrize("unit_count", [10, 50, 100])
    def test_render_scaling_with_unit_count(self, benchmark, unit_count):
        """Test render performance scaling with unit count."""
        game_map = GameMap(20, 20)
        
        # Add specified number of units
        for i in range(unit_count):
            x, y = i % 20, i // 20
            if y < 20:
                unit = TestDataBuilder.unit(f"Unit_{i}", UnitClass.WARRIOR, Team.PLAYER, Vector2(y, x))
                game_map.add_unit(unit)
        
        game_state = GameState()
        mock_renderer = MockFactory.create_mock_renderer()
        render_builder = RenderBuilder(game_map, game_state, mock_renderer)
        
        result = benchmark(render_builder.build_render_context)
        
        assert result is not None
        assert len(result.units) == unit_count


@pytest.mark.performance
class TestDataStructurePerformance:
    """Benchmark core data structure performance."""
    
    def test_vector_array_operations_performance(self, benchmark):
        """Benchmark VectorArray operations."""
        # Create large vector array
        vectors = [Vector2(i, j) for i in range(50) for j in range(50)]
        
        def vector_array_operations():
            # Create VectorArray from list - this is the correct API
            arr = VectorArray(vectors)
            
            # Test contains operations
            test_vectors = vectors[:100]
            results = []
            for test_vec in test_vectors:
                results.append(arr.contains(test_vec))
            
            return arr, results
        
        arr, results = benchmark(vector_array_operations)
        
        assert len(arr) == len(vectors)
        assert len(results) == 100
    
    def test_vector2_distance_calculations(self, benchmark):
        """Benchmark Vector2 distance calculations."""
        vectors = [Vector2(i, j) for i in range(100) for j in range(100)]
        
        def distance_calculations():
            distances = []
            base_vector = Vector2(50, 50)
            
            for vector in vectors:
                distance = base_vector.distance_to(vector)
                distances.append(distance)
            
            return distances
        
        distances = benchmark(distance_calculations)
        
        assert len(distances) == len(vectors)
        assert all(d >= 0 for d in distances)
    
    def test_map_position_validation_performance(self, benchmark):
        """Benchmark map position validation."""
        game_map = GameMap(50, 50)
        
        # Generate many positions to test
        positions = [Vector2(i, j) for i in range(-10, 60) for j in range(-10, 60)]
        
        def validate_positions():
            results = []
            for pos in positions:
                valid = game_map.is_valid_position(pos)
                results.append(valid)
            return results
        
        results = benchmark(validate_positions)
        
        assert len(results) == len(positions)
        assert isinstance(results[0], bool)


@pytest.mark.performance
class TestPerformanceRegression:
    """Performance regression detection tests."""
    
    def test_basic_game_operations_baseline(self, benchmark):
        """Establish baseline for basic game operations."""
        # Create standard test scenario
        game_map = GameMap(10, 10)
        unit = TestDataBuilder.unit("Baseline", UnitClass.KNIGHT, Team.PLAYER, Vector2(5, 5))
        game_map.add_unit(unit)
        
        def basic_operations():
            # Movement calculation
            movement = game_map.calculate_movement_range(unit)
            
            # Attack calculation
            attack = game_map.calculate_attack_range(unit)
            
            # Position checks
            valid_positions = 0
            for x in range(10):
                for y in range(10):
                    if game_map.is_valid_position(Vector2(x, y)):
                        valid_positions += 1
            
            return len(movement), len(attack), valid_positions
        
        movement_count, attack_count, valid_count = benchmark(basic_operations)
        
        # Baseline assertions
        assert movement_count > 0
        assert attack_count > 0
        assert valid_count == 100  # 10x10 map
    
    def test_combat_resolution_baseline(self, benchmark):
        """Establish baseline for combat resolution."""
        game_map, player, enemy = self._create_standard_combat()
        resolver = CombatResolver(game_map)
        
        def combat_baseline():
            results = []
            for _ in range(5):  # 5 attacks
                result = resolver.execute_single_attack(player, enemy)
                results.append(result)
            return results
        
        results = benchmark(combat_baseline)
        
        assert len(results) == 5
        for result in results:
            assert result is not None
    
    def _create_standard_combat(self):
        """Create standard combat scenario for baselines."""
        game_map = GameMap(5, 5)
        player = TestDataBuilder.unit("Player", UnitClass.KNIGHT, Team.PLAYER, Vector2(1, 1))
        enemy = TestDataBuilder.unit("Enemy", UnitClass.WARRIOR, Team.ENEMY, Vector2(1, 2))
        
        game_map.add_unit(player)
        game_map.add_unit(enemy)
        
        return game_map, player, enemy
    
    @pytest.mark.slow
    def test_stress_test_performance(self, benchmark):
        """Stress test for performance under load."""
        # Create large scenario
        game_map = GameMap(50, 50)
        
        # Add many units
        for i in range(200):
            x, y = i % 50, i // 50
            if y < 50:
                unit = TestDataBuilder.unit(f"Stress_{i}", UnitClass.WARRIOR, Team.PLAYER, Vector2(x, y))
                game_map.add_unit(unit)
        
        def stress_operations():
            results = []
            
            # Test 20 units
            test_units = [unit for unit in game_map.units if unit is not None][:20]
            
            for unit in test_units:
                movement = game_map.calculate_movement_range(unit)
                attack = game_map.calculate_attack_range(unit)
                results.append((len(movement), len(attack)))
            
            return results
        
        results = benchmark(stress_operations)
        
        assert len(results) == 20
        for movement_count, attack_count in results:
            assert movement_count >= 0
            assert attack_count >= 0