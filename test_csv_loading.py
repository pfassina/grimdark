#!/usr/bin/env python3
"""Quick test to verify CSV map loading works."""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.game.map import GameMap

def test_csv_loading():
    """Test loading a CSV map."""
    print("Testing CSV map loading...")
    
    # Test CSV loading
    try:
        csv_map = GameMap.from_csv_layers("assets/maps/fortress")
        print(f"✓ CSV loading successful: {csv_map.width}x{csv_map.height}")
        
        # Check some tiles
        test_positions = [(0, 0), (7, 5), (14, 11)]
        for x, y in test_positions:
            tile = csv_map.get_tile(x, y)
            if tile:
                print(f"  Tile at ({x}, {y}): {tile.terrain_type}")
            else:
                print(f"  No tile at ({x}, {y})")
                
    except Exception as e:
        print(f"✗ CSV loading failed: {e}")
    
    print("✓ CSV map loading test complete!")

if __name__ == '__main__':
    test_csv_loading()