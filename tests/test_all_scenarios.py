#!/usr/bin/env python3
"""Test all scenarios quickly."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.game.scenario_loader import ScenarioLoader

def test_scenario(scenario_path):
    print(f"\n=== Testing {scenario_path} ===")
    try:
        scenario = ScenarioLoader.load_from_file(scenario_path)
        print(f"✓ Name: {scenario.name}")
        print(f"✓ Description: {scenario.description}")
        
        # Create game map
        game_map = ScenarioLoader.create_game_map(scenario)
        print(f"✓ Map: {game_map.width}x{game_map.height}")
        
        # Place units
        ScenarioLoader.place_units(scenario, game_map)
        print(f"✓ Units: {len(game_map.units)}")
        
        # Check objectives
        print(f"✓ Objectives: {len(scenario.victory_objectives)} victory, {len(scenario.defeat_objectives)} defeat")
        
        # Test objective checking
        victory = scenario.check_victory(game_map, 1)
        defeat = scenario.check_defeat(game_map, 1)
        print(f"✓ Initial state: Victory={victory}, Defeat={defeat}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    scenarios = [
        "assets/scenarios/tutorial.yaml",
        "assets/scenarios/fortress_defense.yaml", 
        "assets/scenarios/escape_mission.yaml",
        "assets/scenarios/default_test.yaml"
    ]
    
    passed = 0
    total = len(scenarios)
    
    for scenario in scenarios:
        if test_scenario(scenario):
            passed += 1
    
    print("\n=== RESULTS ===")
    print(f"Passed: {passed}/{total} scenarios")
    
    if passed == total:
        print("🎉 All scenarios working correctly!")
    else:
        print("⚠️  Some scenarios have issues")

if __name__ == "__main__":
    main()