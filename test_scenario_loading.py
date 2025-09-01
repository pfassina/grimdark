#!/usr/bin/env python3
"""Quick test to verify scenario loading works."""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.game.scenario_loader import ScenarioLoader

def test_scenario_loading():
    """Test loading a scenario with CSV maps."""
    print("Testing scenario loading...")
    
    scenario_file = "assets/scenarios/default_test.yaml"
    
    try:
        # Load scenario
        scenario = ScenarioLoader.load_from_file(scenario_file)
        print(f"✓ Scenario loaded: {scenario.name}")
        print(f"  Map file: {scenario.map_file}")
        print(f"  Units: {len(scenario.units)}")
        
        # Load map
        game_map = ScenarioLoader.create_game_map(scenario)
        print(f"✓ Map loaded: {game_map.width}x{game_map.height}")
        
        # Place units
        ScenarioLoader.place_units(scenario, game_map)
        print(f"✓ Units placed: {len(game_map.units)}")
        
        # List units
        for unit_name, unit in game_map.units.items():
            print(f"  {unit_name}: {unit.unit_class} at ({unit.x}, {unit.y})")
        
    except Exception as e:
        import traceback
        print(f"✗ Scenario loading failed: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    test_scenario_loading()