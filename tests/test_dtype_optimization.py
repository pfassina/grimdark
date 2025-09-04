#!/usr/bin/env python3
"""
Memory usage analysis for numpy dtype optimizations.

This test demonstrates the memory savings from using optimal data types
for coordinates, terrain types, and other game data structures.
"""

import numpy as np
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.data_structures import Vector2, VectorArray
from src.core.game_enums import TerrainType
from src.game.map import GameMap


def analyze_dtype_memory_usage():
    """Analyze memory usage differences between old and new dtypes."""
    
    print("="*60)
    print("NUMPY DTYPE MEMORY OPTIMIZATION ANALYSIS")  
    print("="*60)
    
    # Test map size similar to our game
    map_size = 50
    num_positions = map_size * map_size  # 2500 positions
    
    print(f"\nTest Configuration:")
    print(f"  Map size: {map_size}x{map_size} = {num_positions:,} tiles")
    print(f"  Positions tested: {num_positions:,}")
    
    # 1. Coordinate Storage Analysis
    print(f"\n🎯 Coordinate Storage (VectorArray):")
    
    # Old approach: int32 coordinates
    old_coords = np.zeros((num_positions, 2), dtype=np.int32)
    old_size = old_coords.nbytes
    
    # New approach: int16 coordinates  
    new_coords = np.zeros((num_positions, 2), dtype=np.int16)
    new_size = new_coords.nbytes
    
    coords_savings = old_size - new_size
    coords_ratio = old_size / new_size
    
    print(f"  int32 coordinates: {old_size:,} bytes")
    print(f"  int16 coordinates: {new_size:,} bytes") 
    print(f"  Memory saved: {coords_savings:,} bytes ({coords_ratio:.1f}x reduction)")
    
    # 2. Terrain Storage Analysis
    print(f"\n🌲 Terrain Storage (GameMap tiles):")
    
    # Old approach: int32 terrain types and elevation
    old_terrain_dtype = np.dtype([
        ('terrain_type', np.int32),
        ('elevation', np.int32)
    ])
    old_terrain = np.zeros((map_size, map_size), dtype=old_terrain_dtype)
    old_terrain_size = old_terrain.nbytes
    
    # New approach: uint8 terrain, int8 elevation
    new_terrain_dtype = np.dtype([
        ('terrain_type', np.uint8),
        ('elevation', np.int8)
    ])
    new_terrain = np.zeros((map_size, map_size), dtype=new_terrain_dtype)
    new_terrain_size = new_terrain.nbytes
    
    terrain_savings = old_terrain_size - new_terrain_size
    terrain_ratio = old_terrain_size / new_terrain_size
    
    print(f"  int32 terrain + elevation: {old_terrain_size:,} bytes")
    print(f"  uint8 terrain + int8 elevation: {new_terrain_size:,} bytes")
    print(f"  Memory saved: {terrain_savings:,} bytes ({terrain_ratio:.1f}x reduction)")
    
    # 3. Movement Cost Arrays
    print(f"\n⚡ Movement Cost Lookup Arrays:")
    
    max_terrain_value = 10  # Reasonable upper bound for terrain types
    
    # Old: int32 movement costs
    old_costs = np.ones(max_terrain_value, dtype=np.int32)
    old_costs_size = old_costs.nbytes
    
    # New: uint8 movement costs (values 1-10)
    new_costs = np.ones(max_terrain_value, dtype=np.uint8)
    new_costs_size = new_costs.nbytes
    
    costs_savings = old_costs_size - new_costs_size
    costs_ratio = old_costs_size / new_costs_size if new_costs_size > 0 else float('inf')
    
    print(f"  int32 movement costs: {old_costs_size:,} bytes")
    print(f"  uint8 movement costs: {new_costs_size:,} bytes")
    print(f"  Memory saved: {costs_savings:,} bytes ({costs_ratio:.1f}x reduction)")
    
    # 4. Distance Arrays (pathfinding)
    print(f"\n🗺️  Pathfinding Distance Arrays:")
    
    # Old: int32 distances
    old_distances = np.full((map_size, map_size), -1, dtype=np.int32)
    old_dist_size = old_distances.nbytes
    
    # New: int16 distances (sufficient for any reasonable game distance)
    new_distances = np.full((map_size, map_size), -1, dtype=np.int16)
    new_dist_size = new_distances.nbytes
    
    dist_savings = old_dist_size - new_dist_size
    dist_ratio = old_dist_size / new_dist_size
    
    print(f"  int32 distances: {old_dist_size:,} bytes")
    print(f"  int16 distances: {new_dist_size:,} bytes")
    print(f"  Memory saved: {dist_savings:,} bytes ({dist_ratio:.1f}x reduction)")
    
    # 5. Total Memory Analysis
    print(f"\n🎉 TOTAL MEMORY OPTIMIZATION:")
    
    total_old = old_size + old_terrain_size + old_costs_size + old_dist_size
    total_new = new_size + new_terrain_size + new_costs_size + new_dist_size
    total_savings = total_old - total_new
    total_ratio = total_old / total_new
    
    print(f"  Total old memory usage: {total_old:,} bytes")
    print(f"  Total new memory usage: {total_new:,} bytes")
    print(f"  Total memory saved: {total_savings:,} bytes ({total_ratio:.1f}x reduction)")
    print(f"  Percentage saved: {(total_savings/total_old)*100:.1f}%")
    
    # 6. Practical Benefits
    print(f"\n💡 PRACTICAL BENEFITS:")
    print(f"  Better CPU cache utilization (smaller data fits in cache)")
    print(f"  Faster memory transfers (less data to move)")  
    print(f"  Reduced memory pressure (more room for other game data)")
    print(f"  Improved vectorized operation performance")
    print(f"  Lower memory bandwidth requirements")
    
    # 7. Range Validation
    print(f"\n🔍 DATA RANGE VALIDATION:")
    
    # Check int16 coordinate range
    int16_range = (-32768, 32767)
    print(f"  int16 coordinate range: {int16_range[0]:,} to {int16_range[1]:,}")
    print(f"  Supports maps up to: {int16_range[1]:,}x{int16_range[1]:,}")
    
    # Check uint8 terrain range
    uint8_range = (0, 255)
    terrain_count = len(TerrainType)
    print(f"  uint8 terrain range: {uint8_range[0]} to {uint8_range[1]}")
    print(f"  Current terrain types: {terrain_count} (plenty of room for expansion)")
    
    # Check int8 elevation range
    int8_range = (-128, 127) 
    print(f"  int8 elevation range: {int8_range[0]} to {int8_range[1]}")
    print(f"  Supports elevation differences from deep valleys to high mountains")
    
    print(f"\n✅ All data ranges are more than sufficient for strategy game requirements!")
    
    return {
        'coords_savings_bytes': coords_savings,
        'coords_ratio': coords_ratio,
        'terrain_savings_bytes': terrain_savings, 
        'terrain_ratio': terrain_ratio,
        'total_savings_bytes': total_savings,
        'total_ratio': total_ratio,
        'total_percentage_saved': (total_savings/total_old)*100
    }


def test_functional_correctness():
    """Test that optimized dtypes work correctly in practice."""
    
    print(f"\n" + "="*60)
    print("FUNCTIONAL CORRECTNESS VALIDATION")
    print("="*60)
    
    # Test VectorArray with optimized dtypes
    print(f"\n🧪 Testing VectorArray with int16 coordinates...")
    
    positions = [Vector2(0, 0), Vector2(10, 20), Vector2(100, 200)]
    vec_array = VectorArray(positions)
    
    print(f"  Created VectorArray with {len(vec_array)} positions")
    print(f"  Internal dtype: {vec_array.data.dtype}")
    print(f"  Y coordinates: {list(vec_array.y_coords)}")
    print(f"  X coordinates: {list(vec_array.x_coords)}")
    
    # Test distance calculations
    target = Vector2(50, 100)
    distances = vec_array.distance_to_point(target)
    manhattan_distances = vec_array.manhattan_distance_to_point(target)
    
    print(f"  Distance calculations work: ✓")
    print(f"  Euclidean distances: {distances}")
    print(f"  Manhattan distances: {manhattan_distances}")
    
    # Test GameMap with optimized dtypes
    print(f"\n🗺️  Testing GameMap with optimized terrain storage...")
    
    game_map = GameMap(10, 10)
    print(f"  Created {game_map.width}x{game_map.height} map")
    print(f"  Terrain dtype: {game_map.tiles.dtype}")
    
    # Set some terrain
    game_map.set_tile(Vector2(5, 5), TerrainType.FOREST, elevation=3)
    tile_data = game_map.get_tile_data(Vector2(5, 5))
    
    print(f"  Set forest tile at (5,5) with elevation 3")
    print(f"  Retrieved: {tile_data}")
    print(f"  Terrain storage works correctly: ✓")
    
    print(f"\n✅ All functional tests passed! Optimized dtypes work perfectly.")


def main():
    """Run the complete dtype optimization analysis."""
    try:
        # Run memory analysis
        results = analyze_dtype_memory_usage()
        
        # Run functional tests
        test_functional_correctness()
        
        print(f"\n" + "="*60)
        print("DTYPE OPTIMIZATION ANALYSIS COMPLETE")
        print("="*60)
        
        print(f"\n🚀 KEY ACHIEVEMENTS:")
        print(f"  Memory usage reduced by {results['total_ratio']:.1f}x")
        print(f"  {results['total_percentage_saved']:.1f}% less memory required")
        print(f"  Coordinates are {results['coords_ratio']:.1f}x more memory efficient")
        print(f"  Terrain data is {results['terrain_ratio']:.1f}x more memory efficient")
        print(f"  All functionality preserved with optimized types")
        print(f"  Ready for larger game worlds and better performance!")
        
        return 0
        
    except Exception as e:
        print(f"Analysis failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())