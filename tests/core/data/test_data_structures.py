"""
Unit tests for core data structures.

Tests Vector2, GameState, and other fundamental data structures used
throughout the timeline-based game architecture.
"""

import pytest
from src.core.data.data_structures import Vector2
from src.core.engine.game_state import GamePhase, BattlePhase, CursorState


class TestVector2:
    """Test Vector2 functionality."""

    def test_vector2_creation(self):
        """Test basic Vector2 creation."""
        v = Vector2(3, 4)
        assert v.y == 3
        assert v.x == 4

    def test_vector2_addition(self):
        """Test vector addition."""
        v1 = Vector2(1, 2)
        v2 = Vector2(3, 4)
        result = v1 + v2
        
        assert result.y == 4
        assert result.x == 6

    def test_vector2_subtraction(self):
        """Test vector subtraction."""
        v1 = Vector2(5, 7)
        v2 = Vector2(2, 3)
        result = v1 - v2
        
        assert result.y == 3
        assert result.x == 4

    def test_vector2_scalar_multiplication(self):
        """Test scalar multiplication."""
        v = Vector2(2, 3)
        result = v * 3
        
        assert result.y == 6
        assert result.x == 9

    def test_vector2_floor_division(self):
        """Test integer division."""
        v = Vector2(7, 9)
        result = v // 3
        
        assert result.y == 2
        assert result.x == 3

    def test_vector2_equality(self):
        """Test vector equality comparison."""
        v1 = Vector2(2, 3)
        v2 = Vector2(2, 3)
        v3 = Vector2(3, 2)
        
        assert v1 == v2
        assert v1 != v3
        assert v1 != "not a vector"

    def test_vector2_hash(self):
        """Test vector hashing for use in sets/dicts."""
        v1 = Vector2(2, 3)
        v2 = Vector2(2, 3)
        v3 = Vector2(3, 2)
        
        # Equal vectors should have same hash
        assert hash(v1) == hash(v2)
        # Different vectors may have different hashes
        vector_set = {v1, v2, v3}
        assert len(vector_set) == 2  # v1 and v2 are same, v3 is different

    def test_vector2_iteration(self):
        """Test vector iteration (y, x order)."""
        v = Vector2(2, 3)
        y, x = v
        
        assert y == 2
        assert x == 3

    def test_vector2_indexing(self):
        """Test indexed access."""
        v = Vector2(2, 3)
        
        assert v[0] == 2  # y coordinate
        assert v[1] == 3  # x coordinate
        
        with pytest.raises(IndexError):
            _ = v[2]

    def test_vector2_string_representation(self):
        """Test string representation."""
        v = Vector2(2, 3)
        assert str(v) == "Vector2(2, 3)"
        assert repr(v) == "Vector2(2, 3)"

    def test_euclidean_distance(self):
        """Test Euclidean distance calculation."""
        v1 = Vector2(0, 0)
        v2 = Vector2(3, 4)
        
        distance = v1.distance_to(v2)
        assert distance == 5.0  # 3-4-5 triangle

    def test_manhattan_distance(self):
        """Test Manhattan distance calculation."""
        v1 = Vector2(1, 1)
        v2 = Vector2(4, 5)
        
        distance = v1.manhattan_distance_to(v2)
        assert distance == 7  # |4-1| + |5-1| = 3 + 4 = 7

    def test_magnitude(self):
        """Test vector magnitude calculation."""
        v = Vector2(3, 4)
        assert v.magnitude() == 5.0

    def test_zero_vector(self):
        """Test zero vector behavior."""
        zero = Vector2(0, 0)
        v = Vector2(5, 3)
        
        assert zero + v == v
        assert v - v == zero
        assert zero.magnitude() == 0.0
        assert zero.manhattan_distance_to(v) == 8


class TestGamePhase:
    """Test GamePhase enum."""

    def test_game_phase_values(self):
        """Test that all expected game phases exist."""
        assert GamePhase.MAIN_MENU
        assert GamePhase.BATTLE
        assert GamePhase.CUTSCENE
        assert GamePhase.PAUSE
        assert GamePhase.GAME_OVER


class TestBattlePhase:
    """Test BattlePhase enum."""

    def test_battle_phase_values(self):
        """Test that all expected battle phases exist."""
        assert BattlePhase.TIMELINE_PROCESSING
        assert BattlePhase.UNIT_SELECTION
        assert BattlePhase.UNIT_MOVING
        assert BattlePhase.UNIT_ACTION_SELECTION
        assert BattlePhase.ACTION_TARGETING
        assert BattlePhase.ACTION_EXECUTION
        assert BattlePhase.INTERRUPT_RESOLUTION
        assert BattlePhase.INSPECT


class TestCursorState:
    """Test CursorState functionality."""

    def test_cursor_state_creation(self):
        """Test cursor state initialization."""
        cursor = CursorState()
        
        # Should default to (0, 0)
        assert cursor.position == Vector2(0, 0)

    def test_cursor_state_with_position(self):
        """Test cursor state with custom position."""
        position = Vector2(5, 7)
        cursor = CursorState(position=position)
        
        assert cursor.position == position


class TestGameState:
    """Test GameState functionality."""

    def test_game_state_creation(self, game_state):
        """Test game state initialization."""
        assert game_state.phase == GamePhase.BATTLE
        assert hasattr(game_state, 'cursor')
        assert hasattr(game_state, 'battle')
        assert hasattr(game_state, 'ui')

    def test_game_state_phase_change(self, game_state):
        """Test changing game phase."""
        original_phase = game_state.phase
        game_state.phase = GamePhase.PAUSE
        
        assert game_state.phase == GamePhase.PAUSE
        assert game_state.phase != original_phase

    def test_game_state_cursor_access(self, game_state):
        """Test accessing cursor state."""
        # Should have a cursor state
        assert game_state.cursor is not None
        assert isinstance(game_state.cursor.position, Vector2)

    def test_game_state_battle_access(self, game_state):
        """Test accessing battle state."""
        # Should have a battle state
        assert game_state.battle is not None
        assert hasattr(game_state.battle, 'phase')

    def test_game_state_ui_access(self, game_state):
        """Test accessing UI state."""
        # Should have a UI state
        assert game_state.ui is not None


class TestVectorOperationsEdgeCases:
    """Test edge cases for Vector2 operations."""

    def test_negative_coordinates(self):
        """Test vectors with negative coordinates."""
        v1 = Vector2(-2, -3)
        v2 = Vector2(1, 4)
        
        result = v1 + v2
        assert result == Vector2(-1, 1)

    def test_large_coordinates(self):
        """Test vectors with large coordinates."""
        v1 = Vector2(1000000, 2000000)
        v2 = Vector2(500000, -1000000)
        
        result = v1 + v2
        assert result == Vector2(1500000, 1000000)

    def test_zero_scalar_multiplication(self):
        """Test multiplication by zero."""
        v = Vector2(5, 3)
        result = v * 0
        
        assert result == Vector2(0, 0)

    def test_distance_to_self(self):
        """Test distance from vector to itself."""
        v = Vector2(5, 3)
        
        assert v.distance_to(v) == 0.0
        assert v.manhattan_distance_to(v) == 0

    def test_symmetric_distance(self):
        """Test that distance is symmetric."""
        v1 = Vector2(1, 2)
        v2 = Vector2(4, 6)
        
        assert v1.distance_to(v2) == v2.distance_to(v1)
        assert v1.manhattan_distance_to(v2) == v2.manhattan_distance_to(v1)