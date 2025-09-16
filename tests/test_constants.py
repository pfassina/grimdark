"""
Test constants and configuration for the grimdark test suite.

This module defines constants, expected values, and configuration
used across multiple test modules.
"""

# Map dimensions commonly used in tests
SMALL_MAP_SIZE = (5, 5)
MEDIUM_MAP_SIZE = (10, 10)
LARGE_MAP_SIZE = (20, 20)

# Common test positions
DEFAULT_PLAYER_POS = (1, 1)
DEFAULT_ENEMY_POS = (3, 3)
DEFAULT_CURSOR_POS = (0, 0)

# Unit test data
DEFAULT_KNIGHT_HP = 100
DEFAULT_ARCHER_HP = 80
DEFAULT_MAGE_HP = 60
DEFAULT_WARRIOR_HP = 90

# Combat test values
DEFAULT_KNIGHT_ATTACK = 25
DEFAULT_ARCHER_ATTACK = 20
DEFAULT_MAGE_ATTACK = 30

# Movement ranges (from unit templates)
KNIGHT_MOVE_RANGE = 3
ARCHER_MOVE_RANGE = 2
MAGE_MOVE_RANGE = 2

# Attack ranges
KNIGHT_ATTACK_RANGE = 1
ARCHER_ATTACK_RANGE = 3
MAGE_ATTACK_RANGE = 2

# Terrain movement costs
PLAIN_MOVE_COST = 1
FOREST_MOVE_COST = 2
MOUNTAIN_MOVE_COST = 3

# Expected AOE patterns
CROSS_PATTERN_OFFSETS = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
SQUARE_PATTERN_OFFSETS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 0), (0, 1),
    (1, -1), (1, 0), (1, 1)
]

# Performance test thresholds
MAX_PATHFINDING_TIME_MS = 50  # Maximum time for pathfinding operations
MAX_COMBAT_CALC_TIME_MS = 10  # Maximum time for combat calculations
MAX_RENDER_BUILD_TIME_MS = 20  # Maximum time for render context building

# Test file paths
TEST_SCENARIOS_DIR = "tests/test_data/scenarios"
TEST_MAPS_DIR = "tests/test_data/maps"