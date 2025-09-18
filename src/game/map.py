import csv
import os
from collections import deque
from collections.abc import KeysView
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from ..core.data.data_structures import Vector2, VectorArray
from ..core.data.game_enums import Team, TerrainType
from ..core.tileset_loader import get_tileset_config
from .tile import Tile
from .entities.unit import Unit


class UnitCollection:
    """Compatibility wrapper for units that provides dict-like interface while using list storage."""

    def __init__(self, units: list[Unit], unit_id_to_index: dict[str, int]):
        self._units = units
        self._unit_id_to_index = unit_id_to_index

    def __len__(self) -> int:
        """Return number of units."""
        return len(self._units)

    def __contains__(self, unit_id: str) -> bool:
        """Check if unit ID exists."""
        return unit_id in self._unit_id_to_index

    def __getitem__(self, unit_id: str) -> Unit:
        """Get unit by ID."""
        if unit_id not in self._unit_id_to_index:
            raise KeyError(unit_id)
        index = self._unit_id_to_index[unit_id]
        return self._units[index]

    def keys(self) -> KeysView[str]:
        """Get all unit IDs."""
        return self._unit_id_to_index.keys()

    def values(self):
        """Get all units."""
        return iter(self._units)

    def __iter__(self):
        """Iterate over all units."""
        return iter(self._units)


@dataclass
class GameMap:
    width: int
    height: int
    tiles: np.ndarray = field(init=False)
    # Replace dict-based storage with indexed arrays for O(1) lookups
    _units: list[Unit] = field(default_factory=list)
    occupancy: np.ndarray = field(init=False)  # Stores unit indices (-1 for empty)
    unit_id_to_index: dict[str, int] = field(default_factory=dict)
    units: UnitCollection = field(init=False)

    def __post_init__(self):
        # Create structured array for efficient tile storage
        # Use optimal dtypes: uint8 for terrain (8 values), int8 for elevation (-128 to 127)
        tile_dtype = np.dtype([("terrain_type", np.uint8), ("elevation", np.int8)])

        self.tiles = np.zeros((self.height, self.width), dtype=tile_dtype)
        # Initialize all tiles to PLAIN terrain with 0 elevation
        self.tiles["terrain_type"] = TerrainType.PLAIN.value
        self.tiles["elevation"] = 0

        # Initialize occupancy array: -1 = empty, >=0 = unit index
        # Use int16 to support up to 32,767 units
        self.occupancy = np.full((self.height, self.width), -1, dtype=np.int16)

        # Initialize compatibility wrapper
        self.units = UnitCollection(self._units, self.unit_id_to_index)

    @classmethod
    def from_csv_layers(cls, map_directory: str) -> "GameMap":
        """Load a map from CSV layers and tileset configuration.

        Expected directory structure:
        map_directory/
        ├── ground.csv (required - base terrain)
        ├── walls.csv (optional - blocking structures)
        └── features.csv (optional - decorative elements)

        Layers are composited in order: ground -> walls -> features.
        Each higher layer overrides the terrain type if present.
        """
        map_dir = os.path.abspath(map_directory)
        ground_csv = os.path.join(map_dir, "ground.csv")
        walls_csv = os.path.join(map_dir, "walls.csv")
        features_csv = os.path.join(map_dir, "features.csv")

        if not os.path.exists(ground_csv):
            raise FileNotFoundError(f"Required ground.csv not found in {map_dir}")

        # Load ground layer (required)
        with open(ground_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            ground_data = [row for row in reader if row]  # Skip empty rows

        if not ground_data:
            raise ValueError("No data found in ground.csv")

        # Get dimensions from ground layer
        height = len(ground_data)
        width = len(ground_data[0]) if ground_data else 0

        # Create the map
        game_map = cls(width, height)

        # Load tileset configuration
        tileset_config = get_tileset_config()

        # Helper function to process a CSV layer
        def process_layer(csv_data, override_empty=False):
            for y, row in enumerate(csv_data):
                if y >= height:
                    break
                for x, cell in enumerate(row):
                    if x >= width:
                        break

                    # Skip empty cells (0 or empty string) unless override_empty is True
                    if not override_empty and (not cell or cell == "0"):
                        continue

                    try:
                        tile_id = int(cell)
                        if tile_id == 0 and not override_empty:
                            continue

                        tile_config = tileset_config.get_tile_config(tile_id)

                        if tile_config:
                            terrain_type_str = tile_config.get("terrain_type", "plain")
                            # Convert string terrain type to enum
                            terrain_type = TerrainType[terrain_type_str.upper()]
                        else:
                            # Default to plain terrain if tile ID not found
                            terrain_type = TerrainType.PLAIN

                        game_map.set_tile(Vector2(y, x), terrain_type)
                    except (ValueError, IndexError, KeyError):
                        # Only set to plain if this is the ground layer
                        if override_empty:
                            game_map.set_tile(Vector2(y, x), TerrainType.PLAIN)

        # Process ground layer (required, fills all cells)
        process_layer(ground_data, override_empty=True)

        # Process walls layer if it exists
        if os.path.exists(walls_csv):
            with open(walls_csv, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                walls_data = [row for row in reader if row]
            if walls_data:
                process_layer(walls_data, override_empty=False)

        # Process features layer if it exists
        if os.path.exists(features_csv):
            with open(features_csv, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                features_data = [row for row in reader if row]
            if features_data:
                process_layer(features_data, override_empty=False)

        return game_map

    def get_tile_data(self, position: Vector2) -> Optional[tuple[TerrainType, int]]:
        """Get terrain type and elevation at position directly from structured array."""
        if self.is_valid_position(position):
            tile_data = self.tiles[position.y, position.x]
            terrain_type = TerrainType(tile_data["terrain_type"])
            elevation = int(tile_data["elevation"])
            return (terrain_type, elevation)
        return None

    def get_tile(self, position: Vector2) -> Tile:
        """Get tile at position. Position must be valid (call is_valid_position first)."""
        assert self.is_valid_position(position), f"Invalid position: {position}"
        tile_data = self.tiles[position.y, position.x]
        terrain_type = TerrainType(tile_data["terrain_type"])
        elevation = int(tile_data["elevation"])
        return Tile(position, terrain_type, elevation)

    def set_tile(
        self, position: Vector2, terrain_type: TerrainType, elevation: int = 0
    ):
        """Set tile at position using structured array for efficiency."""
        if self.is_valid_position(position):
            self.tiles[position.y, position.x] = (terrain_type.value, elevation)

    def get_terrain_type(self, position: Vector2) -> Optional[TerrainType]:
        """Get terrain type directly from structured array (faster than get_tile)."""
        if self.is_valid_position(position):
            terrain_value = self.tiles[position.y, position.x]["terrain_type"]
            return TerrainType(terrain_value)
        return None

    def get_elevation(self, position: Vector2) -> Optional[int]:
        """Get elevation directly from structured array (faster than get_tile)."""
        if self.is_valid_position(position):
            return int(self.tiles[position.y, position.x]["elevation"])
        return None

    def get_terrain_mask(self, terrain_type: TerrainType) -> NDArray[np.bool_]:
        """Get boolean mask of all positions with specified terrain type."""
        return self.tiles["terrain_type"] == terrain_type.value

    def find_terrain_positions(self, terrain_type: TerrainType) -> VectorArray:
        """Find all positions with specified terrain type using vectorized operations."""
        mask = self.get_terrain_mask(terrain_type)
        y_coords, x_coords = np.where(mask)
        positions = np.column_stack((y_coords, x_coords)).astype(np.int16)
        return VectorArray(positions)

    # ============== Occupancy and Unit Mask Methods ==============

    def get_occupied_mask(self) -> NDArray[np.bool_]:
        """Get boolean mask of all occupied positions."""
        return self.occupancy >= 0

    def get_team_mask(self, team: Team) -> NDArray[np.bool_]:
        """Get boolean mask of positions occupied by specific team."""
        mask = np.zeros((self.height, self.width), dtype=np.bool_)

        # Use vectorized operations where possible
        occupied_mask = self.get_occupied_mask()
        y_coords, x_coords = np.where(occupied_mask)

        for y, x in zip(y_coords, x_coords):
            unit_index = self.occupancy[y, x]
            unit = self._units[unit_index]
            if unit is not None and unit.is_alive and unit.team == team:
                mask[y, x] = True

        return mask

    def get_enemy_mask(self, team: Team) -> NDArray[np.bool_]:
        """Get boolean mask of positions occupied by enemies of specified team."""
        mask = np.zeros((self.height, self.width), dtype=np.bool_)

        occupied_mask = self.get_occupied_mask()
        y_coords, x_coords = np.where(occupied_mask)

        for y, x in zip(y_coords, x_coords):
            unit_index = self.occupancy[y, x]
            unit = self._units[unit_index]
            if unit is not None and unit.is_alive and unit.team != team:
                mask[y, x] = True

        return mask

    def get_blocking_mask(self, team: Team) -> NDArray[np.bool_]:
        """Get boolean mask combining terrain and enemy unit blocking for pathfinding."""
        # Get terrain blocking
        terrain_types = self.tiles["terrain_type"]

        # Import terrain data
        from ..core.data.game_info import TERRAIN_DATA

        max_terrain_value = max(terrain.value for terrain in TerrainType)
        blocks_movement = np.zeros(max_terrain_value + 1, dtype=np.bool_)

        for terrain_type in TerrainType:
            terrain_info = TERRAIN_DATA[terrain_type]
            blocks_movement[terrain_type.value] = terrain_info.blocks_movement

        terrain_blocking = blocks_movement[terrain_types]

        # Get enemy unit blocking
        enemy_blocking = self.get_enemy_mask(team)

        # Combine both types of blocking
        return terrain_blocking | enemy_blocking

    def is_position_blocked(self, position: Vector2, team: Team) -> bool:
        """Check if position is blocked by terrain or enemy units."""
        if not self.is_valid_position(position):
            return True

        # Check terrain blocking
        terrain_type = self.get_terrain_type(position)
        if terrain_type and self.is_terrain_blocking(terrain_type):
            return True

        # Check unit blocking
        unit = self.get_unit_at(position)
        if unit and unit.team != team:
            return True

        return False

    def is_terrain_blocking(self, terrain_type: TerrainType) -> bool:
        """Check if terrain type blocks movement using direct lookup."""
        from ..core.data.game_info import TERRAIN_DATA

        return TERRAIN_DATA[terrain_type].blocks_movement

    def get_terrain_move_cost(self, terrain_type: TerrainType) -> int:
        """Get movement cost for terrain type using direct lookup."""
        from ..core.data.game_info import TERRAIN_DATA

        return TERRAIN_DATA[terrain_type].move_cost

    def is_valid_position(self, position: Vector2) -> bool:
        return 0 <= position.x < self.width and 0 <= position.y < self.height

    def add_unit(self, unit: Unit) -> bool:
        """Add unit to map and return success status."""
        if not self.is_valid_position(unit.position):
            return False

        if self.get_unit_at(unit.position):
            return False

        # Check if tile can be entered using direct terrain access
        terrain_type = self.get_terrain_type(unit.position)
        if not terrain_type or self.is_terrain_blocking(terrain_type):
            return False

        # Add to units list and update lookup structures
        unit_index = len(self._units)
        self._units.append(unit)
        self.unit_id_to_index[unit.unit_id] = unit_index

        # Update occupancy array
        self.occupancy[unit.position.y, unit.position.x] = unit_index

        return True

    def remove_unit(self, unit_id: str) -> Optional[Unit]:
        """Remove unit by ID and clean up all data structures."""
        unit_index = self.unit_id_to_index.get(unit_id)
        if unit_index is None:
            return None

        unit = self._units[unit_index]

        # Clear occupancy array at unit's position
        self.occupancy[unit.position.y, unit.position.x] = -1

        # Remove from index mapping
        del self.unit_id_to_index[unit_id]

        # Remove unit and compact array to eliminate None values
        self._units.pop(unit_index)

        # Update all indices that were shifted down
        for uid, idx in self.unit_id_to_index.items():
            if idx > unit_index:
                self.unit_id_to_index[uid] = idx - 1

        # Update occupancy array to reflect new indices
        self._reindex_occupancy_after_removal(unit_index)

        return unit

    def _reindex_occupancy_after_removal(self, removed_index: int) -> None:
        """Update occupancy array indices after unit removal and array compaction."""
        # Find all positions that have indices greater than the removed one
        indices_to_update = self.occupancy > removed_index
        # Decrement them by 1 to account for the removed element
        self.occupancy[indices_to_update] -= 1

    def remove_units_batch(self, unit_ids: list[str]) -> list[Unit]:
        """Remove multiple units efficiently in a single batch operation.

        This method is optimized for removing multiple units at once,
        such as when processing AOE damage that defeats multiple targets.

        Args:
            unit_ids: List of unit IDs to remove

        Returns:
            List of removed Unit objects
        """
        if not unit_ids:
            return []

        # Collect unit indices and positions
        indices_to_remove = []
        positions_to_clear = []
        removed_units = []

        for unit_id in unit_ids:
            unit_index = self.unit_id_to_index.get(unit_id)
            if unit_index is not None:
                unit = self._units[unit_index]
                indices_to_remove.append(unit_index)
                positions_to_clear.append((unit.position.y, unit.position.x))
                removed_units.append(unit)
                del self.unit_id_to_index[unit_id]

        if not indices_to_remove:
            return []

        # Sort indices in descending order for safe removal
        indices_to_remove.sort(reverse=True)

        # Clear occupancy at all positions using vectorized operation
        if positions_to_clear:
            y_coords = np.array([pos[0] for pos in positions_to_clear], dtype=np.int16)
            x_coords = np.array([pos[1] for pos in positions_to_clear], dtype=np.int16)
            self.occupancy[y_coords, x_coords] = -1

        # Remove units from list (in reverse order to maintain indices)
        for idx in indices_to_remove:
            self._units.pop(idx)

        # Rebuild index mappings efficiently
        self._rebuild_unit_index_mappings()

        return removed_units

    def _rebuild_unit_index_mappings(self) -> None:
        """Rebuild unit ID to index mappings and occupancy array after batch removal."""
        # Clear and rebuild unit_id_to_index
        self.unit_id_to_index.clear()

        # Clear occupancy grid
        self.occupancy.fill(-1)

        # Rebuild both mappings in a single pass
        for idx, unit in enumerate(self._units):
            self.unit_id_to_index[unit.unit_id] = idx
            self.occupancy[unit.position.y, unit.position.x] = idx

    def get_unit(self, unit_id: str) -> Optional[Unit]:
        """Get unit by ID using index lookup."""
        unit_index = self.unit_id_to_index.get(unit_id)
        if unit_index is None:
            return None
        unit = self._units[unit_index]
        # Handle removed units (None entries)
        return unit if unit is not None else None

    def get_unit_at(self, position: Vector2) -> Optional[Unit]:
        """Get unit at position using O(1) occupancy array lookup."""
        if not self.is_valid_position(position):
            return None

        unit_index = self.occupancy[position.y, position.x]
        if unit_index < 0:
            return None

        unit = self._units[unit_index]
        # Handle removed units (None entries) and check if alive
        if unit is None or not unit.is_alive:
            # Clear stale occupancy entry
            self.occupancy[position.y, position.x] = -1
            return None

        # Check if unit moved without notifying the map (compatibility)
        if unit.position != position:
            # Unit moved! Update occupancy arrays
            self.occupancy[position.y, position.x] = -1  # Clear old position

            # Find unit at its current position and update occupancy
            new_pos = unit.position
            if self.is_valid_position(new_pos):
                self.occupancy[new_pos.y, new_pos.x] = unit_index

            return None  # No unit at the requested position anymore

        return unit

    def get_units_by_team(self, team: Team) -> list[Unit]:
        """Get all units for a team using vectorized operations."""
        # O(1) mask generation + O(occupied_positions) extraction
        team_mask = self.get_team_mask(team)
        y_coords, x_coords = np.where(team_mask)
        # team_mask guarantees valid units exist at these positions
        return [self._units[self.occupancy[y, x]] for y, x in zip(y_coords, x_coords)]

    def count_units_by_team(self, team: Team) -> int:
        """Count units for a team using O(1) mask operations."""
        return int(np.sum(self.get_team_mask(team)))

    def count_alive_units(self) -> int:
        """Count all alive units using O(1) operations."""
        return int(np.sum(self.get_occupied_mask()))

    def get_units_in_positions(self, positions: VectorArray) -> list[Unit]:
        """Get all units at specified positions using vectorized operations."""
        if len(positions) == 0:
            return []

        # Extract coordinates
        y_coords, x_coords = positions.y_coords, positions.x_coords

        # Vectorized occupancy lookup
        unit_indices = self.occupancy[y_coords, x_coords]

        # Filter valid indices and return units
        valid_mask = unit_indices >= 0
        return [self._units[idx] for idx in unit_indices[valid_mask]]

    def are_positions_blocked(
        self, positions: VectorArray, team: Team
    ) -> NDArray[np.bool_]:
        """Check multiple positions for blocking using vectorized operations."""
        if len(positions) == 0:
            return np.array([], dtype=np.bool_)

        y_coords, x_coords = positions.y_coords, positions.x_coords

        # Combine terrain and unit blocking
        blocking_mask = self.get_blocking_mask(team)
        return blocking_mask[y_coords, x_coords]

    def move_unit(self, unit_id: str, position: Vector2) -> bool:
        """Move unit and update occupancy array."""
        unit = self.get_unit(unit_id)
        if not unit:
            return False

        if not self.is_valid_position(position):
            return False

        if self.get_unit_at(position):
            return False

        # Check if tile can be entered using direct terrain access
        terrain_type = self.get_terrain_type(position)
        if not terrain_type or self.is_terrain_blocking(terrain_type):
            return False

        # Clear old position in occupancy array
        old_position = unit.position
        self.occupancy[old_position.y, old_position.x] = -1

        # Update unit position and status
        unit.update_position_and_status(position)

        # Set new position in occupancy array
        unit_index = self.unit_id_to_index[unit_id]
        self.occupancy[position.y, position.x] = unit_index

        return True

    def calculate_movement_range(self, unit: Unit) -> VectorArray:
        """Calculate movement range using numpy-accelerated pathfinding."""
        if not unit or not unit.can_move:
            return VectorArray()

        movement = unit.movement.movement_points
        return self._calculate_movement_range_vectorized(
            unit.position, movement, unit.team
        )

    def _calculate_movement_range_vectorized(
        self, start_pos: Vector2, movement_points: int, unit_team: Team
    ) -> VectorArray:
        """Vectorized implementation of movement range calculation.

        Uses numpy arrays for distance calculations and flooding algorithm
        for significant performance improvement over the original loop-based version.
        """
        # Create arrays for pathfinding
        height, width = self.height, self.width

        # Distance array: -1 = unvisited, >= 0 = movement cost to reach
        # Use int16 for distance values (sufficient for any reasonable movement cost)
        distances = np.full((height, width), -1, dtype=np.int16)
        distances[start_pos.y, start_pos.x] = 0

        # Get terrain data for fast access
        terrain_types = self.tiles["terrain_type"]

        # Import terrain data for move costs and blocking
        from ..core.data.game_info import TERRAIN_DATA

        # Create movement cost lookup array for all terrain types
        max_terrain_value = max(terrain.value for terrain in TerrainType)
        move_costs = np.ones(
            max_terrain_value + 1, dtype=np.uint8
        )  # Movement costs are small values
        blocks_movement = np.zeros(max_terrain_value + 1, dtype=np.bool_)

        for terrain_type in TerrainType:
            terrain_info = TERRAIN_DATA[terrain_type]
            move_costs[terrain_type.value] = terrain_info.move_cost
            blocks_movement[terrain_type.value] = terrain_info.blocks_movement

        # Apply movement costs and blocking to the map
        terrain_move_costs = move_costs[terrain_types]
        terrain_blocks = blocks_movement[terrain_types]

        # Mark blocked tiles as unreachable
        distances[terrain_blocks] = -2  # -2 = permanently blocked

        # Flood fill using Dijkstra-like algorithm
        changed = True
        while changed:
            changed = False
            current_distances = distances.copy()

            # Check all four directions using array slicing
            # Right movement
            new_distances = current_distances[:-1, :] + terrain_move_costs[1:, :]
            mask = (
                (distances[1:, :] == -1)
                & (current_distances[:-1, :] >= 0)
                & (new_distances <= movement_points)
            )
            if np.any(mask):
                distances[1:, :][mask] = new_distances[mask]
                changed = True

            # Left movement
            new_distances = current_distances[1:, :] + terrain_move_costs[:-1, :]
            mask = (
                (distances[:-1, :] == -1)
                & (current_distances[1:, :] >= 0)
                & (new_distances <= movement_points)
            )
            if np.any(mask):
                distances[:-1, :][mask] = new_distances[mask]
                changed = True

            # Down movement
            new_distances = current_distances[:, :-1] + terrain_move_costs[:, 1:]
            mask = (
                (distances[:, 1:] == -1)
                & (current_distances[:, :-1] >= 0)
                & (new_distances <= movement_points)
            )
            if np.any(mask):
                distances[:, 1:][mask] = new_distances[mask]
                changed = True

            # Up movement
            new_distances = current_distances[:, 1:] + terrain_move_costs[:, :-1]
            mask = (
                (distances[:, :-1] == -1)
                & (current_distances[:, 1:] >= 0)
                & (new_distances <= movement_points)
            )
            if np.any(mask):
                distances[:, :-1][mask] = new_distances[mask]
                changed = True

        # Filter out positions occupied by enemy units using masks
        reachable_mask = distances >= 0

        # Get enemy unit positions using vectorized mask
        enemy_mask = self.get_enemy_mask(unit_team)

        # Combine reachability with enemy blocking
        valid_mask = reachable_mask & ~enemy_mask

        # Include starting position even if enemy is there (shouldn't happen but be safe)
        valid_mask[start_pos.y, start_pos.x] = True

        y_coords, x_coords = np.where(valid_mask)

        if len(y_coords) == 0:
            return VectorArray([start_pos])  # At least return starting position

        positions = np.column_stack((y_coords, x_coords)).astype(np.int16)
        return VectorArray(positions)

    def calculate_attack_range(
        self, unit: Unit, from_position: Optional[Vector2] = None
    ) -> VectorArray:
        """Calculate attack range using numpy-accelerated distance calculations."""
        if not unit or not unit.is_alive:
            return VectorArray()

        pos = from_position if from_position else unit.position
        min_range = unit.combat.attack_range_min
        max_range = unit.combat.attack_range_max

        return self._calculate_attack_range_vectorized(pos, min_range, max_range)

    def _calculate_attack_range_vectorized(
        self, center: Vector2, min_range: int, max_range: int
    ) -> VectorArray:
        """Vectorized implementation of attack range calculation.

        Uses numpy meshgrid and broadcasting for efficient distance calculations
        across the entire potential range area.
        """
        # Create coordinate arrays for the bounding box around the attack range
        y_min = max(0, center.y - max_range)
        y_max = min(self.height - 1, center.y + max_range)
        x_min = max(0, center.x - max_range)
        x_max = min(self.width - 1, center.x + max_range)

        # Create meshgrid for all positions in the bounding box
        y_coords, x_coords = np.mgrid[y_min : y_max + 1, x_min : x_max + 1]

        # Calculate Manhattan distances using broadcasting
        distances = np.abs(y_coords - center.y) + np.abs(x_coords - center.x)

        # Create mask for positions within attack range
        range_mask = (distances >= min_range) & (distances <= max_range)

        # Get valid positions
        valid_y = y_coords[range_mask]
        valid_x = x_coords[range_mask]

        if len(valid_y) == 0:
            return VectorArray()

        # Stack coordinates and create VectorArray
        positions = np.column_stack((valid_y, valid_x)).astype(np.int16)
        return VectorArray(positions)

    def calculate_aoe_tiles(self, center: Vector2, pattern: str) -> VectorArray:
        """Calculate AOE affected tiles from center position, clipped to map bounds.

        Args:
            center: Center position vector of the AOE
            pattern: AOE pattern type ("single", "cross", etc.)

        Returns:
            VectorArray of tiles affected by the AOE pattern
        """
        return self._calculate_aoe_tiles_vectorized(center, pattern)

    def _calculate_aoe_tiles_vectorized(
        self, center: Vector2, pattern: str
    ) -> VectorArray:
        """Vectorized implementation of AOE pattern generation.

        Uses numpy arrays for efficient pattern generation and bounds checking.
        """
        if pattern == "single":
            if self.is_valid_position(center):
                return VectorArray([center])
            else:
                return VectorArray()

        elif pattern == "cross":
            # Cross pattern: center plus 4 cardinal directions
            offsets = np.array(
                [
                    [0, 0],  # Center
                    [0, 1],  # Right
                    [0, -1],  # Left
                    [1, 0],  # Down
                    [-1, 0],  # Up
                ],
                dtype=np.int8,
            )  # Small offset values

        elif pattern == "square":
            # 3x3 square pattern
            offsets = np.array(
                [
                    [-1, -1],
                    [-1, 0],
                    [-1, 1],
                    [0, -1],
                    [0, 0],
                    [0, 1],
                    [1, -1],
                    [1, 0],
                    [1, 1],
                ],
                dtype=np.int8,
            )

        elif pattern == "diamond":
            # Diamond pattern (Manhattan distance <= 2)
            offsets = np.array(
                [
                    [0, 0],  # Center
                    [-1, 0],
                    [1, 0],
                    [0, -1],
                    [0, 1],  # Distance 1
                    [-2, 0],
                    [2, 0],
                    [0, -2],
                    [0, 2],  # Distance 2
                    [-1, -1],
                    [-1, 1],
                    [1, -1],
                    [1, 1],  # Distance 2 diagonals
                ],
                dtype=np.int8,
            )

        elif pattern == "line_horizontal":
            # 5-tile horizontal line
            offsets = np.array(
                [[0, -2], [0, -1], [0, 0], [0, 1], [0, 2]], dtype=np.int8
            )

        elif pattern == "line_vertical":
            # 5-tile vertical line
            offsets = np.array(
                [[-2, 0], [-1, 0], [0, 0], [1, 0], [2, 0]], dtype=np.int8
            )

        else:
            # Unknown pattern, default to single
            if self.is_valid_position(center):
                return VectorArray([center])
            else:
                return VectorArray()

        # Calculate absolute positions
        center_array = np.array([center.y, center.x], dtype=np.int16)
        positions = center_array + offsets

        # Filter positions within map bounds using vectorized operations
        valid_mask = (
            (positions[:, 0] >= 0)
            & (positions[:, 0] < self.height)
            & (positions[:, 1] >= 0)
            & (positions[:, 1] < self.width)
        )

        valid_positions = positions[valid_mask].astype(np.int16)

        if len(valid_positions) == 0:
            return VectorArray()

        return VectorArray(valid_positions)

    def calculate_threat_range(self, team: Team) -> set[Vector2]:
        """Calculate threat range for all enemy units using vectorized operations."""
        threat_range = set()

        # Use vectorized enemy mask to identify enemy positions
        enemy_mask = self.get_enemy_mask(team)
        y_coords, x_coords = np.where(enemy_mask)

        # Calculate threat ranges only for enemy units
        for y, x in zip(y_coords, x_coords):
            unit_index = self.occupancy[y, x]
            unit = self._units[unit_index]
            threat_range.update(self.calculate_attack_range(unit))

        return threat_range

    def get_path(
        self, start: Vector2, end: Vector2, max_cost: int
    ) -> Optional[list[Vector2]]:
        if start == end:
            return [start]


        queue = deque([(start, 0, [start])])
        visited = {start: 0}

        while queue:
            pos, cost, path = queue.popleft()

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_pos = Vector2(pos.y + dy, pos.x + dx)

                if not self.is_valid_position(next_pos):
                    continue

                tile = self.get_tile(next_pos)
                if tile.blocks_movement:
                    continue

                new_cost = cost + tile.move_cost

                if new_cost > max_cost:
                    continue

                if next_pos == end:
                    return path + [next_pos]

                if next_pos not in visited or visited[next_pos] > new_cost:
                    visited[next_pos] = new_cost
                    queue.append((next_pos, new_cost, path + [next_pos]))

        return None
