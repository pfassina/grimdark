#!/usr/bin/env python3
"""Test YAML scenario loading functionality."""

import os
import sys
from pathlib import Path

# Add the project root to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.game.scenario_loader import ScenarioLoader


def test_yaml_scenarios():
    """Test loading all YAML scenarios."""
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    scenarios_dir = project_root / "assets" / "scenarios"
    
    # Find all YAML scenario files
    yaml_files = list(scenarios_dir.glob("*.yaml"))
    
    if not yaml_files:
        print("❌ No YAML scenario files found")
        return False
    
    print(f"Testing {len(yaml_files)} YAML scenarios...")
    
    success_count = 0
    
    for yaml_file in yaml_files:
        try:
            print(f"\nTesting: {yaml_file.name}")
            
            # Load the scenario
            scenario = ScenarioLoader.load_from_file(str(yaml_file))
            
            # Basic validation
            assert scenario.name, "Scenario must have a name"
            assert scenario.units, "Scenario must have units"
            assert scenario.victory_objectives, "Scenario must have victory objectives"
            assert scenario.defeat_objectives, "Scenario must have defeat objectives"
            assert scenario.map_file, "Scenario must have a map file"
            
            # Validate units have required fields
            for unit in scenario.units:
                assert unit.name, "Unit must have a name"
                assert unit.unit_class, "Unit must have a class"
                assert unit.team, "Unit must have a team"
                assert isinstance(unit.x, int) and isinstance(unit.y, int), "Unit must have valid position"
            
            # Validate objectives
            for obj in scenario.victory_objectives + scenario.defeat_objectives:
                assert hasattr(obj, 'description'), "Objective must have description"
            
            print(f"  ✅ {scenario.name}")
            print(f"     Units: {len(scenario.units)}")
            print(f"     Victory objectives: {len(scenario.victory_objectives)}")
            print(f"     Defeat objectives: {len(scenario.defeat_objectives)}")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            return False
    
    print(f"\n✅ All {success_count}/{len(yaml_files)} YAML scenarios loaded successfully!")
    return True


def test_json_yaml_equivalence():
    """Test that JSON and YAML versions of scenarios are equivalent."""
    
    project_root = Path(__file__).parent.parent
    scenarios_dir = project_root / "assets" / "scenarios"
    
    # Find pairs of JSON/YAML files
    yaml_files = list(scenarios_dir.glob("*.yaml"))
    pairs = []
    
    for yaml_file in yaml_files:
        json_file = yaml_file.with_suffix('.json')
        if json_file.exists():
            pairs.append((json_file, yaml_file))
    
    if not pairs:
        print("No JSON/YAML pairs found for comparison")
        return True
    
    print(f"\nComparing {len(pairs)} JSON/YAML pairs...")
    
    for json_file, yaml_file in pairs:
        try:
            # Load both versions
            json_scenario = ScenarioLoader.load_from_file(str(json_file))
            yaml_scenario = ScenarioLoader.load_from_file(str(yaml_file))
            
            # Compare key fields
            assert json_scenario.name == yaml_scenario.name, "Names don't match"
            assert json_scenario.description == yaml_scenario.description, "Descriptions don't match"
            assert json_scenario.author == yaml_scenario.author, "Authors don't match"
            assert len(json_scenario.units) == len(yaml_scenario.units), "Unit counts don't match"
            assert len(json_scenario.victory_objectives) == len(yaml_scenario.victory_objectives), "Victory objective counts don't match"
            assert len(json_scenario.defeat_objectives) == len(yaml_scenario.defeat_objectives), "Defeat objective counts don't match"
            
            print(f"  ✅ {yaml_file.stem}: JSON and YAML versions match")
            
        except Exception as e:
            print(f"  ❌ {yaml_file.stem}: Equivalence test failed: {e}")
            return False
    
    print("✅ All JSON/YAML pairs are equivalent!")
    return True


def main():
    """Run all YAML scenario tests."""
    
    print("=== Testing YAML Scenario Loading ===")
    
    # Test YAML loading
    if not test_yaml_scenarios():
        return False
    
    # Test JSON/YAML equivalence
    if not test_json_yaml_equivalence():
        return False
    
    print("\n🎉 All YAML scenario tests passed!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)