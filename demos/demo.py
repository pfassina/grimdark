#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.renderer import RendererConfig
from src.renderers.simple_renderer import SimpleRenderer
from src.game.game import Game


def main():
    print("Grimdark SRPG - Demo Mode")
    print("This demo uses the default test scenario with a simple renderer")
    print("The scenario includes varied terrain and balanced 3v3 combat")
    print("")
    
    config = RendererConfig(
        width=40,
        height=23,
        title="Grimdark SRPG Demo",
        target_fps=2
    )
    
    renderer = SimpleRenderer(config)
    
    game = Game(None, renderer)
    game.fps = 2
    game.frame_time = 1.0 / game.fps
    
    # Set to battle phase so it loads the default scenario
    from src.core.game_state import GamePhase
    game.state.phase = GamePhase.BATTLE
    
    try:
        game.run()
    except Exception as e:
        print(f"\nError: {e}")
        raise
    
    print("\nDemo complete!")
    print("\nThe architecture successfully demonstrates:")
    print("  ✓ Complete separation between game logic and rendering")
    print("  ✓ Renderer-agnostic design (easily swap renderers)")
    print("  ✓ Data-driven rendering through RenderContext")
    print("  ✓ Clean input abstraction")
    print("  ✓ Layered rendering system")
    print("  ✓ Scenario system with objectives and victory conditions")
    print("\nTo play interactively:")
    print("  - Run 'python main.py' for the default scenario")
    print("  - Run 'python demo_scenario.py assets/scenarios/tutorial.yaml' for specific scenarios")


if __name__ == "__main__":
    main()