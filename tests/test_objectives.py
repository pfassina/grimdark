#!/usr/bin/env python3
"""Test scenario objectives functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.game.scenario_loader import ScenarioLoader
from src.game.map import GameMap
from src.game.unit import Unit, UnitClass, Team
from src.game.scenario import (
    DefeatAllEnemiesObjective, SurviveTurnsObjective,
    ReachPositionObjective, ProtectUnitObjective,
    ObjectiveStatus
)


def test_defeat_all_enemies():
    print("Testing DefeatAllEnemiesObjective...")
    
    # Create a small map
    game_map = GameMap(5, 5)
    
    # Add a player unit
    player = Unit("Hero", UnitClass.KNIGHT, Team.PLAYER, 1, 1)
    game_map.add_unit(player)
    
    # Add an enemy unit
    enemy = Unit("Enemy", UnitClass.WARRIOR, Team.ENEMY, 3, 3)
    game_map.add_unit(enemy)
    
    # Create objective
    objective = DefeatAllEnemiesObjective()
    
    # Check initial status
    status = objective.check_status(game_map, 1)
    assert status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Initial status: IN_PROGRESS")
    
    # Defeat the enemy
    enemy.take_damage(100)
    
    # Check status after defeating enemy
    status = objective.check_status(game_map, 2)
    assert status == ObjectiveStatus.COMPLETED
    print("  ✓ After defeating enemy: COMPLETED")


def test_survive_turns():
    print("\nTesting SurviveTurnsObjective...")
    
    game_map = GameMap(5, 5)
    objective = SurviveTurnsObjective(turns=5)
    
    # Check status on turn 1
    status = objective.check_status(game_map, 1)
    assert status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Turn 1: IN_PROGRESS")
    
    # Check status on turn 5
    status = objective.check_status(game_map, 5)
    assert status == ObjectiveStatus.COMPLETED
    print("  ✓ Turn 5: COMPLETED")


def test_reach_position():
    print("\nTesting ReachPositionObjective...")
    
    game_map = GameMap(5, 5)
    
    # Add a player unit
    unit = Unit("Hero", UnitClass.KNIGHT, Team.PLAYER, 1, 1)
    game_map.add_unit(unit)
    
    # Create objective to reach (3, 3)
    objective = ReachPositionObjective(x=3, y=3, unit_name="Hero")
    
    # Check initial status
    status = objective.check_status(game_map, 1)
    assert status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Initial position: IN_PROGRESS")
    
    # Move unit to target position
    game_map.move_unit(unit.unit_id, 3, 3)
    
    # Check status after moving
    status = objective.check_status(game_map, 2)
    assert status == ObjectiveStatus.COMPLETED
    print("  ✓ After reaching position: COMPLETED")


def test_protect_unit():
    print("\nTesting ProtectUnitObjective...")
    
    game_map = GameMap(5, 5)
    
    # Add a unit to protect
    vip = Unit("VIP", UnitClass.PRIEST, Team.PLAYER, 2, 2)
    game_map.add_unit(vip)
    
    # Create objective
    objective = ProtectUnitObjective(unit_name="VIP")
    
    # Check initial status
    status = objective.check_status(game_map, 1)
    assert status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Unit alive: IN_PROGRESS")
    
    # Kill the VIP
    vip.take_damage(100)
    
    # Check status after unit dies
    status = objective.check_status(game_map, 2)
    assert status == ObjectiveStatus.FAILED
    print("  ✓ Unit dead: FAILED")


def test_scenario_loading():
    print("\nTesting scenario loading from YAML...")
    
    # Load tutorial scenario
    scenario = ScenarioLoader.load_from_file("assets/scenarios/tutorial.yaml")
    
    assert scenario.name == "Tutorial - First Battle"
    print(f"  ✓ Loaded scenario: {scenario.name}")
    
    assert len(scenario.units) == 2
    print(f"  ✓ Units: {len(scenario.units)}")
    
    assert len(scenario.victory_objectives) == 1
    assert len(scenario.defeat_objectives) == 1
    print(f"  ✓ Objectives: {len(scenario.victory_objectives)} victory, {len(scenario.defeat_objectives)} defeat")


def main():
    print("=== Testing Scenario Objectives ===\n")
    
    test_defeat_all_enemies()
    test_survive_turns()
    test_reach_position()
    test_protect_unit()
    test_scenario_loading()
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    main()