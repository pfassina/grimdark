#!/usr/bin/env python3
"""Demo script for playing scenarios."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.game.scenario_loader import ScenarioLoader
from src.game.game import Game
from src.renderers.terminal_renderer import TerminalRenderer
from src.core.renderer import RendererConfig


def main():
    if len(sys.argv) != 2:
        print("Usage: python demo_scenario.py <scenario_file.yaml>")
        print("\nAvailable scenarios:")
        print("  - assets/scenarios/tutorial.yaml")
        print("  - assets/scenarios/fortress_defense.yaml")
        print("  - assets/scenarios/escape_mission.yaml")
        return
    
    scenario_file = sys.argv[1]
    
    try:
        # Load scenario
        print(f"Loading scenario: {scenario_file}")
        scenario = ScenarioLoader.load_from_file(scenario_file)
        
        print(f"\n=== {scenario.name} ===")
        print(f"{scenario.description}")
        print(f"Author: {scenario.author}")
        print("\nObjectives:")
        
        if scenario.victory_objectives:
            print("\nVictory Conditions:")
            for obj in scenario.victory_objectives:
                print(f"  • {obj.description}")
        
        if scenario.defeat_objectives:
            print("\nDefeat Conditions:")
            for obj in scenario.defeat_objectives:
                print(f"  • {obj.description}")
        
        print("\nPress any key to start...")
        try:
            input()
        except EOFError:
            # Handle non-interactive environments
            print("(Running in non-interactive mode)")
        
        # Create game map from scenario
        game_map = ScenarioLoader.create_game_map(scenario)
        
        # Place units from scenario
        ScenarioLoader.place_units(scenario, game_map)
        
        # Create renderer
        config = RendererConfig(
            width=max(80, game_map.width + 10),
            height=max(24, game_map.height + 8)
        )
        renderer = TerminalRenderer(config)
        
        # Create game with scenario
        game = Game(game_map, renderer, scenario)
        
        # Run the game
        game.run()
        
    except FileNotFoundError:
        print(f"Error: Scenario file '{scenario_file}' not found")
    except Exception as e:
        print(f"Error loading scenario: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()