"""
Shared fixtures and test utilities for the grimdark test suite.

This module provides common test fixtures, mock objects, and utilities
that can be used across all test modules.
"""
import sys
import os
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock
from typing import Optional

from src.core.data_structures import Vector2
from src.core.game_enums import Team, UnitClass, TerrainType
from src.core.game_state import GameState, GamePhase
from src.game.map import GameMap
from src.game.unit import Unit
from src.game.scenario import Scenario
from src.game.scenario_loader import ScenarioLoader


@pytest.fixture
def game_state() -> GameState:
    """Create a basic game state for testing."""
    return GameState(phase=GamePhase.BATTLE)


@pytest.fixture
def small_map() -> GameMap:
    """Create a small 5x5 test map."""
    return GameMap(5, 5)


@pytest.fixture
def medium_map() -> GameMap:
    """Create a medium 10x10 test map."""
    return GameMap(10, 10)


@pytest.fixture
def large_map() -> GameMap:
    """Create a large 20x20 test map."""
    return GameMap(20, 20)


@pytest.fixture
def player_knight(small_map) -> Unit:
    """Create a player knight unit at (1, 1)."""
    unit = Unit("Test Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(1, 1))
    small_map.add_unit(unit)
    return unit


@pytest.fixture
def enemy_warrior(small_map) -> Unit:
    """Create an enemy warrior unit at (3, 3)."""
    unit = Unit("Test Warrior", UnitClass.WARRIOR, Team.ENEMY, Vector2(3, 3))
    small_map.add_unit(unit)
    return unit


@pytest.fixture
def player_mage(small_map) -> Unit:
    """Create a player mage unit at (2, 2)."""
    unit = Unit("Test Mage", UnitClass.MAGE, Team.PLAYER, Vector2(2, 2))
    small_map.add_unit(unit)
    return unit


@pytest.fixture
def populated_map(medium_map) -> GameMap:
    """Create a map with various units for complex testing."""
    # Player units
    knight = Unit("Player Knight", UnitClass.KNIGHT, Team.PLAYER, Vector2(2, 2))
    archer = Unit("Player Archer", UnitClass.ARCHER, Team.PLAYER, Vector2(3, 1))
    mage = Unit("Player Mage", UnitClass.MAGE, Team.PLAYER, Vector2(1, 3))
    
    # Enemy units
    enemy_warrior = Unit("Enemy Warrior", UnitClass.WARRIOR, Team.ENEMY, Vector2(7, 7))
    enemy_archer = Unit("Enemy Archer", UnitClass.ARCHER, Team.ENEMY, Vector2(8, 6))
    
    # Add all units to the map
    for unit in [knight, archer, mage, enemy_warrior, enemy_archer]:
        medium_map.add_unit(unit)
    
    return medium_map


@pytest.fixture
def terrain_map(small_map) -> GameMap:
    """Create a map with various terrain types for pathfinding tests."""
        
    # Add forest tiles
    small_map.set_tile(Vector2(1, 2), TerrainType.FOREST)
    small_map.set_tile(Vector2(2, 2), TerrainType.FOREST)
    
    # Add mountain tiles  
    small_map.set_tile(Vector2(3, 1), TerrainType.MOUNTAIN)
    small_map.set_tile(Vector2(3, 2), TerrainType.MOUNTAIN)
    
    # Add water tiles
    small_map.set_tile(Vector2(4, 3), TerrainType.WATER)
    small_map.set_tile(Vector2(4, 4), TerrainType.WATER)
    
    return small_map


@pytest.fixture
def mock_renderer():
    """Create a mock renderer for testing."""
    renderer = Mock()
    renderer.initialize = Mock()
    renderer.render_frame = Mock()
    renderer.get_input_events = Mock(return_value=[])
    renderer.cleanup = Mock()
    return renderer


@pytest.fixture
def mock_event_emitter():
    """Create a mock event emitter for testing."""
    return Mock()


@pytest.fixture
def tutorial_scenario() -> Scenario:
    """Load the tutorial scenario for testing."""
    return ScenarioLoader.load_from_file("assets/scenarios/tutorial.yaml")


class TestDataBuilder:
    """Builder class for creating test data objects."""
    
    @staticmethod
    def unit(
        name: str = "Test Unit",
        unit_class: UnitClass = UnitClass.KNIGHT,
        team: Team = Team.PLAYER,
        position: Vector2 = Vector2(1, 1),
        hp: Optional[int] = None
    ) -> Unit:
        """Create a unit with specified parameters."""
        unit = Unit(name, unit_class, team, position)
        if hp is not None:
            unit.hp_current = hp
        return unit
    
    @staticmethod
    def vector2(x: int = 0, y: int = 0) -> Vector2:
        """Create a Vector2 with specified coordinates."""
        return Vector2(x, y)


@pytest.fixture
def builder():
    """Provide the test data builder."""
    return TestDataBuilder


# Performance test configuration
@pytest.fixture(scope="session")
def benchmark_config():
    """Configuration for performance benchmarks."""
    return {
        "min_rounds": 5,
        "max_time": 1.0,
        "warmup": True,
        "warmup_iterations": 3
    }