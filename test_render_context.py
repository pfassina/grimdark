#!/usr/bin/env python3
"""Test what's being passed to the renderer."""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.game.scenario_loader import ScenarioLoader
from src.game.game import Game
from src.renderers.simple_renderer import SimpleRenderer
from src.core.renderer import RendererConfig

class DebugRenderer(SimpleRenderer):
    """Renderer that just prints what it receives."""
    
    def render_frame(self, context):
        print(f"Render context received:")
        print(f"  viewport: {context.viewport_width}x{context.viewport_height}")
        print(f"  world: {context.world_width}x{context.world_height}")
        print(f"  tiles: {len(context.tiles) if context.tiles else 0}")
        print(f"  units: {len(context.units) if context.units else 0}")
        print(f"  current_turn: {context.current_turn}")
        
        if context.tiles and len(context.tiles) > 0:
            print(f"  first tile: {context.tiles[0]}")
        
        # Only render one frame
        self._frame_count = 99  # Force quit

def test_render_context():
    """Test what render context is generated."""
    print("Testing render context generation...")
    
    # Set up game with debug renderer
    renderer = DebugRenderer(RendererConfig(width=40, height=23))
    game = Game(renderer=renderer)
    
    # Start the game (this should trigger one render frame)
    game.run()

if __name__ == '__main__':
    test_render_context()