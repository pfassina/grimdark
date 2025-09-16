"""
Test utilities and helper functions for the grimdark test suite.

This module provides utility functions, assertion helpers, and test data
generators that make testing more convenient and consistent.
"""
import tempfile
import os
from typing import List, Tuple, Optional
from unittest.mock import Mock

from src.core.data_structures import Vector2, VectorArray
from src.core.game_enums import Team, UnitClass, TerrainType
from src.game.map import GameMap
from src.game.unit import Unit


class MapTestBuilder:
    """Builder for creating test maps with specific layouts."""
    
    def __init__(self, width: int = 10, height: int = 10):
        self.map = GameMap(width, height)
        self.units: List[Unit] = []
    
    def with_terrain(self, positions: List[Tuple[int, int]], terrain_type: TerrainType) -> "MapTestBuilder":
        """Add terrain of specified type at given positions."""
        for x, y in positions:
            self.map.set_tile(Vector2(x, y), terrain_type)
        return self
    
    def with_forest(self, positions: List[Tuple[int, int]]) -> "MapTestBuilder":
        """Add forest terrain at specified positions."""
        return self.with_terrain(positions, TerrainType.FOREST)
    
    def with_mountains(self, positions: List[Tuple[int, int]]) -> "MapTestBuilder":
        """Add mountain terrain at specified positions."""
        return self.with_terrain(positions, TerrainType.MOUNTAIN)
    
    def with_water(self, positions: List[Tuple[int, int]]) -> "MapTestBuilder":
        """Add water terrain at specified positions."""
        return self.with_terrain(positions, TerrainType.WATER)
    
    def with_unit(
        self, 
        name: str, 
        unit_class: UnitClass, 
        team: Team, 
        x: int, 
        y: int,
        hp: Optional[int] = None
    ) -> "MapTestBuilder":
        """Add a unit to the map."""
        unit = Unit(name, unit_class, team, Vector2(y, x))
        if hp is not None:
            unit.hp_current = hp
        self.map.add_unit(unit)
        self.units.append(unit)
        return self
    
    def with_player_knight(self, name: str = "Knight", x: int = 1, y: int = 1) -> "MapTestBuilder":
        """Add a player knight at specified position."""
        return self.with_unit(name, UnitClass.KNIGHT, Team.PLAYER, x, y)
    
    def with_enemy_warrior(self, name: str = "Warrior", x: int = 5, y: int = 5) -> "MapTestBuilder":
        """Add an enemy warrior at specified position."""
        return self.with_unit(name, UnitClass.WARRIOR, Team.ENEMY, x, y)
    
    def with_walls(self, positions: List[Tuple[int, int]]) -> "MapTestBuilder":
        """Add walls (mountains) to create barriers."""
        return self.with_mountains(positions)
    
    def build(self) -> GameMap:
        """Build and return the configured map."""
        return self.map


class ScenarioTestData:
    """Provides test data for scenario testing."""
    
    @staticmethod
    def create_minimal_scenario_yaml() -> str:
        """Create minimal YAML for testing scenario loading."""
        return """
name: "Test Scenario"
description: "A test scenario"
author: "Test Suite"
map:
  source: "test_map"
units:
  - id: "player_unit"
    name: "Test Hero"
    class: "knight"
    team: "player"
  - id: "enemy_unit"
    name: "Test Enemy"
    class: "warrior"
    team: "enemy"
placements:
  - unit: "player_unit"
    at: [1, 1]
  - unit: "enemy_unit"
    at: [3, 3]
objectives:
  victory:
    - type: "defeat_all_enemies"
  defeat:
    - type: "all_units_defeated"
        """
    
    @staticmethod
    def create_temp_scenario_file(yaml_content: str) -> str:
        """Create a temporary scenario file and return its path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            return f.name


class AssertionHelpers:
    """Helper methods for common test assertions."""
    
    @staticmethod
    def assert_vector2_equal(actual: Vector2, expected: Vector2, msg: str = ""):
        """Assert two Vector2 objects are equal."""
        assert actual.x == expected.x and actual.y == expected.y, \
            f"Expected Vector2({expected.x}, {expected.y}), got Vector2({actual.x}, {actual.y}). {msg}"
    
    @staticmethod
    def assert_positions_equal(actual: Tuple[int, int], expected: Tuple[int, int], msg: str = ""):
        """Assert two position tuples are equal."""
        assert actual == expected, f"Expected position {expected}, got {actual}. {msg}"
    
    @staticmethod
    def assert_unit_at_position(unit: Unit, x: int, y: int):
        """Assert a unit is at the expected position."""
        AssertionHelpers.assert_positions_equal((unit.position.x, unit.position.y), (x, y),
                                               f"Unit {unit.name} not at expected position")
    
    @staticmethod
    def assert_tiles_accessible(game_map: GameMap, positions: List[Tuple[int, int]]):
        """Assert that all given positions are accessible on the map."""
        for x, y in positions:
            pos = Vector2(x, y)
            assert game_map.is_valid_position(pos), f"Position ({x}, {y}) should be valid"
            tile = game_map.get_tile(pos)
            assert tile is not None, f"Tile at ({x}, {y}) should exist"
    
    @staticmethod
    def assert_vector_array_contains(vector_array: VectorArray, positions: List[Tuple[int, int]]):
        """Assert that a VectorArray contains all specified positions."""
        array_positions = {(v.x, v.y) for v in vector_array}
        expected_positions = set(positions)
        assert expected_positions.issubset(array_positions), \
            f"Expected positions {expected_positions} not all found in {array_positions}"


class MockFactory:
    """Factory for creating common mock objects."""
    
    @staticmethod
    def create_mock_renderer():
        """Create a mock renderer with all required methods."""
        renderer = Mock()
        renderer.initialize.return_value = None
        renderer.start.return_value = None
        renderer.stop.return_value = None
        renderer.clear.return_value = None
        renderer.present.return_value = None
        renderer.render_frame.return_value = None
        renderer.get_input_events.return_value = []
        renderer.get_screen_size.return_value = (80, 24)
        renderer.cleanup.return_value = None
        return renderer
    
    @staticmethod
    def create_mock_event_emitter():
        """Create a mock event emitter."""
        emitter = Mock()
        emitter.emit.return_value = None
        return emitter
    
    @staticmethod
    def create_mock_game_state():
        """Create a mock game state."""
        from src.core.game_state import GameState, GamePhase, BattlePhase
        
        state = Mock(spec=GameState)
        state.phase = GamePhase.BATTLE
        state.battle.phase = BattlePhase.UNIT_SELECTION
        state.battle.cursor = Vector2(0, 0)
        state.battle.selected_unit = None
        return state


def create_combat_scenario(map_size: Tuple[int, int] = (5, 5)) -> Tuple[GameMap, Unit, Unit]:
    """
    Create a basic combat scenario with two opposing units.
    
    Returns:
        Tuple of (map, player_unit, enemy_unit)
    """
    width, height = map_size
    game_map = GameMap(width, height)
    
    player_unit = Unit("Player", UnitClass.KNIGHT, Team.PLAYER, Vector2(1, 1))
    enemy_unit = Unit("Enemy", UnitClass.WARRIOR, Team.ENEMY, Vector2(height-2, width-2))
    
    game_map.add_unit(player_unit)
    game_map.add_unit(enemy_unit)
    
    return game_map, player_unit, enemy_unit


def cleanup_temp_files(*file_paths: str):
    """Clean up temporary files created during testing."""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            pass  # Ignore cleanup errors