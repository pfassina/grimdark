#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.renderable import (
    RenderContext, TileRenderData, UnitRenderData,
    CursorRenderData
)
from src.game.map import GameMap
from src.game.tile import TerrainType
from src.game.unit import Unit, UnitClass, Team


def test_architecture():
    print("Testing Grimdark SRPG Architecture")
    print("=" * 40)
    
    print("\n1. Creating game map...")
    game_map = GameMap(20, 15)
    
    for x in range(3, 7):
        game_map.set_tile(x, 3, TerrainType.FOREST)
    
    for y in range(5, 8):
        game_map.set_tile(10, y, TerrainType.MOUNTAIN)
    
    print(f"   Map created: {game_map.width}x{game_map.height}")
    
    print("\n2. Adding units...")
    knight = Unit("Knight 1", UnitClass.KNIGHT, Team.PLAYER, 2, 2)
    archer = Unit("Archer 1", UnitClass.ARCHER, Team.PLAYER, 4, 3)
    enemy = Unit("Enemy Knight", UnitClass.KNIGHT, Team.ENEMY, 15, 8)
    
    game_map.add_unit(knight)
    game_map.add_unit(archer)
    game_map.add_unit(enemy)
    
    print(f"   Added {len(game_map.units)} units")
    
    print("\n3. Testing movement calculation...")
    movement_range = game_map.calculate_movement_range(knight)
    print(f"   Knight can move to {len(movement_range)} tiles")
    
    print("\n4. Testing attack range calculation...")
    attack_range = game_map.calculate_attack_range(archer)
    print(f"   Archer can attack {len(attack_range)} tiles")
    
    print("\n5. Building render context...")
    context = RenderContext()
    context.viewport_width = 20
    context.viewport_height = 10
    
    for y in range(10):
        for x in range(20):
            tile = game_map.get_tile(x, y)
            if tile:
                context.tiles.append(TileRenderData(
                    x=x,
                    y=y,
                    terrain_type=tile.terrain_type.name.lower(),
                    elevation=tile.elevation
                ))
    
    for unit in game_map.units.values():
        context.units.append(UnitRenderData(
            x=unit.x,
            y=unit.y,
            unit_type=unit.actor.get_class_name(),
            team=unit.team.value,
            hp_current=unit.hp_current,
            hp_max=unit.health.hp_max
        ))
    
    context.cursor = CursorRenderData(x=2, y=2)
    
    print(f"   Render context has {len(context.tiles)} tiles")
    print(f"   Render context has {len(context.units)} units")
    
    print("\n6. Displaying ASCII map:")
    print("-" * 40)
    
    grid = [['.' for _ in range(20)] for _ in range(10)]
    
    for tile in context.tiles[:200]:
        if 0 <= tile.x < 20 and 0 <= tile.y < 10:
            terrain_symbols = {
                "plain": ".",
                "forest": "F",
                "mountain": "M",
                "water": "~",
            }
            grid[tile.y][tile.x] = terrain_symbols.get(tile.terrain_type, "?")
    
    for unit in context.units:
        if 0 <= unit.x < 20 and 0 <= unit.y < 10:
            team_symbols = {0: "@", 1: "E", 2: "A", 3: "N"}
            grid[unit.y][unit.x] = team_symbols.get(unit.team, "?")
    
    if context.cursor and 0 <= context.cursor.x < 20 and 0 <= context.cursor.y < 10:
        grid[context.cursor.y][context.cursor.x] = "X"
    
    for row in grid:
        print("   " + "".join(row))
    
    print("-" * 40)
    
    print("\n✓ Architecture test complete!")
    print("\nKey features demonstrated:")
    print("  • Complete separation of game logic and rendering")
    print("  • Data-driven render context")
    print("  • Flexible entity system")
    print("  • Grid-based movement and combat")
    print("  • Team-based units")
    print("  • Renderer-agnostic design")
    
    print("\nYou can now:")
    print("  1. Run 'python main.py' in a proper terminal for interactive play")
    print("  2. Create new renderer implementations (pygame, raylib, etc.)")
    print("  3. Extend the game logic without touching rendering code")


if __name__ == "__main__":
    test_architecture()