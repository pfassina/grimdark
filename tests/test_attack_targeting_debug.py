#!/usr/bin/env python3
"""Debug script to test attack targeting with AOE."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import project modules (after path modification)
from src.game.map import GameMap  # noqa: E402
from src.core.game_enums import UnitClass, Team  # noqa: E402
from src.game.unit import Unit  # noqa: E402
from src.core.game_state import GameState  # noqa: E402
from src.core.data_structures import Vector2  # noqa: E402

def main():
    print("Testing Attack Targeting with AOE")
    print("=" * 40)
    
    # Create a small test map
    game_map = GameMap(10, 10)
    
    # Create a mage at position (2, 2)
    mage = Unit(
        name="Test Mage",
        unit_class=UnitClass.MAGE,
        team=Team.PLAYER,
        x=2,
        y=2
    )
    game_map.add_unit(mage)
    
    # Create an enemy at position (3, 2) - within mage's range
    enemy = Unit(
        name="Enemy Knight",
        unit_class=UnitClass.KNIGHT,
        team=Team.ENEMY,
        x=3,
        y=2
    )
    game_map.add_unit(enemy)
    
    # Calculate attack range for mage
    attack_range = game_map.calculate_attack_range(mage)
    print("\nMage at (2,2) with range 1-2")
    print(f"Attack range positions: {sorted(attack_range)}")
    
    # Check what happens when cursor is at enemy position
    cursor_pos = (3, 2)
    print(f"\nCursor at enemy position {cursor_pos}:")
    print(f"  Is in attack range? {cursor_pos in attack_range}")
    
    # Calculate AOE from enemy position
    aoe_pattern = mage.combat.aoe_pattern
    print(f"  Mage AOE pattern: {aoe_pattern}")
    
    aoe_tiles = game_map.calculate_aoe_tiles(cursor_pos, aoe_pattern)
    print(f"  AOE tiles from {cursor_pos}: {sorted(aoe_tiles)}")
    
    # Check if any position has an enemy
    print("\nPositions with units:")
    for pos in sorted(attack_range):
        unit_at_pos = game_map.get_unit_at(*pos)
        if unit_at_pos:
            print(f"  {pos}: {unit_at_pos.name} (Team {unit_at_pos.team})")
    
    # Create game state and test the targeting
    state = GameState()
    state.battle.selected_unit_id = mage.unit_id
    state.battle.set_attack_range(list(attack_range))
    
    # Simulate cursor movement
    print("\n" + "=" * 40)
    print("Simulating cursor movement:")
    
    # Move cursor to enemy position
    state.cursor.set_position(Vector2(2, 3))
    print("\nCursor at (3, 2) - enemy position")
    
    # Check if we should show AOE
    if state.cursor.position in state.battle.attack_range:
        state.battle.selected_target = state.cursor.position
        state.battle.aoe_tiles = game_map.calculate_aoe_tiles(state.cursor.position, aoe_pattern)
        print(f"  Selected target: {state.battle.selected_target}")
        print(f"  AOE tiles: {state.battle.aoe_tiles}")
    else:
        print("  Cursor not in attack range!")
    
    # Move cursor to empty position in range
    state.cursor.set_position(Vector2(2, 4))
    print("\nCursor at (4, 2) - empty position in range")
    
    if state.cursor.position in state.battle.attack_range:
        state.battle.selected_target = state.cursor.position
        state.battle.aoe_tiles = game_map.calculate_aoe_tiles(state.cursor.position, aoe_pattern)
        print(f"  Selected target: {state.battle.selected_target}")
        print(f"  AOE tiles: {state.battle.aoe_tiles}")
    else:
        print("  Cursor not in attack range!")

if __name__ == "__main__":
    main()