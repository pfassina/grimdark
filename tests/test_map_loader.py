#!/usr/bin/env python3
"""Test script for map loading functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.game.map import GameMap
from src.core.game_enums import TerrainType

def test_map_loading():
    # Test loading from CSV directory
    game_map = GameMap.from_csv_layers('assets/maps/fortress')
    
    print(f"Loaded map: {game_map.width}x{game_map.height}")
    
    # Check some specific tiles from fortress map
    tile = game_map.get_tile(0, 0)
    assert tile is not None and tile.terrain_type == TerrainType.WALL
    tile = game_map.get_tile(1, 1)
    assert tile is not None and tile.terrain_type == TerrainType.PLAIN
    tile = game_map.get_tile(2, 2)
    assert tile is not None and tile.terrain_type == TerrainType.FOREST
    tile = game_map.get_tile(6, 5)
    assert tile is not None and tile.terrain_type == TerrainType.BRIDGE
    tile = game_map.get_tile(7, 9)
    assert tile is not None and tile.terrain_type == TerrainType.FORT
    
    print("Map loaded successfully!")
    print("✓ All terrain types verified correctly")

if __name__ == "__main__":
    test_map_loading()