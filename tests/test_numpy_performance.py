#!/usr/bin/env python3
"""
Performance benchmark tests for numpy vectorization improvements.

This test suite compares the performance of original implementations vs 
numpy-vectorized implementations across key game systems.
"""

import time
import numpy as np
from typing import List
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.data_structures import Vector2, VectorArray
from src.core.game_enums import TerrainType, UnitClass, Team
from src.game.map import GameMap
from src.game.unit import Unit


class PerformanceBenchmark:
    """Performance benchmark suite for numpy vectorization improvements."""
    
    def __init__(self):
        """Initialize benchmark with test data."""
        # Create a medium-sized map for testing
        self.map_size = 50
        self.game_map = GameMap(self.map_size, self.map_size)
        
        # Add some varied terrain for realistic testing
        self._setup_test_terrain()
        
        # Create test units
        self._setup_test_units()
        
        # Test data for vector operations
        self.test_vectors = [Vector2(i % 10, i // 10) for i in range(100)]
    
    def _setup_test_terrain(self):
        """Setup varied terrain types for realistic testing."""
        # Add some obstacles and varied terrain
        for y in range(self.map_size):
            for x in range(self.map_size):
                pos = Vector2(y, x)
                if (x + y) % 7 == 0:
                    self.game_map.set_tile(pos, TerrainType.MOUNTAIN)
                elif (x * y) % 11 == 0:
                    self.game_map.set_tile(pos, TerrainType.FOREST)
                elif x % 13 == 0:
                    self.game_map.set_tile(pos, TerrainType.WATER)
                else:
                    self.game_map.set_tile(pos, TerrainType.PLAIN)
    
    def _setup_test_units(self):
        """Setup test units for benchmarking."""
        # Create a few test units with different stats
        self.test_units = []
        for i in range(5):
            unit = Unit(
                f"TestUnit{i}",
                UnitClass.KNIGHT,
                Team.PLAYER,
                Vector2(5 + i, 5 + i)
            )
            self.game_map.add_unit(unit)
            self.test_units.append(unit)
    
    def time_function(self, func, *args, **kwargs):
        """Time a function execution and return elapsed time in milliseconds."""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return (end_time - start_time) * 1000, result  # Convert to milliseconds
    
    def benchmark_vector_operations(self) -> dict:
        """Benchmark Vector2 vs VectorArray operations."""
        results = {}
        
        # Test batch distance calculations
        positions1 = self.test_vectors[:50]
        positions2 = self.test_vectors[50:]
        target = Vector2(25, 25)
        
        # Original individual calculations
        def original_distances():
            return [pos.distance_to(target) for pos in positions1]
        
        # Vectorized batch calculations
        def vectorized_distances():
            vec_array = VectorArray(positions1)
            return vec_array.distance_to_point(target)
        
        orig_time, orig_result = self.time_function(original_distances)
        vect_time, vect_result = self.time_function(vectorized_distances)
        
        results['vector_distance_original_ms'] = orig_time
        results['vector_distance_vectorized_ms'] = vect_time
        results['vector_distance_speedup'] = orig_time / vect_time if vect_time > 0 else float('inf')
        
        # Test Manhattan distance calculations
        def original_manhattan():
            return [pos.manhattan_distance_to(target) for pos in positions1]
        
        def vectorized_manhattan():
            vec_array = VectorArray(positions1)
            return vec_array.manhattan_distance_to_point(target)
        
        orig_time, _ = self.time_function(original_manhattan)
        vect_time, _ = self.time_function(vectorized_manhattan)
        
        results['manhattan_distance_original_ms'] = orig_time
        results['manhattan_distance_vectorized_ms'] = vect_time
        results['manhattan_distance_speedup'] = orig_time / vect_time if vect_time > 0 else float('inf')
        
        return results
    
    def benchmark_movement_range(self) -> dict:
        """Benchmark movement range calculations."""
        results = {}
        unit = self.test_units[0]
        
        # We can't easily compare original vs vectorized since we replaced the original
        # Instead, we'll benchmark the vectorized version and compare with a simple baseline
        
        def simple_movement_range():
            """Simple baseline: just return positions within Manhattan distance."""
            movement = unit.movement.movement_points
            center = unit.position
            positions = []
            for dy in range(-movement, movement + 1):
                for dx in range(-movement, movement + 1):
                    if abs(dx) + abs(dy) <= movement:
                        pos = Vector2(center.y + dy, center.x + dx)
                        if self.game_map.is_valid_position(pos):
                            positions.append(pos)
            return set(positions)
        
        def vectorized_movement_range():
            return list(self.game_map.calculate_movement_range(unit))
        
        simple_time, simple_result = self.time_function(simple_movement_range)
        vect_time, vect_result = self.time_function(vectorized_movement_range)
        
        results['movement_simple_ms'] = simple_time
        results['movement_vectorized_ms'] = vect_time
        results['movement_range_accuracy'] = len(vect_result) / len(simple_result) if simple_result else 0
        
        return results
    
    def benchmark_attack_range(self) -> dict:
        """Benchmark attack range calculations."""
        results = {}
        unit = self.test_units[0]
        
        # Original nested loop implementation (recreated for comparison)
        def original_attack_range():
            min_range = unit.combat.attack_range_min
            max_range = unit.combat.attack_range_max
            pos = unit.position
            attack_range = set()
            
            for dy in range(-max_range, max_range + 1):
                for dx in range(-max_range, max_range + 1):
                    distance = abs(dx) + abs(dy)
                    if min_range <= distance <= max_range:
                        target_pos = Vector2(pos.y + dy, pos.x + dx)
                        if self.game_map.is_valid_position(target_pos):
                            attack_range.add(target_pos)
            return attack_range
        
        def vectorized_attack_range():
            return list(self.game_map.calculate_attack_range(unit))
        
        orig_time, orig_result = self.time_function(original_attack_range)
        vect_time, vect_result = self.time_function(vectorized_attack_range)
        
        results['attack_range_original_ms'] = orig_time
        results['attack_range_vectorized_ms'] = vect_time
        results['attack_range_speedup'] = orig_time / vect_time if vect_time > 0 else float('inf')
        results['attack_range_accuracy'] = len(vect_result) == len(orig_result)
        
        return results
    
    def benchmark_aoe_patterns(self) -> dict:
        """Benchmark AOE pattern generation."""
        results = {}
        center = Vector2(25, 25)
        
        # Original cross pattern implementation (recreated)
        def original_cross_pattern():
            candidates = [
                center,
                Vector2(center.y, center.x + 1),
                Vector2(center.y, center.x - 1),
                Vector2(center.y + 1, center.x),
                Vector2(center.y - 1, center.x),
            ]
            tiles = []
            for pos in candidates:
                if self.game_map.is_valid_position(pos):
                    tiles.append(pos)
            return tiles
        
        def vectorized_cross_pattern():
            return list(self.game_map.calculate_aoe_tiles(center, "cross"))
        
        orig_time, orig_result = self.time_function(original_cross_pattern)
        vect_time, vect_result = self.time_function(vectorized_cross_pattern)
        
        results['aoe_cross_original_ms'] = orig_time
        results['aoe_cross_vectorized_ms'] = vect_time
        results['aoe_cross_speedup'] = orig_time / vect_time if vect_time > 0 else float('inf')
        results['aoe_cross_accuracy'] = len(orig_result) == len(vect_result)
        
        return results
    
    def benchmark_terrain_queries(self) -> dict:
        """Benchmark terrain-based queries."""
        results = {}
        
        # Original approach: loop through all tiles
        def original_find_terrain():
            positions = []
            for y in range(self.game_map.height):
                for x in range(self.game_map.width):
                    pos = Vector2(y, x)
                    tile = self.game_map.get_tile(pos)
                    if tile and tile.terrain_type == TerrainType.FOREST:
                        positions.append(pos)
            return positions
        
        def vectorized_find_terrain():
            return list(self.game_map.find_terrain_positions(TerrainType.FOREST))
        
        orig_time, orig_result = self.time_function(original_find_terrain)
        vect_time, vect_result = self.time_function(vectorized_find_terrain)
        
        results['terrain_query_original_ms'] = orig_time
        results['terrain_query_vectorized_ms'] = vect_time
        results['terrain_query_speedup'] = orig_time / vect_time if vect_time > 0 else float('inf')
        results['terrain_query_accuracy'] = len(orig_result) == len(vect_result)
        
        return results
    
    def run_full_benchmark(self) -> dict:
        """Run all benchmarks and return comprehensive results."""
        print("Running numpy vectorization performance benchmarks...")
        
        all_results = {}
        
        print("  - Vector operations...")
        all_results.update(self.benchmark_vector_operations())
        
        print("  - Movement range calculations...")
        all_results.update(self.benchmark_movement_range())
        
        print("  - Attack range calculations...")
        all_results.update(self.benchmark_attack_range())
        
        print("  - AOE pattern generation...")
        all_results.update(self.benchmark_aoe_patterns())
        
        print("  - Terrain queries...")
        all_results.update(self.benchmark_terrain_queries())
        
        return all_results
    
    def print_results(self, results: dict):
        """Print benchmark results in a readable format."""
        print("\n" + "="*60)
        print("NUMPY VECTORIZATION PERFORMANCE BENCHMARK RESULTS")
        print("="*60)
        
        print(f"\n📊 Vector Operations:")
        print(f"  Distance calculations:")
        print(f"    Original: {results['vector_distance_original_ms']:.2f}ms")
        print(f"    Vectorized: {results['vector_distance_vectorized_ms']:.2f}ms")
        print(f"    Speedup: {results['vector_distance_speedup']:.1f}x")
        
        print(f"  Manhattan distance calculations:")
        print(f"    Original: {results['manhattan_distance_original_ms']:.2f}ms")
        print(f"    Vectorized: {results['manhattan_distance_vectorized_ms']:.2f}ms")
        print(f"    Speedup: {results['manhattan_distance_speedup']:.1f}x")
        
        print(f"\n🎯 Attack Range Calculations:")
        print(f"  Original: {results['attack_range_original_ms']:.2f}ms")
        print(f"  Vectorized: {results['attack_range_vectorized_ms']:.2f}ms")
        print(f"  Speedup: {results['attack_range_speedup']:.1f}x")
        print(f"  Accuracy: {'✓' if results['attack_range_accuracy'] else '✗'}")
        
        print(f"\n💥 AOE Pattern Generation:")
        print(f"  Cross pattern:")
        print(f"    Original: {results['aoe_cross_original_ms']:.2f}ms")
        print(f"    Vectorized: {results['aoe_cross_vectorized_ms']:.2f}ms")
        print(f"    Speedup: {results['aoe_cross_speedup']:.1f}x")
        print(f"    Accuracy: {'✓' if results['aoe_cross_accuracy'] else '✗'}")
        
        print(f"\n🌲 Terrain Queries:")
        print(f"  Find terrain positions:")
        print(f"    Original: {results['terrain_query_original_ms']:.2f}ms")
        print(f"    Vectorized: {results['terrain_query_vectorized_ms']:.2f}ms")
        print(f"    Speedup: {results['terrain_query_speedup']:.1f}x")
        print(f"    Accuracy: {'✓' if results['terrain_query_accuracy'] else '✗'}")
        
        print(f"\n🚀 Movement Range:")
        print(f"  Simple baseline: {results['movement_simple_ms']:.2f}ms")
        print(f"  Vectorized (with pathfinding): {results['movement_vectorized_ms']:.2f}ms")
        print(f"  Range accuracy: {results['movement_range_accuracy']:.1%}")
        
        # Calculate overall performance improvement
        speedups = [
            results['vector_distance_speedup'],
            results['manhattan_distance_speedup'],
            results['attack_range_speedup'],
            results['aoe_cross_speedup'],
            results['terrain_query_speedup']
        ]
        avg_speedup = np.mean([s for s in speedups if s != float('inf')])
        
        print(f"\n🎉 OVERALL RESULTS:")
        print(f"  Average speedup: {avg_speedup:.1f}x")
        print(f"  Map size tested: {self.map_size}x{self.map_size}")
        accuracy_passed = all([
            results['attack_range_accuracy'],
            results['aoe_cross_accuracy'], 
            results['terrain_query_accuracy']
        ])
        print(f"  All accuracy checks: {'PASSED' if accuracy_passed else 'FAILED'}")


def main():
    """Run the benchmark suite."""
    try:
        benchmark = PerformanceBenchmark()
        results = benchmark.run_full_benchmark()
        benchmark.print_results(results)
        
        print(f"\nBenchmark completed successfully! ✅")
        
    except Exception as e:
        print(f"Benchmark failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())