#!/usr/bin/env python3
"""Test scenario loading with simple renderer."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.game.scenario_loader import ScenarioLoader
from src.game.game import Game
from src.renderers.simple_renderer import SimpleRenderer
from src.core.renderer import RendererConfig


def main():
    # Load tutorial scenario
    scenario_file = "assets/scenarios/tutorial.yaml"
    
    print(f"Loading scenario: {scenario_file}")
    scenario = ScenarioLoader.load_from_file(scenario_file)
    
    print(f"\n=== {scenario.name} ===")
    print(f"{scenario.description}")
    print(f"Author: {scenario.author}")
    
    # Create game map from scenario
    game_map = ScenarioLoader.create_game_map(scenario)
    print(f"\nMap size: {game_map.width}x{game_map.height}")
    
    # Place units from scenario
    ScenarioLoader.place_units(scenario, game_map)
    print(f"Units placed: {len(game_map.units)}")
    
    for unit in game_map.units.values():
        print(f"  - {unit.name} ({unit.actor.get_class_name()}) at ({unit.position.x}, {unit.position.y})")
    
    # Create renderer and game
    config = RendererConfig(
        width=game_map.width + 2,
        height=game_map.height + 5,
        target_fps=2
    )
    renderer = SimpleRenderer(config)
    
    game = Game(game_map, renderer, scenario)
    game.fps = 2
    
    # Set to battle phase so the game renders the map
    from src.core.game_state import GamePhase
    game.state.phase = GamePhase.BATTLE
    
    print("\nStarting game...")
    
    try:
        game.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()