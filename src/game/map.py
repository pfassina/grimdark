from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import csv
import os
from numpy.typing import NDArray

from ..core.game_enums import TerrainType, Team
from ..core.tileset_loader import get_tileset_config
from ..core.data_structures import Vector2, VectorArray
from .tile import Tile
from .unit import Unit


@dataclass
class GameMap:
    width: int
    height: int
    tiles: np.ndarray = field(init=False)
    units: dict[str, Unit] = field(default_factory=dict)
    
    def __post_init__(self):
        # Create structured array for efficient tile storage
        # Use optimal dtypes: uint8 for terrain (8 values), int8 for elevation (-128 to 127)
        tile_dtype = np.dtype([
            ('terrain_type', np.uint8),
            ('elevation', np.int8)
        ])
        
        self.tiles = np.zeros((self.height, self.width), dtype=tile_dtype)
        # Initialize all tiles to PLAIN terrain with 0 elevation
        self.tiles['terrain_type'] = TerrainType.PLAIN.value
        self.tiles['elevation'] = 0
    
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
        ground_csv = os.path.join(map_dir, 'ground.csv')
        walls_csv = os.path.join(map_dir, 'walls.csv')
        features_csv = os.path.join(map_dir, 'features.csv')
        
        if not os.path.exists(ground_csv):
            raise FileNotFoundError(f"Required ground.csv not found in {map_dir}")
        
        # Load ground layer (required)
        with open(ground_csv, 'r', encoding='utf-8') as f:
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
                    if not override_empty and (not cell or cell == '0'):
                        continue
                    
                    try:
                        tile_id = int(cell)
                        if tile_id == 0 and not override_empty:
                            continue
                            
                        tile_config = tileset_config.get_tile_config(tile_id)
                        
                        if tile_config:
                            terrain_type_str = tile_config.get('terrain_type', 'plain')
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
            with open(walls_csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                walls_data = [row for row in reader if row]
            if walls_data:
                process_layer(walls_data, override_empty=False)
        
        # Process features layer if it exists  
        if os.path.exists(features_csv):
            with open(features_csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                features_data = [row for row in reader if row]
            if features_data:
                process_layer(features_data, override_empty=False)
        
        return game_map
    
    def get_tile_data(self, position: Vector2) -> Optional[tuple[TerrainType, int]]:
        """Get terrain type and elevation at position directly from structured array."""
        if self.is_valid_position(position):
            tile_data = self.tiles[position.y, position.x]
            terrain_type = TerrainType(tile_data['terrain_type'])
            elevation = int(tile_data['elevation'])
            return (terrain_type, elevation)
        return None
    
    def get_tile(self, position: Vector2) -> Optional[Tile]:
        """Get tile at position. Legacy method for compatibility."""
        if self.is_valid_position(position):
            tile_data = self.tiles[position.y, position.x]
            terrain_type = TerrainType(tile_data['terrain_type'])
            elevation = int(tile_data['elevation'])
            return Tile(position, terrain_type, elevation)
        return None
    
    def set_tile(self, position: Vector2, terrain_type: TerrainType, elevation: int = 0):
        """Set tile at position using structured array for efficiency."""
        if self.is_valid_position(position):
            self.tiles[position.y, position.x] = (terrain_type.value, elevation)
    
    def get_terrain_type(self, position: Vector2) -> Optional[TerrainType]:
        """Get terrain type directly from structured array (faster than get_tile)."""
        if self.is_valid_position(position):
            terrain_value = self.tiles[position.y, position.x]['terrain_type']
            return TerrainType(terrain_value)
        return None
    
    def get_elevation(self, position: Vector2) -> Optional[int]:
        """Get elevation directly from structured array (faster than get_tile)."""
        if self.is_valid_position(position):
            return int(self.tiles[position.y, position.x]['elevation'])
        return None
    
    def get_terrain_mask(self, terrain_type: TerrainType) -> NDArray[np.bool_]:
        """Get boolean mask of all positions with specified terrain type."""
        return self.tiles['terrain_type'] == terrain_type.value
    
    def find_terrain_positions(self, terrain_type: TerrainType) -> VectorArray:
        """Find all positions with specified terrain type using vectorized operations."""
        mask = self.get_terrain_mask(terrain_type)
        y_coords, x_coords = np.where(mask)
        positions = np.column_stack((y_coords, x_coords)).astype(np.int16)
        return VectorArray(positions)
    
    def is_terrain_blocking(self, terrain_type: TerrainType) -> bool:
        """Check if terrain type blocks movement using direct lookup."""
        from ..core.game_info import TERRAIN_DATA
        return TERRAIN_DATA[terrain_type].blocks_movement
    
    def get_terrain_move_cost(self, terrain_type: TerrainType) -> int:
        """Get movement cost for terrain type using direct lookup."""
        from ..core.game_info import TERRAIN_DATA
        return TERRAIN_DATA[terrain_type].move_cost
    
    def is_valid_position(self, position: Vector2) -> bool:
        return 0 <= position.x < self.width and 0 <= position.y < self.height
    
    def add_unit(self, unit: Unit) -> bool:
        if not self.is_valid_position(unit.position):
            return False
        
        if self.get_unit_at(unit.position):
            return False
        
        # Check if tile can be entered using direct terrain access
        terrain_type = self.get_terrain_type(unit.position)
        if not terrain_type or self.is_terrain_blocking(terrain_type):
            return False
        
        self.units[unit.unit_id] = unit
        return True
    
    def remove_unit(self, unit_id: str) -> Optional[Unit]:
        return self.units.pop(unit_id, None)
    
    def get_unit(self, unit_id: str) -> Optional[Unit]:
        return self.units.get(unit_id)
    
    def get_unit_at(self, position: Vector2) -> Optional[Unit]:
        for unit in self.units.values():
            if unit.position == position and unit.is_alive:
                return unit
        return None
    
    def get_units_by_team(self, team: Team) -> list[Unit]:
        return [unit for unit in self.units.values() if unit.team == team and unit.is_alive]
    
    def move_unit(self, unit_id: str, position: Vector2) -> bool:
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
        
        unit.move_to(position)
        return True
    
    def calculate_movement_range(self, unit: Unit) -> VectorArray:
        """Calculate movement range using numpy-accelerated pathfinding."""
        if not unit or not unit.can_move:
            return VectorArray()
        
        movement = unit.movement.movement_points
        return self._calculate_movement_range_vectorized(unit.position, movement, unit.team)
    
    def _calculate_movement_range_vectorized(self, start_pos: Vector2, movement_points: int, unit_team: Team) -> VectorArray:
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
        terrain_types = self.tiles['terrain_type']
        
        # Import terrain data for move costs and blocking
        from ..core.game_info import TERRAIN_DATA
        
        # Create movement cost lookup array for all terrain types
        max_terrain_value = max(terrain.value for terrain in TerrainType)
        move_costs = np.ones(max_terrain_value + 1, dtype=np.uint8)  # Movement costs are small values
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
            mask = ((distances[1:, :] == -1) & (current_distances[:-1, :] >= 0) & 
                   (new_distances <= movement_points))
            if np.any(mask):
                distances[1:, :][mask] = new_distances[mask]
                changed = True
            
            # Left movement  
            new_distances = current_distances[1:, :] + terrain_move_costs[:-1, :]
            mask = ((distances[:-1, :] == -1) & (current_distances[1:, :] >= 0) &
                   (new_distances <= movement_points))
            if np.any(mask):
                distances[:-1, :][mask] = new_distances[mask]
                changed = True
            
            # Down movement
            new_distances = current_distances[:, :-1] + terrain_move_costs[:, 1:]
            mask = ((distances[:, 1:] == -1) & (current_distances[:, :-1] >= 0) &
                   (new_distances <= movement_points))
            if np.any(mask):
                distances[:, 1:][mask] = new_distances[mask]
                changed = True
            
            # Up movement
            new_distances = current_distances[:, 1:] + terrain_move_costs[:, :-1]
            mask = ((distances[:, :-1] == -1) & (current_distances[:, 1:] >= 0) &
                   (new_distances <= movement_points))
            if np.any(mask):
                distances[:, :-1][mask] = new_distances[mask]
                changed = True
        
        # Filter out positions occupied by enemy units
        reachable_mask = distances >= 0
        y_coords, x_coords = np.where(reachable_mask)
        
        # Check for unit conflicts (this part still needs unit position lookup)
        valid_positions = []
        for y, x in zip(y_coords, x_coords):
            pos = Vector2(int(y), int(x))
            if pos != start_pos:  # Skip starting position check
                existing_unit = self.get_unit_at(pos)
                if existing_unit and existing_unit.team != unit_team:
                    continue
            valid_positions.append([int(y), int(x)])
        
        if not valid_positions:
            return VectorArray([start_pos])  # At least return starting position
        
        return VectorArray(np.array(valid_positions, dtype=np.int16))
    
    def calculate_attack_range(self, unit: Unit, from_position: Optional[Vector2] = None) -> VectorArray:
        """Calculate attack range using numpy-accelerated distance calculations."""
        if not unit or not unit.is_alive:
            return VectorArray()
        
        pos = from_position if from_position else unit.position
        min_range = unit.combat.attack_range_min
        max_range = unit.combat.attack_range_max
        
        return self._calculate_attack_range_vectorized(pos, min_range, max_range)
    
    def _calculate_attack_range_vectorized(self, center: Vector2, min_range: int, max_range: int) -> VectorArray:
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
        y_coords, x_coords = np.mgrid[y_min:y_max+1, x_min:x_max+1]
        
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
    
    def _calculate_aoe_tiles_vectorized(self, center: Vector2, pattern: str) -> VectorArray:
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
            offsets = np.array([
                [0, 0],   # Center
                [0, 1],   # Right
                [0, -1],  # Left
                [1, 0],   # Down
                [-1, 0],  # Up
            ], dtype=np.int8)  # Small offset values
            
        elif pattern == "square":
            # 3x3 square pattern
            offsets = np.array([
                [-1, -1], [-1, 0], [-1, 1],
                [0, -1],  [0, 0],  [0, 1],
                [1, -1],  [1, 0],  [1, 1]
            ], dtype=np.int8)
            
        elif pattern == "diamond":
            # Diamond pattern (Manhattan distance <= 2)
            offsets = np.array([
                [0, 0],                    # Center
                [-1, 0], [1, 0], [0, -1], [0, 1],  # Distance 1
                [-2, 0], [2, 0], [0, -2], [0, 2],  # Distance 2
                [-1, -1], [-1, 1], [1, -1], [1, 1] # Distance 2 diagonals
            ], dtype=np.int8)
            
        elif pattern == "line_horizontal":
            # 5-tile horizontal line
            offsets = np.array([
                [0, -2], [0, -1], [0, 0], [0, 1], [0, 2]
            ], dtype=np.int8)
            
        elif pattern == "line_vertical":
            # 5-tile vertical line
            offsets = np.array([
                [-2, 0], [-1, 0], [0, 0], [1, 0], [2, 0]
            ], dtype=np.int8)
            
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
        valid_mask = ((positions[:, 0] >= 0) & (positions[:, 0] < self.height) &
                     (positions[:, 1] >= 0) & (positions[:, 1] < self.width))
        
        valid_positions = positions[valid_mask].astype(np.int16)
        
        if len(valid_positions) == 0:
            return VectorArray()
        
        return VectorArray(valid_positions)
    
    def calculate_threat_range(self, team: Team) -> set[Vector2]:
        threat_range = set()
        
        for unit in self.units.values():
            if unit.team != team and unit.is_alive:
                threat_range.update(self.calculate_attack_range(unit))
        
        return threat_range
    
    def get_path(self, start: Vector2, end: Vector2, max_cost: int) -> Optional[list[Vector2]]:
        if start == end:
            return [start]
        
        from collections import deque
        
        queue = deque([(start, 0, [start])])
        visited = {start: 0}
        
        while queue:
            pos, cost, path = queue.popleft()
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_pos = Vector2(pos.y + dy, pos.x + dx)
                
                if not self.is_valid_position(next_pos):
                    continue
                
                tile = self.get_tile(next_pos)
                if not tile or tile.blocks_movement:
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
    
