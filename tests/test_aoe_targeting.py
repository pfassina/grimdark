#!/usr/bin/env python3
"""Test AOE targeting functionality."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.game.map import GameMap
from src.game.unit import Unit
from src.game.components import CombatComponent
from src.core.game_enums import Team
from src.core.game_state import GameState
from src.game.game import Game
from src.core.input import InputEvent, Key
from src.core.renderable import RenderContext, AttackTargetRenderData

def test_aoe_patterns():
    """Test AOE pattern calculation."""
    print("Testing AOE Pattern Calculation")
    print("=" * 40)
    
    # Create a small test map
    game_map = GameMap(10, 10)
    
    # Test cross pattern
    print("\n1. Testing Cross Pattern (center at 5,5):")
    cross_tiles = game_map.calculate_aoe_tiles((5, 5), "cross")
    print(f"   Cross tiles: {sorted(cross_tiles)}")
    expected_cross = [(5, 5), (4, 5), (6, 5), (5, 4), (5, 6)]
    assert set(cross_tiles) == set(expected_cross), f"Expected {expected_cross}, got {cross_tiles}"
    print("   ✓ Cross pattern correct")
    
    # Test cross pattern at edge (clipping)
    print("\n2. Testing Cross Pattern at edge (0,0):")
    edge_cross = game_map.calculate_aoe_tiles((0, 0), "cross")
    print(f"   Edge cross tiles: {sorted(edge_cross)}")
    expected_edge = [(0, 0), (1, 0), (0, 1)]
    assert set(edge_cross) == set(expected_edge), f"Expected {expected_edge}, got {edge_cross}"
    print("   ✓ Edge clipping correct")
    
    # Test single pattern
    print("\n3. Testing Single Pattern:")
    single_tiles = game_map.calculate_aoe_tiles((3, 3), "single")
    print(f"   Single tiles: {single_tiles}")
    assert single_tiles == [(3, 3)], f"Expected [(3, 3)], got {single_tiles}"
    print("   ✓ Single pattern correct")

def test_combat_component_aoe():
    """Test that Combat component supports AOE patterns."""
    print("\n" + "=" * 40)
    print("Testing Combat Component AOE Support")
    print("=" * 40)
    
    # Create a test unit with mage stats
    from src.game.unit_templates import create_unit_entity
    from src.core.game_enums import UnitClass, Team
    
    # Create a mage entity
    mage_entity = create_unit_entity(
        name="Test Mage",
        unit_class=UnitClass.MAGE,
        team=Team.PLAYER,
        x=5,
        y=5
    )
    
    # Access the combat component
    mage_combat = mage_entity.get_component("Combat")
    
    print(f"\n1. Mage Combat Stats:")
    print(f"   Attack Range: {mage_combat.attack_range_min}-{mage_combat.attack_range_max}")
    print(f"   AOE Pattern: {mage_combat.aoe_pattern}")
    assert mage_combat.aoe_pattern == "cross", f"Expected 'cross' pattern, got {mage_combat.aoe_pattern}"
    print("   ✓ Mage has cross AOE pattern")
    
    # Create a knight for comparison
    knight = create_unit_entity(
        name="Test Knight",
        unit_class=UnitClass.KNIGHT,
        team=Team.PLAYER,
        x=3,
        y=3
    )
    
    knight_combat = knight.get_component("Combat")
    
    print(f"\n2. Knight Combat Stats:")
    print(f"   Attack Range: {knight_combat.attack_range_min}-{knight_combat.attack_range_max}")
    print(f"   AOE Pattern: {knight_combat.aoe_pattern}")
    assert knight_combat.aoe_pattern == "single", f"Expected 'single' pattern, got {knight_combat.aoe_pattern}"
    print("   ✓ Knight has single target pattern")

def test_render_data():
    """Test AttackTargetRenderData creation."""
    print("\n" + "=" * 40)
    print("Testing Attack Target Render Data")
    print("=" * 40)
    
    # Create test render data
    range_target = AttackTargetRenderData(x=5, y=5, target_type="range", blink_phase=False)
    aoe_target = AttackTargetRenderData(x=6, y=5, target_type="aoe", blink_phase=True)
    selected_target = AttackTargetRenderData(x=5, y=4, target_type="selected", blink_phase=True)
    
    print("\n1. Range target data:")
    print(f"   Position: ({range_target.x}, {range_target.y})")
    print(f"   Type: {range_target.target_type}")
    print(f"   Blink: {range_target.blink_phase}")
    print("   ✓ Range target created")
    
    print("\n2. AOE target data:")
    print(f"   Position: ({aoe_target.x}, {aoe_target.y})")
    print(f"   Type: {aoe_target.target_type}")
    print(f"   Blink: {aoe_target.blink_phase}")
    print("   ✓ AOE target created")
    
    print("\n3. Selected target data:")
    print(f"   Position: ({selected_target.x}, {selected_target.y})")
    print(f"   Type: {selected_target.target_type}")
    print(f"   Blink: {selected_target.blink_phase}")
    print("   ✓ Selected target created")

def main():
    """Run all AOE targeting tests."""
    print("AOE Targeting System Test Suite")
    print("=" * 40)
    
    try:
        test_aoe_patterns()
        test_combat_component_aoe()
        test_render_data()
        
        print("\n" + "=" * 40)
        print("✓ All AOE targeting tests passed!")
        print("=" * 40)
        
        print("\nKey features verified:")
        print("  • Cross AOE pattern calculation")
        print("  • Map boundary clipping for AOE")
        print("  • Combat component AOE pattern support")
        print("  • Mage class has cross AOE attack")
        print("  • AttackTargetRenderData structures")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())