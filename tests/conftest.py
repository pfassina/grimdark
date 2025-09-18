"""
Basic test fixtures for the grimdark test suite.

Provides simple fixtures for testing the timeline-based game architecture.
"""

import sys
import os
import pytest

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.data.data_structures import Vector2
from src.core.events.event_manager import EventManager
from src.core.engine.game_state import GameState, GamePhase
from src.core.engine.timeline import Timeline
from src.game.map import GameMap


@pytest.fixture
def game_state():
    """Create a fresh game state for testing."""
    return GameState(phase=GamePhase.BATTLE)


@pytest.fixture
def event_manager():
    """Create an event manager for testing."""
    return EventManager(enable_debug_logging=False)


@pytest.fixture
def timeline():
    """Create a fresh timeline for testing."""
    return Timeline()


@pytest.fixture
def small_game_map():
    """Create a small 5x5 game map for testing."""
    return GameMap(width=5, height=5)


@pytest.fixture
def sample_vector():
    """Create a sample Vector2 for testing."""
    return Vector2(2, 3)


@pytest.fixture
def sample_positions():
    """Create a list of sample positions for testing."""
    return [
        Vector2(0, 0),
        Vector2(1, 1), 
        Vector2(2, 2),
        Vector2(3, 4)
    ]