#!/usr/bin/env python3
"""Visual test for AOE attack targeting overlay."""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import project modules (after path modification)
from src.game.map import GameMap  # noqa: E402
from src.game.unit import Unit  # noqa: E402
from src.core.game_enums import UnitClass, Team  # noqa: E402
from src.core.data_structures import Vector2  # noqa: E402
from src.core.game_state import GameState, GamePhase, BattlePhase  # noqa: E402
from src.core.renderable import RenderContext, AttackTargetRenderData  # noqa: E402
from src.renderers.simple_renderer import SimpleRenderer  # noqa: E402
from src.core.renderer import RendererConfig  # noqa: E402

def main():
    print("Testing AOE Attack Targeting Visual Display")
    print("=" * 50)
    
    # Create a small test map
    game_map = GameMap(10, 8)
    
    # Create a mage at position (3, 3)
    mage = Unit(
        name="Test Mage",
        unit_class=UnitClass.MAGE,
        team=Team.PLAYER,
        x=3,
        y=3
    )
    game_map.add_unit(mage)
    
    # Create enemies around the mage
    enemy1 = Unit(
        name="Enemy1",
        unit_class=UnitClass.KNIGHT,
        team=Team.ENEMY,
        x=4,
        y=3
    )
    game_map.add_unit(enemy1)
    
    enemy2 = Unit(
        name="Enemy2", 
        unit_class=UnitClass.WARRIOR,
        team=Team.ENEMY,
        x=3,
        y=4
    )
    game_map.add_unit(enemy2)
    
    # Create enemy that's outside attack range but inside potential AOE
    enemy3 = Unit(
        name="Enemy3",
        unit_class=UnitClass.THIEF,
        team=Team.ENEMY,
        x=2,
        y=2  # This should be outside attack range but could be in AOE
    )
    game_map.add_unit(enemy3)
    
    # Create game state in attack mode
    state = GameState()
    state.phase = GamePhase.BATTLE
    state.battle.phase = BattlePhase.TARGETING
    state.battle.selected_unit_id = mage.unit_id
    state.cursor.set_position(Vector2(2, 3))  # y,x
    
    # Calculate attack range
    attack_range = game_map.calculate_attack_range(mage)
    state.battle.set_attack_range(list(attack_range))
    
    # Set selected target and AOE tiles
    state.battle.selected_target = state.cursor.position
    state.battle.aoe_tiles = game_map.calculate_aoe_tiles(state.battle.selected_target, mage.combat.aoe_pattern)
    
    print(f"Mage at ({mage.x}, {mage.y})")
    print(f"Attack range: {sorted(attack_range)}")
    print(f"Cursor at ({state.cursor.position.x}, {state.cursor.position.y})")
    print(f"Selected target: {state.battle.selected_target}")
    print(f"AOE pattern: {mage.combat.aoe_pattern}")
    print(f"AOE tiles: {sorted(state.battle.aoe_tiles)}")
    print()
    
    # Create simple renderer for display
    config = RendererConfig(width=30, height=12, title="AOE Test", target_fps=2)
    renderer = SimpleRenderer(config)
    renderer.initialize()
    
    try:
        # Show 4 frames to demonstrate blinking
        for frame in range(4):
            print(f"--- Frame {frame + 1} ---")
            
            # Build render context
            context = RenderContext()
            context.world_width = game_map.width
            context.world_height = game_map.height
            context.viewport_width = game_map.width
            context.viewport_height = game_map.height
            context.current_time_ms = int(time.time() * 1000)
            
            # Calculate blink phase
            blink_phase = (context.current_time_ms // 500) % 2 == 1
            
            # Add terrain tiles
            from src.core.renderable import TileRenderData
            for y in range(game_map.height):
                for x in range(game_map.width):
                    tile = game_map.get_tile(Vector2(y, x))
                    if tile is not None:
                        context.tiles.append(TileRenderData(position=Vector2(y, x), terrain_type=tile.terrain_type.name, layer=1))
            
            # Add units
            from src.core.renderable import UnitRenderData
            for unit in game_map.units.values():
                context.units.append(UnitRenderData(
                    position=unit.position,
                    unit_type=unit.actor.unit_class.name,
                    team=unit.actor.team.value,  # Convert enum to int
                    hp_current=unit.health.hp_current,
                    hp_max=unit.health.hp_max
                ))
            
            # Add cursor
            from src.core.renderable import CursorRenderData
            context.cursor = CursorRenderData(position=state.cursor.position)
            
            # Add attack targeting overlay
            # Range tiles
            for pos in state.battle.attack_range:
                if pos != state.battle.selected_target and pos not in state.battle.aoe_tiles:
                    context.attack_targets.append(AttackTargetRenderData(
                        x=pos[0], y=pos[1], target_type="range", blink_phase=blink_phase
                    ))
            
            # AOE tiles
            for pos in state.battle.aoe_tiles:
                if pos != state.battle.selected_target:
                    context.attack_targets.append(AttackTargetRenderData(
                        x=pos[0], y=pos[1], target_type="aoe", blink_phase=blink_phase
                    ))
            
            # Selected target
            if state.battle.selected_target:
                context.attack_targets.append(AttackTargetRenderData(
                    x=state.battle.selected_target[0], y=state.battle.selected_target[1], 
                    target_type="selected", blink_phase=blink_phase
                ))
            
            # Render frame
            renderer.render_frame(context)
            
            # Wait to show blinking
            time.sleep(0.3)
        
    finally:
        renderer.cleanup()
    
    print("\nTest complete!")
    print("Expected display:")
    print("  . = attack range tiles")
    print("  * = AOE tiles (blinking)")
    print("  X = selected target (blinking)")
    print("  M = mage, K = knight, W = warrior")

if __name__ == "__main__":
    main()