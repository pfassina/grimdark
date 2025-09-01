#!/usr/bin/env python3
"""Test the default scenario with simple renderer."""

from src.game.scenario_loader import ScenarioLoader
from src.game.game import Game
from src.renderers.simple_renderer import SimpleRenderer
from src.core.renderer import RendererConfig

def main():
    print("Testing default scenario...")
    
    # Load default scenario
    scenario = ScenarioLoader.load_from_file("assets/scenarios/default_test.yaml")
    
    print(f"✓ Loaded: {scenario.name}")
    print(f"  Description: {scenario.description}")
    
    # Create game map from scenario
    game_map = ScenarioLoader.create_game_map(scenario)
    print(f"✓ Map: {game_map.width}x{game_map.height}")
    
    # Place units from scenario
    ScenarioLoader.place_units(scenario, game_map)
    print(f"✓ Units: {len(game_map.units)}")
    
    for unit in game_map.units.values():
        print(f"    {unit.name} ({unit.actor.get_class_name()}, {unit.team.name}) at ({unit.x}, {unit.y})")
    
    print(f"✓ Objectives: {len(scenario.victory_objectives)} victory, {len(scenario.defeat_objectives)} defeat")
    
    # Test that Game can use None parameters and load default scenario
    print("\n--- Testing Game with None parameters ---")
    config = RendererConfig(width=25, height=20, target_fps=2)
    renderer = SimpleRenderer(config)
    
    game = Game(None, renderer)  # No map or scenario provided
    game.fps = 2
    
    print("✓ Game created successfully")
    print("Running a few frames to test default scenario loading...")
    
    try:
        # Just run a couple frames to test initialization
        import time
        game.initialize()
        print("✓ Game initialized with default scenario")
        
        # Build one render context to verify everything works
        context = game.build_render_context()
        print(f"✓ Render context built: {len(context.tiles)} tiles, {len(context.units)} units")
        
        game.cleanup()
        print("✓ Game cleanup successful")
        
        print("\n🎉 Default scenario test passed!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()