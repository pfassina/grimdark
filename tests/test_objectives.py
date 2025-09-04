#!/usr/bin/env python3
"""Test scenario objectives functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.game.scenario_loader import ScenarioLoader
from src.game.map import GameMap
from src.game.unit import Unit, UnitClass, Team
from src.game.objectives import (
    DefeatAllEnemiesObjective, SurviveTurnsObjective,
    ReachPositionObjective, ProtectUnitObjective
)
from src.core.game_enums import ObjectiveStatus
from src.game.objective_manager import ObjectiveManager
from src.core.game_view import GameView
from src.core.events import UnitDefeated, TurnEnded, UnitMoved


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
    
    game_view = GameView(game_map)
    
    # Create objective and manager
    objective = DefeatAllEnemiesObjective()
    manager = ObjectiveManager(game_view)
    manager.register_objectives([objective], [])
    
    # Check initial status
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Initial status: IN_PROGRESS")
    
    # Defeat the enemy by emitting event
    defeat_event = UnitDefeated(
        turn=1,
        unit_name="Enemy", 
        team=Team.ENEMY,
        position=(3, 3)
    )
    manager.on_event(defeat_event)
    
    # Check status after defeating enemy
    assert objective.status == ObjectiveStatus.COMPLETED
    print("  ✓ After defeating enemy: COMPLETED")


def test_survive_turns():
    print("\nTesting SurviveTurnsObjective...")
    
    game_map = GameMap(5, 5)
    game_view = GameView(game_map)
    
    objective = SurviveTurnsObjective(turns=5)
    manager = ObjectiveManager(game_view)
    manager.register_objectives([objective], [])
    
    # Check status on turn 1
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Turn 1: IN_PROGRESS")
    
    # Emit turn ended event for turn 5
    turn_event = TurnEnded(turn=5, team=Team.PLAYER)
    manager.on_event(turn_event)
    
    # Check status after turn 5
    assert objective.status == ObjectiveStatus.COMPLETED
    print("  ✓ Turn 5: COMPLETED")


def test_reach_position():
    print("\nTesting ReachPositionObjective...")
    
    game_map = GameMap(5, 5)
    
    # Add a player unit
    unit = Unit("Hero", UnitClass.KNIGHT, Team.PLAYER, 1, 1)
    game_map.add_unit(unit)
    
    game_view = GameView(game_map)
    
    # Create objective to reach (3, 3)
    objective = ReachPositionObjective(x=3, y=3, unit_name="Hero")
    manager = ObjectiveManager(game_view)
    manager.register_objectives([objective], [])
    
    # Check initial status
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Initial position: IN_PROGRESS")
    
    # Emit unit moved event to target position
    move_event = UnitMoved(
        turn=1,
        unit_name="Hero",
        team=Team.PLAYER,
        from_position=(1, 1),
        to_position=(3, 3)
    )
    manager.on_event(move_event)
    
    # Check status after moving
    assert objective.status == ObjectiveStatus.COMPLETED
    print("  ✓ After reaching position: COMPLETED")


def test_protect_unit():
    print("\nTesting ProtectUnitObjective...")
    
    game_map = GameMap(5, 5)
    
    # Add a unit to protect
    vip = Unit("VIP", UnitClass.PRIEST, Team.PLAYER, 2, 2)
    game_map.add_unit(vip)
    
    game_view = GameView(game_map)
    
    # Create objective
    objective = ProtectUnitObjective(unit_name="VIP")
    manager = ObjectiveManager(game_view)
    manager.register_objectives([], [objective])  # Defeat objective
    
    # Check initial status
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Unit alive: IN_PROGRESS")
    
    # Emit unit defeated event for VIP
    defeat_event = UnitDefeated(
        turn=1,
        unit_name="VIP",
        team=Team.PLAYER,
        position=(2, 2)
    )
    manager.on_event(defeat_event)
    
    # Check status after unit dies
    assert objective.status == ObjectiveStatus.FAILED
    print("  ✓ Unit dead: FAILED")


def test_scenario_loading():
    print("\nTesting scenario loading and event-driven integration...")
    
    # Load tutorial scenario
    scenario = ScenarioLoader.load_from_file("assets/scenarios/tutorial.yaml")
    
    assert scenario.name == "Tutorial - First Battle"
    print(f"  ✓ Loaded scenario: {scenario.name}")
    
    assert len(scenario.units) == 2
    print(f"  ✓ Units: {len(scenario.units)}")
    
    assert len(scenario.victory_objectives) == 1
    assert len(scenario.defeat_objectives) == 1
    print(f"  ✓ Objectives: {len(scenario.victory_objectives)} victory, {len(scenario.defeat_objectives)} defeat")
    
    # Test event-driven integration
    game_map = GameMap(10, 10)
    
    # Add units to match the scenario's expectations
    player = Unit("Hero", UnitClass.KNIGHT, Team.PLAYER, 1, 1)
    enemy = Unit("Test Enemy", UnitClass.WARRIOR, Team.ENEMY, 5, 5)
    game_map.add_unit(player)  # Player unit so AllUnitsDefeatedObjective doesn't fail immediately
    game_map.add_unit(enemy)   # Enemy unit so DefeatAllEnemiesObjective isn't completed immediately
    
    game_view = GameView(game_map)
    
    # Initialize ObjectiveManager
    scenario.initialize_objective_manager(game_view)
    
    assert scenario.objective_manager is not None
    assert not scenario.check_victory()  # Should not be victorious initially (enemy still alive)
    assert not scenario.check_defeat()   # Should not be defeated initially (player still alive)
    print("  ✓ Event-driven ObjectiveManager initialized successfully")


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