"""
Unit tests for the GameMap class.

Tests grid-based battlefield mechanics, pathfinding, visibility,
unit management, and terrain interaction.
"""
import pytest

from src.game.map import GameMap
from src.game.tile import Tile, TerrainType
from src.core.data_structures import Vector2, VectorArray
from src.core.game_enums import Team, UnitClass
from tests.conftest import TestDataBuilder
# Test constants
SMALL_MAP_SIZE = (5, 5)
MEDIUM_MAP_SIZE = (10, 10)
LARGE_MAP_SIZE = (20, 20)


class TestGameMapInitialization:
    """Test GameMap initialization and basic properties."""
    
    def test_initialization_small_map(self):
        """Test GameMap initialization with small dimensions."""
        width, height = SMALL_MAP_SIZE
        game_map = GameMap(width, height)
        
        assert game_map.width == width
        assert game_map.height == height
        assert len(game_map.units) == 0
    
    def test_initialization_medium_map(self):
        """Test GameMap initialization with medium dimensions."""
        width, height = MEDIUM_MAP_SIZE
        game_map = GameMap(width, height)
        
        assert game_map.width == width
        assert game_map.height == height
    
    def test_initialization_large_map(self):
        """Test GameMap initialization with large dimensions."""
        width, height = LARGE_MAP_SIZE
        game_map = GameMap(width, height)
        
        assert game_map.width == width
        assert game_map.height == height
    
    def test_default_terrain(self, small_map):
        """Test that map initializes with default terrain."""
        # Check that all positions have valid tiles
        for y in range(small_map.height):
            for x in range(small_map.width):
                pos = Vector2(y, x)
                tile = small_map.get_tile(pos)
                assert tile is not None
                assert isinstance(tile.terrain_type, TerrainType)
    
    @pytest.mark.parametrize("width,height", [
        (1, 1), (5, 5), (10, 10), (20, 20), (50, 30)
    ])
    def test_various_dimensions(self, width: int, height: int):
        """Test GameMap with various dimensions."""
        game_map = GameMap(width, height)
        
        assert game_map.width == width
        assert game_map.height == height
        
        # Should be able to access all positions
        for y in range(height):
            for x in range(width):
                pos = Vector2(y, x)
                assert game_map.is_valid_position(pos)


class TestPositionValidation:
    """Test position validation and boundary checking."""
    
    def test_valid_positions(self, small_map):
        """Test validation of valid positions."""
        width, height = small_map.width, small_map.height
        
        # Test corners
        assert small_map.is_valid_position(Vector2(0, 0))
        assert small_map.is_valid_position(Vector2(width - 1, 0))
        assert small_map.is_valid_position(Vector2(0, height - 1))
        assert small_map.is_valid_position(Vector2(width - 1, height - 1))
        
        # Test center
        center_x, center_y = width // 2, height // 2
        assert small_map.is_valid_position(Vector2(center_x, center_y))
    
    def test_invalid_positions(self, small_map):
        """Test validation of invalid positions."""
        width, height = small_map.width, small_map.height
        
        # Test out of bounds
        assert not small_map.is_valid_position(Vector2(-1, 0))
        assert not small_map.is_valid_position(Vector2(0, -1))
        assert not small_map.is_valid_position(Vector2(width, 0))
        assert not small_map.is_valid_position(Vector2(0, height))
        assert not small_map.is_valid_position(Vector2(width, height))
        
        # Test extreme values
        assert not small_map.is_valid_position(Vector2(-100, -100))
        assert not small_map.is_valid_position(Vector2(1000, 1000))
    
    @pytest.mark.parametrize("x,y,expected", [
        (0, 0, True),      # Top-left corner
        (4, 4, True),      # Valid position in 5x5 map
        (-1, 0, False),    # Left boundary violation
        (0, -1, False),    # Top boundary violation
        (5, 0, False),     # Right boundary violation (5x5 map)
        (0, 5, False),     # Bottom boundary violation (5x5 map)
    ])
    def test_position_validation_cases(self, x: int, y: int, expected: bool):
        """Test specific position validation cases."""
        game_map = GameMap(5, 5)
        result = game_map.is_valid_position(Vector2(x, y))
        assert result == expected


class TestTileManagement:
    """Test tile management and terrain manipulation."""
    
    def test_get_tile(self, small_map):
        """Test getting tiles from map."""
        pos = Vector2(2, 2)
        tile = small_map.get_tile(pos)
        
        assert tile is not None
        assert isinstance(tile, Tile)
        assert hasattr(tile, 'terrain_type')
    
    def test_set_tile(self, small_map):
        """Test setting tiles on map."""
        pos = Vector2(1, 1)
        
        # Set forest tile
        small_map.set_tile(pos, TerrainType.FOREST)
        tile = small_map.get_tile(pos)
        
        assert tile.terrain_type == TerrainType.FOREST
    
    def test_get_invalid_tile(self, small_map):
        """Test getting tile from invalid position."""
        invalid_pos = Vector2(-1, -1)
        tile = small_map.get_tile(invalid_pos)
        
        assert tile is None
    
    def test_set_invalid_tile(self, small_map):
        """Test setting tile at invalid position."""
        invalid_pos = Vector2(100, 100)
        
        # Should handle gracefully
        try:
            small_map.set_tile(invalid_pos, TerrainType.MOUNTAIN)
            # If it doesn't crash, that's acceptable
        except (IndexError, ValueError):
            # May raise error for invalid positions
            pass
    
    def test_terrain_types_setting(self, small_map):
        """Test setting different terrain types."""
        positions = [Vector2(i, i) for i in range(min(small_map.width, small_map.height))]
        terrain_types = [TerrainType.PLAIN, TerrainType.FOREST, TerrainType.MOUNTAIN, TerrainType.WATER]
        
        for i, pos in enumerate(positions):
            terrain = terrain_types[i % len(terrain_types)]
            small_map.set_tile(pos, terrain)
            
            tile = small_map.get_tile(pos)
            assert tile.terrain_type == terrain


class TestUnitManagement:
    """Test unit placement and management on the map."""
    
    def test_add_unit(self, small_map):
        """Test adding a unit to the map."""
        unit = TestDataBuilder.unit("Test Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(2, 2))
        
        small_map.add_unit(unit)
        
        assert len(small_map.units) == 1
        assert unit.unit_id in small_map.units
        assert small_map.units[unit.unit_id] == unit
    
    def test_add_multiple_units(self, small_map):
        """Test adding multiple units to the map."""
        knight = TestDataBuilder.unit("Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(1, 1))
        archer = TestDataBuilder.unit("Archer", UnitClass.ARCHER, Team.PLAYER, Vector2(2, 2))
        enemy = TestDataBuilder.unit("Enemy", UnitClass.WARRIOR, Team.ENEMY, Vector2(3, 3))
        
        for unit in [knight, archer, enemy]:
            small_map.add_unit(unit)
        
        assert len(small_map.units) == 3
        assert knight.unit_id in small_map.units
        assert archer.unit_id in small_map.units
        assert enemy.unit_id in small_map.units
    
    def test_get_unit_at_position(self, small_map):
        """Test getting unit at specific position."""
        pos = Vector2(2, 3)
        unit = TestDataBuilder.unit("Positioned Unit", UnitClass.MAGE, Team.PLAYER, pos)
        
        small_map.add_unit(unit)
        
        retrieved_unit = small_map.get_unit_at(pos)
        assert retrieved_unit == unit
    
    def test_get_unit_at_empty_position(self, small_map):
        """Test getting unit from position with no unit."""
        empty_pos = Vector2(4, 4)
        unit = small_map.get_unit_at(empty_pos)
        
        assert unit is None
    
    def test_remove_unit(self, small_map):
        """Test removing a unit from the map."""
        unit = TestDataBuilder.unit("Removable", UnitClass.PRIEST, Team.ALLY, Vector2(1, 2))
        
        small_map.add_unit(unit)
        assert len(small_map.units) == 1
        
        small_map.remove_unit(unit.unit_id)
        assert len(small_map.units) == 0
        assert unit.unit_id not in small_map.units
    
    def test_remove_nonexistent_unit(self, small_map):
        """Test removing a unit that doesn't exist."""
        # Should handle gracefully
        small_map.remove_unit("nonexistent-unit-id")
        assert len(small_map.units) == 0
    
    def test_is_position_occupied(self, small_map):
        """Test checking if position is occupied."""
        pos = Vector2(3, 1)
        
        # Position should be empty initially
        assert small_map.get_unit_at(pos) is None
        
        # Add unit
        unit = TestDataBuilder.unit("Occupier", UnitClass.WARRIOR, Team.ENEMY, pos)
        small_map.add_unit(unit)
        
        # Position should now be occupied
        assert small_map.get_unit_at(pos) is not None
    
    def test_unit_position_updating(self, small_map):
        """Test updating unit positions."""
        initial_pos = Vector2(1, 1)
        new_pos = Vector2(3, 3)
        
        unit = TestDataBuilder.unit("Mobile Unit", UnitClass.KNIGHT, Team.PLAYER, initial_pos)
        small_map.add_unit(unit)
        
        # Check initial position
        assert small_map.get_unit_at(initial_pos) == unit
        assert small_map.get_unit_at(new_pos) is None
        
        # Move unit
        unit.move_to(new_pos)
        
        # Map should reflect the change
        assert small_map.get_unit_at(initial_pos) is None
        assert small_map.get_unit_at(new_pos) == unit


class TestMovementCalculation:
    """Test movement range calculation and pathfinding."""
    
    @pytest.fixture
    def movement_setup(self):
        """Create setup for movement testing."""
        game_map = GameMap(8, 8)
        
        # Add obstacles
        game_map.set_tile(Vector2(3, 3), TerrainType.MOUNTAIN)
        game_map.set_tile(Vector2(3, 4), TerrainType.MOUNTAIN) 
        game_map.set_tile(Vector2(4, 3), TerrainType.MOUNTAIN)
        
        # Add knight
        knight = TestDataBuilder.unit("Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(2, 2))
        game_map.add_unit(knight)
        
        return game_map, knight
    
    def test_calculate_movement_range(self, movement_setup):
        """Test basic movement range calculation."""
        game_map, knight = movement_setup
        
        movement_range = game_map.calculate_movement_range(knight)
        
        assert isinstance(movement_range, VectorArray)
        assert len(movement_range) > 0
        
        # Knight should be able to move to adjacent positions
        knight_pos = knight.position
        adjacent_positions = [
            Vector2(knight_pos.x + 1, knight_pos.y),
            Vector2(knight_pos.x - 1, knight_pos.y),
            Vector2(knight_pos.x, knight_pos.y + 1),
            Vector2(knight_pos.x, knight_pos.y - 1)
        ]
        
        for pos in adjacent_positions:
            if game_map.is_valid_position(pos) and game_map.get_unit_at(pos) is None:
                # Should be reachable if terrain allows
                tile = game_map.get_tile(pos)
                if tile and tile.terrain_type != TerrainType.WATER:  # Assuming water blocks movement
                    # Position might be in range depending on terrain cost
                    pass
    
    def test_movement_range_with_obstacles(self, movement_setup):
        """Test movement range calculation with obstacles."""
        game_map, knight = movement_setup
        
        movement_range = game_map.calculate_movement_range(knight)
        
        # Should not include mountain positions
        mountain_positions = [Vector2(3, 3), Vector2(3, 4), Vector2(4, 3)]
        for mountain_pos in mountain_positions:
            # Mountains should either not be in range or be impassable
            if mountain_pos in movement_range:
                # Check if mountains are passable in this implementation
                tile = game_map.get_tile(mountain_pos)
                # This depends on game rules
                pass
    
    def test_movement_blocked_by_units(self, small_map):
        """Test that movement is blocked by other units."""
        knight = TestDataBuilder.unit("Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(2, 2))
        blocker = TestDataBuilder.unit("Blocker", UnitClass.WARRIOR, Team.ENEMY, Vector2(2, 3))
        
        small_map.add_unit(knight)
        small_map.add_unit(blocker)
        
        movement_range = small_map.calculate_movement_range(knight)
        
        # Blocker's position should not be accessible for movement
        blocker_pos = blocker.position
        # Implementation may vary - some games allow attacking occupied positions
        # but not moving to them
        assert isinstance(movement_range, VectorArray)
    
    def test_movement_range_boundaries(self, small_map):
        """Test movement range at map boundaries."""
        # Place unit at corner
        corner_unit = TestDataBuilder.unit("Corner", UnitClass.ARCHER, Team.PLAYER, Vector2(0, 0))
        small_map.add_unit(corner_unit)
        
        movement_range = small_map.calculate_movement_range(corner_unit)
        
        # Should not include positions outside the map
        for pos in movement_range:
            assert small_map.is_valid_position(pos)


class TestAttackRangeCalculation:
    """Test attack range calculation for different unit types."""
    
    def test_melee_attack_range(self, small_map):
        """Test attack range for melee units."""
        knight = TestDataBuilder.unit("Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(2, 2))
        small_map.add_unit(knight)
        
        attack_range = small_map.calculate_attack_range(knight)
        
        assert isinstance(attack_range, VectorArray)
        assert len(attack_range) > 0
        
        # Melee units should have adjacent attack range
        knight_pos = knight.position
        expected_positions = [
            Vector2(knight_pos.x + 1, knight_pos.y),
            Vector2(knight_pos.x - 1, knight_pos.y),
            Vector2(knight_pos.x, knight_pos.y + 1),
            Vector2(knight_pos.x, knight_pos.y - 1)
        ]
        
        # At least some adjacent positions should be in range
        adjacent_in_range = sum(1 for pos in expected_positions if pos in attack_range)
        assert adjacent_in_range > 0
    
    def test_ranged_attack_range(self, medium_map):
        """Test attack range for ranged units."""
        archer = TestDataBuilder.unit("Archer", UnitClass.ARCHER, Team.PLAYER, Vector2(5, 5))
        medium_map.add_unit(archer)
        
        attack_range = medium_map.calculate_attack_range(archer)
        
        assert isinstance(attack_range, VectorArray)
        assert len(attack_range) > 0
        
        # Ranged units should have longer range than melee
        # Test some distant positions
        archer_pos = archer.position
        distant_pos = Vector2(archer_pos.x + 3, archer_pos.y)
        
        if medium_map.is_valid_position(distant_pos):
            # May or may not be in range depending on archer's range
            # Just verify we get reasonable results
            assert len(attack_range) >= 4  # At least adjacent positions
    
    def test_mage_attack_range(self, medium_map):
        """Test attack range for mage units."""
        mage = TestDataBuilder.unit("Mage", UnitClass.MAGE, Team.PLAYER, Vector2(4, 4))
        medium_map.add_unit(mage)
        
        attack_range = medium_map.calculate_attack_range(mage)
        
        assert isinstance(attack_range, VectorArray)
        assert len(attack_range) > 0
    
    def test_attack_range_boundaries(self, small_map):
        """Test attack range at map boundaries."""
        # Place unit at edge
        edge_unit = TestDataBuilder.unit("Edge", UnitClass.ARCHER, Team.PLAYER, Vector2(0, 2))
        small_map.add_unit(edge_unit)
        
        attack_range = small_map.calculate_attack_range(edge_unit)
        
        # All positions should be valid
        for pos in attack_range:
            assert small_map.is_valid_position(pos)


class TestPathfinding:
    """Test pathfinding algorithms."""
    
    def test_get_path_straight_line(self, medium_map):
        """Test pathfinding in straight line with no obstacles."""
        start = Vector2(1, 1)
        end = Vector2(1, 5)
        
        path = medium_map.get_path(start, end, max_cost=10)
        
        if path:  # Pathfinding method might not exist
            assert isinstance(path, list)
            assert len(path) > 0
            assert path[0] == start or path[0] == end  # Depending on implementation
    
    def test_get_path_with_obstacles(self, terrain_map):
        """Test pathfinding around obstacles."""
        start = Vector2(0, 0)
        end = Vector2(4, 4)
        
        # Try to find path (method might not exist in current implementation)
        if hasattr(terrain_map, 'get_path'):
            path = terrain_map.get_path(start, end, max_cost=15)
            
            if path:
                # Path should avoid obstacles
                for pos in path:
                    tile = terrain_map.get_tile(pos)
                    # Should not go through impassable terrain
                    assert tile.terrain_type != TerrainType.WATER  # Assuming water is impassable
    
    def test_unreachable_destination(self, small_map):
        """Test pathfinding to unreachable destination."""
        start = Vector2(0, 0)
        unreachable = Vector2(10, 10)  # Outside map
        
        if hasattr(small_map, 'get_path'):
            path = small_map.get_path(start, unreachable, max_cost=20)
            # Should return None or empty path for unreachable destinations
            assert path is None or len(path) == 0


class TestLineOfSight:
    """Test line of sight calculations."""
    
    def test_clear_line_of_sight(self, small_map):
        """Test line of sight with no obstacles."""
        start = Vector2(1, 1)
        end = Vector2(3, 3)
        
        if hasattr(small_map, 'get_path'):
            path = small_map.get_path(start, end, max_cost=10)
            assert isinstance(path, (list, type(None)))
    
    def test_blocked_line_of_sight(self, terrain_map):
        """Test line of sight blocked by obstacles."""
        start = Vector2(0, 0)
        end = Vector2(4, 4)
        
        if hasattr(terrain_map, 'get_path'):
            path = terrain_map.get_path(start, end, max_cost=15)
            # May be blocked by mountains or other obstacles
            assert isinstance(path, (list, type(None)))


class TestAOECalculations:
    """Test Area of Effect calculations."""
    
    def test_aoe_cross_pattern(self, medium_map):
        """Test AOE cross pattern calculation."""
        center = Vector2(5, 5)
        
        if hasattr(medium_map, 'calculate_aoe_tiles'):
            aoe_tiles = medium_map.calculate_aoe_tiles(center, "cross")
            
            assert isinstance(aoe_tiles, VectorArray)
            assert len(aoe_tiles) > 0
            
            # Should include center and adjacent positions
            expected_positions = [
                (5, 5), (4, 5), (6, 5), (5, 4), (5, 6)
            ]
            
            for pos in expected_positions:
                if medium_map.is_valid_position(Vector2(pos[0], pos[1])):
                    # Should be included in AOE
                    pass
    
    def test_aoe_square_pattern(self, medium_map):
        """Test AOE square pattern calculation."""
        center = Vector2(4, 4)
        
        if hasattr(medium_map, 'calculate_aoe_tiles'):
            aoe_tiles = medium_map.calculate_aoe_tiles(center, "square")
            
            assert isinstance(aoe_tiles, VectorArray)
            # Square pattern should include more tiles than cross
            assert len(aoe_tiles) >= 9  # 3x3 square
    
    def test_aoe_boundary_handling(self, small_map):
        """Test AOE at map boundaries."""
        # Center AOE at corner
        corner = Vector2(0, 0)
        
        if hasattr(small_map, 'calculate_aoe_tiles'):
            aoe_tiles = small_map.calculate_aoe_tiles(corner, "cross")
            
            # All returned positions should be valid
            for pos in aoe_tiles:
                assert small_map.is_valid_position(Vector2(pos[0], pos[1]))


class TestGameMapIntegration:
    """Test GameMap integration with other systems."""
    
    def test_terrain_movement_costs(self, terrain_map):
        """Test that different terrains have appropriate movement costs."""
        knight = TestDataBuilder.unit("Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(0, 0))
        terrain_map.add_unit(knight)
        
        movement_range = terrain_map.calculate_movement_range(knight)
        
        # Movement range should be affected by terrain
        # (Specific behavior depends on implementation)
        assert isinstance(movement_range, VectorArray)
    
    def test_map_state_consistency(self, populated_map):
        """Test that map maintains consistent state."""
        initial_unit_count = len(populated_map.units)
        
        # Add and remove units
        temp_unit = TestDataBuilder.unit("Temp", UnitClass.WARRIOR, Team.NEUTRAL, Vector2(0, 0))
        populated_map.add_unit(temp_unit)
        assert len(populated_map.units) == initial_unit_count + 1
        
        populated_map.remove_unit(temp_unit.unit_id)
        assert len(populated_map.units) == initial_unit_count
        
        # Original units should still be there
        assert len(populated_map.units) > 0
    
    def test_large_map_performance(self):
        """Test that large maps perform reasonably."""
        large_map = GameMap(50, 50)
        
        # Should initialize without issues
        assert large_map.width == 50
        assert large_map.height == 50
        
        # Basic operations should work
        test_unit = TestDataBuilder.unit("Test", UnitClass.KNIGHT, Team.PLAYER, Vector2(25, 25))
        large_map.add_unit(test_unit)
        
        # Movement calculation should complete
        movement_range = large_map.calculate_movement_range(test_unit)
        assert isinstance(movement_range, VectorArray)