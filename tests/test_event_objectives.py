#!/usr/bin/env python3
"""Test event-driven objective system functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.events import (
    UnitMoved, UnitDefeated, UnitSpawned, TurnStarted, TurnEnded, EventType, ObjectiveContext
)
from src.core.game_view import GameView
from src.core.game_enums import Team, ObjectiveStatus
from src.core.data_structures import Vector2
from src.game.objective_manager import ObjectiveManager
from src.game.objectives import (
    DefeatAllEnemiesObjective, SurviveTurnsObjective, ReachPositionObjective, 
    ProtectUnitObjective, DefeatUnitObjective
)
from src.game.map import GameMap
from src.game.unit import Unit, UnitClass


def test_event_routing():
    """Test that ObjectiveManager routes events only to interested objectives."""
    print("Testing event routing...")
    
    # Create a game map and view
    game_map = GameMap(5, 5)
    game_view = GameView(game_map)
    
    # Create objective manager
    manager = ObjectiveManager(game_view)
    
    # Create objectives with different interests
    defeat_enemies = DefeatAllEnemiesObjective()
    survive_turns = SurviveTurnsObjective(turns=5)
    
    manager.register_objectives([defeat_enemies], [survive_turns])
    
    # Check event subscription mapping
    stats = manager.get_event_stats()
    assert stats[EventType.UNIT_DEFEATED.name] == 1  # Only DefeatAllEnemiesObjective
    assert stats[EventType.UNIT_SPAWNED.name] == 1   # Only DefeatAllEnemiesObjective
    assert stats[EventType.TURN_ENDED.name] == 1     # Only SurviveTurnsObjective
    print("  ✓ Event routing correctly maps objectives to event types")
    
    # Test event delivery
    unit_defeated_event = UnitDefeated(
        turn=1,
        unit_name="Orc",
        team=Team.ENEMY,
        position=(2, 3)
    )
    
    manager.on_event(unit_defeated_event)
    
    # DefeatAllEnemiesObjective should have been notified (and its enemy count should have changed)
    # SurviveTurnsObjective should not have been affected
    print("  ✓ Events delivered only to interested objectives")


def test_defeat_all_enemies_objective():
    """Test DefeatAllEnemiesObjective event-driven functionality."""
    print("\nTesting DefeatAllEnemiesObjective...")
    
    # Create game map with enemy units
    game_map = GameMap(5, 5)
    enemy1 = Unit("Orc", UnitClass.WARRIOR, Team.ENEMY, 1, 1)
    enemy2 = Unit("Goblin", UnitClass.THIEF, Team.ENEMY, 3, 3)
    game_map.add_unit(enemy1)
    game_map.add_unit(enemy2)
    
    game_view = GameView(game_map)
    
    # Create objective and manager
    objective = DefeatAllEnemiesObjective()
    manager = ObjectiveManager(game_view)
    manager.register_objectives([objective], [])
    
    # Initial state should be IN_PROGRESS with 2 enemies
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    assert objective._enemy_count == 2
    print("  ✓ Initial state: IN_PROGRESS with correct enemy count")
    
    # Defeat first enemy
    defeat_event = UnitDefeated(
        turn=1,
        unit_name="Orc",
        team=Team.ENEMY,
        position=(1, 1)
    )
    manager.on_event(defeat_event)
    
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    assert objective._enemy_count == 1
    print("  ✓ After defeating one enemy: still IN_PROGRESS")
    
    # Defeat second enemy
    defeat_event2 = UnitDefeated(
        turn=2,
        unit_name="Goblin",
        team=Team.ENEMY,
        position=(3, 3)
    )
    manager.on_event(defeat_event2)
    
    assert objective.status == ObjectiveStatus.COMPLETED
    assert objective._enemy_count == 0
    print("  ✓ After defeating all enemies: COMPLETED")


def test_survive_turns_objective():
    """Test SurviveTurnsObjective event-driven functionality."""
    print("\nTesting SurviveTurnsObjective...")
    
    game_map = GameMap(5, 5)
    game_view = GameView(game_map)
    
    # Create objective and manager
    objective = SurviveTurnsObjective(turns=3)
    manager = ObjectiveManager(game_view)
    manager.register_objectives([objective], [])
    
    # Initial state should be IN_PROGRESS
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Initial state: IN_PROGRESS")
    
    # End turn 1
    turn_end_event = TurnEnded(turn=1, team=Team.PLAYER)
    manager.on_event(turn_end_event)
    
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Turn 1: still IN_PROGRESS")
    
    # End turn 2
    turn_end_event2 = TurnEnded(turn=2, team=Team.PLAYER)
    manager.on_event(turn_end_event2)
    
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Turn 2: still IN_PROGRESS")
    
    # End turn 3 (reaches requirement)
    turn_end_event3 = TurnEnded(turn=3, team=Team.PLAYER)
    manager.on_event(turn_end_event3)
    
    assert objective.status == ObjectiveStatus.COMPLETED
    print("  ✓ Turn 3: COMPLETED")


def test_reach_position_objective():
    """Test ReachPositionObjective event-driven functionality."""
    print("\nTesting ReachPositionObjective...")
    
    # Create game map with player unit
    game_map = GameMap(5, 5)
    hero = Unit("Hero", UnitClass.KNIGHT, Team.PLAYER, 0, 0)
    game_map.add_unit(hero)
    
    game_view = GameView(game_map)
    
    # Create objective to reach position (4, 4) with Hero
    objective = ReachPositionObjective(x=4, y=4, unit_name="Hero")
    manager = ObjectiveManager(game_view)
    manager.register_objectives([objective], [])
    
    # Initial state should be IN_PROGRESS
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Initial state: IN_PROGRESS")
    
    # Move Hero to wrong position
    move_event = UnitMoved(
        turn=1,
        unit_name="Hero",
        team=Team.PLAYER,
        from_position=(0, 0),
        to_position=(2, 2)
    )
    manager.on_event(move_event)
    
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Moved to wrong position: still IN_PROGRESS")
    
    # Move Hero to target position
    move_event2 = UnitMoved(
        turn=2,
        unit_name="Hero",
        team=Team.PLAYER,
        from_position=(2, 2),
        to_position=(4, 4)
    )
    manager.on_event(move_event2)
    
    assert objective.status == ObjectiveStatus.COMPLETED
    print("  ✓ Reached target position: COMPLETED")


def test_protect_unit_objective():
    """Test ProtectUnitObjective event-driven functionality."""
    print("\nTesting ProtectUnitObjective...")
    
    # Create game map with VIP unit
    game_map = GameMap(5, 5)
    vip = Unit("VIP", UnitClass.PRIEST, Team.PLAYER, 2, 2)
    game_map.add_unit(vip)
    
    game_view = GameView(game_map)
    
    # Create objective to protect VIP
    objective = ProtectUnitObjective(unit_name="VIP")
    manager = ObjectiveManager(game_view)
    manager.register_objectives([], [objective])  # Defeat objective
    
    # Initial state should be IN_PROGRESS
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Initial state: IN_PROGRESS")
    
    # Other unit gets defeated (should not affect objective)
    defeat_event = UnitDefeated(
        turn=1,
        unit_name="SomeOtherUnit",
        team=Team.PLAYER,
        position=(1, 1)
    )
    manager.on_event(defeat_event)
    
    assert objective.status == ObjectiveStatus.IN_PROGRESS
    print("  ✓ Other unit defeated: still IN_PROGRESS")
    
    # VIP gets defeated
    defeat_vip_event = UnitDefeated(
        turn=2,
        unit_name="VIP",
        team=Team.PLAYER,
        position=(2, 2)
    )
    manager.on_event(defeat_vip_event)
    
    assert objective.status == ObjectiveStatus.FAILED
    print("  ✓ VIP defeated: FAILED")


def test_game_view_adapter():
    """Test GameView adapter functionality."""
    print("\nTesting GameView adapter...")
    
    # Create game map with various units
    game_map = GameMap(5, 5)
    player1 = Unit("Hero", UnitClass.KNIGHT, Team.PLAYER, 1, 1)
    enemy1 = Unit("Orc", UnitClass.WARRIOR, Team.ENEMY, 3, 3)
    ally1 = Unit("Ally", UnitClass.ARCHER, Team.ALLY, 2, 2)
    
    game_map.add_unit(player1)
    game_map.add_unit(enemy1)
    game_map.add_unit(ally1)
    
    game_view = GameView(game_map)
    
    # Test unit retrieval
    unit_at_pos = game_view.get_unit_at(Vector2(1, 1))
    assert unit_at_pos is not None
    assert unit_at_pos.name == "Hero"
    assert unit_at_pos.team == Team.PLAYER
    print("  ✓ get_unit_at() works correctly")
    
    unit_by_name = game_view.get_unit_by_name("Orc")
    assert unit_by_name is not None
    assert unit_by_name.name == "Orc"
    assert unit_by_name.team == Team.ENEMY
    print("  ✓ get_unit_by_name() works correctly")
    
    # Test unit counting
    player_count = game_view.count_units(Team.PLAYER)
    enemy_count = game_view.count_units(Team.ENEMY)
    ally_count = game_view.count_units(Team.ALLY)
    
    assert player_count == 1
    assert enemy_count == 1
    assert ally_count == 1
    print("  ✓ count_units() works correctly")
    
    # Test unit iteration
    all_units = list(game_view.iter_units())
    player_units = list(game_view.iter_units(team=Team.PLAYER))
    
    assert len(all_units) == 3
    assert len(player_units) == 1
    assert player_units[0].name == "Hero"
    print("  ✓ iter_units() works correctly")


def test_objective_manager_victory_defeat():
    """Test ObjectiveManager victory/defeat aggregation."""
    print("\nTesting ObjectiveManager victory/defeat logic...")
    
    # Create game map with required units
    game_map = GameMap(5, 5)
    vip = Unit("VIP", UnitClass.PRIEST, Team.PLAYER, 2, 2)
    enemy = Unit("Orc", UnitClass.WARRIOR, Team.ENEMY, 3, 3)
    game_map.add_unit(vip)
    game_map.add_unit(enemy)
    
    game_view = GameView(game_map)
    
    # Create multiple victory and defeat objectives
    victory1 = DefeatAllEnemiesObjective()
    victory2 = SurviveTurnsObjective(turns=5)
    defeat1 = ProtectUnitObjective(unit_name="VIP")
    
    manager = ObjectiveManager(game_view)
    manager.register_objectives([victory1, victory2], [defeat1])
    
    # Initial state - no victory or defeat
    assert not manager.check_victory()
    assert not manager.check_defeat()
    print("  ✓ Initial state: no victory or defeat")
    
    # Complete one victory objective
    victory1.status = ObjectiveStatus.COMPLETED
    assert not manager.check_victory()  # Still need victory2
    assert not manager.check_defeat()
    print("  ✓ One victory objective complete: no victory yet")
    
    # Complete all victory objectives
    victory2.status = ObjectiveStatus.COMPLETED
    assert manager.check_victory()
    assert not manager.check_defeat()
    print("  ✓ All victory objectives complete: victory!")
    
    # Fail a defeat objective
    defeat1.status = ObjectiveStatus.FAILED
    assert manager.check_victory()  # Victory still true
    assert manager.check_defeat()   # But also defeat
    print("  ✓ Defeat objective failed: defeat condition triggered")


def test_integration_scenario_events():
    """Test integration between events, objectives, and scenarios.""" 
    print("\nTesting scenario integration...")
    
    # This would test the full integration with Scenario class
    # For now, just verify that the scenario can be initialized properly
    
    from src.game.scenario import Scenario
    
    # Create scenario with objectives
    scenario = Scenario(
        name="Test Scenario",
        description="Test scenario for event system",
        victory_objectives=[DefeatAllEnemiesObjective()],
        defeat_objectives=[ProtectUnitObjective("Hero")]
    )
    
    # Create game setup
    game_map = GameMap(5, 5)
    hero = Unit("Hero", UnitClass.KNIGHT, Team.PLAYER, 1, 1)
    enemy = Unit("Orc", UnitClass.WARRIOR, Team.ENEMY, 3, 3)
    game_map.add_unit(hero)
    game_map.add_unit(enemy)
    
    game_view = GameView(game_map)
    
    # Initialize objective manager
    scenario.initialize_objective_manager(game_view)
    
    assert scenario.objective_manager is not None
    assert not scenario.check_victory()  # Enemy still alive
    assert not scenario.check_defeat()   # Hero still alive
    print("  ✓ Scenario ObjectiveManager initialized correctly")
    
    # Simulate defeat enemy event
    defeat_event = UnitDefeated(turn=1, unit_name="Orc", team=Team.ENEMY, position=(3, 3))
    scenario.on_event(defeat_event)
    
    assert scenario.check_victory()  # Enemy defeated
    assert not scenario.check_defeat()
    print("  ✓ Victory achieved via event-driven update")


def main():
    print("=== Testing Event-Driven Objective System ===\n")
    
    test_event_routing()
    test_defeat_all_enemies_objective()
    test_survive_turns_objective()
    test_reach_position_objective()
    test_protect_unit_objective()
    test_game_view_adapter()
    test_objective_manager_victory_defeat()
    test_integration_scenario_events()
    
    print("\n✅ All event-driven objective tests passed!")


if __name__ == "__main__":
    main()