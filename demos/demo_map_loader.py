#!/usr/bin/env python3
"""Demo script showing map loading from CSV directories."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.game.map import GameMap
from src.game.game import Game
from src.renderers.terminal_renderer import TerminalRenderer
from src.core.renderer import RendererConfig
from src.core.game_state import GamePhase

def main():
    if len(sys.argv) != 2:
        print("Usage: python demo_map_loader.py <map_directory>")
        print("Example: python demo_map_loader.py assets/maps/sample")
        print("Available maps: tutorial, sample, fortress, escape_mission, default_test")
        return
    
    map_dir = sys.argv[1]
    
    try:
        # Load map from CSV directory
        game_map = GameMap.from_csv_layers(map_dir)
        print(f"Loaded map from {map_dir}: {game_map.width}x{game_map.height}")
        
        # Create game with loaded map
        config = RendererConfig(width=game_map.width + 2, height=game_map.height + 5)
        renderer = TerminalRenderer(config)
        game = Game(game_map, renderer)
        
        # Set to battle phase to show the map
        game.state.phase = GamePhase.BATTLE
        
        # Run the game
        game.run()
        
    except FileNotFoundError:
        print(f"Error: Map directory '{map_dir}' not found")
    except Exception as e:
        print(f"Error loading map: {e}")

if __name__ == "__main__":
    main()