#!/usr/bin/env python3
"""Simple test to verify map loading works with the simple renderer."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.game.map import GameMap
from src.game.game import Game
from src.renderers.simple_renderer import SimpleRenderer
from src.core.renderer import RendererConfig
from src.core.game_state import GamePhase

def main():
    # Load map from CSV directory
    game_map = GameMap.from_csv_layers('assets/maps/sample')
    print(f"Loaded map: {game_map.width}x{game_map.height}")
    
    # Create game with loaded map
    config = RendererConfig(width=game_map.width + 2, height=game_map.height + 5, target_fps=1)
    renderer = SimpleRenderer(config)
    game = Game(game_map, renderer)
    
    # Set to battle phase to show the map
    game.state.phase = GamePhase.BATTLE
    
    # Run just a few frames to see the map
    game.fps = 1
    game.frame_time = 1.0
    
    try:
        game.run()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()