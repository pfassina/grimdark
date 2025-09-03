from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import csv
import os

from ..core.game_enums import TerrainType, Team
from ..core.game_info import TERRAIN_DATA
from ..core.tileset_loader import get_tileset_config
from .tile import Tile
from .unit import Unit


@dataclass
class GameMap:
    width: int
    height: int
    tiles: np.ndarray = field(init=False)
    units: dict[str, Unit] = field(default_factory=dict)
    
    def __post_init__(self):
        self.tiles = np.empty((self.height, self.width), dtype=object)
        for y in range(self.height):
            for x in range(self.width):
                self.tiles[y, x] = Tile(x, y, TerrainType.PLAIN)
    
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
                        
                        game_map.set_tile(x, y, terrain_type)
                    except (ValueError, IndexError, KeyError):
                        # Only set to plain if this is the ground layer
                        if override_empty:
                            game_map.set_tile(x, y, TerrainType.PLAIN)
        
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
    
    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if self.is_valid_position(x, y):
            return self.tiles[y, x]
        return None
    
    def set_tile(self, x: int, y: int, terrain_type: TerrainType, elevation: int = 0):
        if self.is_valid_position(x, y):
            self.tiles[y, x] = Tile(x, y, terrain_type, elevation)
    
    def is_valid_position(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height
    
    def add_unit(self, unit: Unit) -> bool:
        if not self.is_valid_position(unit.x, unit.y):
            return False
        
        if self.get_unit_at(unit.x, unit.y):
            return False
        
        tile = self.get_tile(unit.x, unit.y)
        if not tile or not tile.can_enter(unit):
            return False
        
        self.units[unit.unit_id] = unit
        return True
    
    def remove_unit(self, unit_id: str) -> Optional[Unit]:
        return self.units.pop(unit_id, None)
    
    def get_unit(self, unit_id: str) -> Optional[Unit]:
        return self.units.get(unit_id)
    
    def get_unit_at(self, x: int, y: int) -> Optional[Unit]:
        for unit in self.units.values():
            if unit.x == x and unit.y == y and unit.is_alive:
                return unit
        return None
    
    def get_units_by_team(self, team: Team) -> list[Unit]:
        return [unit for unit in self.units.values() if unit.team == team and unit.is_alive]
    
    def move_unit(self, unit_id: str, x: int, y: int) -> bool:
        unit = self.get_unit(unit_id)
        if not unit:
            return False
        
        if not self.is_valid_position(x, y):
            return False
        
        if self.get_unit_at(x, y):
            return False
        
        tile = self.get_tile(x, y)
        if not tile or not tile.can_enter(unit):
            return False
        
        unit.move_to(x, y)
        return True
    
    def calculate_movement_range(self, unit: Unit) -> set[tuple[int, int]]:
        if not unit or not unit.can_move:
            return set()
        
        movement = unit.movement.movement_points
        visited = set()
        reachable = set()
        frontier = [(unit.x, unit.y, movement)]
        
        while frontier:
            x, y, remaining = frontier.pop(0)
            
            if (x, y) in visited:
                continue
            
            visited.add((x, y))
            
            if (x, y) != (unit.x, unit.y):
                existing_unit = self.get_unit_at(x, y)
                if existing_unit and existing_unit.team != unit.team:
                    continue
            
            reachable.add((x, y))
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                
                if not self.is_valid_position(nx, ny):
                    continue
                
                tile = self.get_tile(nx, ny)
                if not tile or tile.blocks_movement:
                    continue
                
                cost = tile.move_cost
                if remaining >= cost:
                    frontier.append((nx, ny, remaining - cost))
        
        return reachable
    
    def calculate_attack_range(self, unit: Unit, from_position: Optional[tuple[int, int]] = None) -> set[tuple[int, int]]:
        if not unit or not unit.is_alive:
            return set()
        
        if from_position:
            x, y = from_position
        else:
            x, y = unit.x, unit.y
        
        attack_range = set()
        min_range = unit.combat.attack_range_min
        max_range = unit.combat.attack_range_max
        
        for dy in range(-max_range, max_range + 1):
            for dx in range(-max_range, max_range + 1):
                distance = abs(dx) + abs(dy)
                
                if min_range <= distance <= max_range:
                    nx, ny = x + dx, y + dy
                    if self.is_valid_position(nx, ny):
                        attack_range.add((nx, ny))
        
        return attack_range
    
    def calculate_aoe_tiles(self, center: tuple[int, int], pattern: str) -> list[tuple[int, int]]:
        """Calculate AOE affected tiles from center position, clipped to map bounds.
        
        Args:
            center: Center position (x, y) of the AOE
            pattern: AOE pattern type ("single", "cross", etc.)
            
        Returns:
            List of tiles affected by the AOE pattern
        """
        tiles = []
        x, y = center
        
        if pattern == "cross":
            # Cross pattern: center plus 1 Manhattan distance
            candidates = [
                (x, y),      # Center
                (x+1, y),    # Right
                (x-1, y),    # Left
                (x, y+1),    # Down
                (x, y-1),    # Up
            ]
            
            # Clip to map boundaries
            for cx, cy in candidates:
                if 0 <= cx < self.width and 0 <= cy < self.height:
                    tiles.append((cx, cy))
                    
        elif pattern == "single":
            # Single target only
            if 0 <= x < self.width and 0 <= y < self.height:
                tiles.append((x, y))
        
        # Future patterns can be added here (square, line, etc.)
        
        return tiles
    
    def calculate_threat_range(self, team: Team) -> set[tuple[int, int]]:
        threat_range = set()
        
        for unit in self.units.values():
            if unit.team != team and unit.is_alive:
                threat_range.update(self.calculate_attack_range(unit))
        
        return threat_range
    
    def get_path(self, start: tuple[int, int], end: tuple[int, int], max_cost: int) -> Optional[list[tuple[int, int]]]:
        if start == end:
            return [start]
        
        from collections import deque
        
        queue = deque([(start, 0, [start])])
        visited = {start: 0}
        
        while queue:
            (x, y), cost, path = queue.popleft()
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                
                if not self.is_valid_position(nx, ny):
                    continue
                
                tile = self.get_tile(nx, ny)
                if not tile or tile.blocks_movement:
                    continue
                
                new_cost = cost + tile.move_cost
                
                if new_cost > max_cost:
                    continue
                
                if (nx, ny) == end:
                    return path + [(nx, ny)]
                
                if (nx, ny) not in visited or visited[(nx, ny)] > new_cost:
                    visited[(nx, ny)] = new_cost
                    queue.append(((nx, ny), new_cost, path + [(nx, ny)]))
        
        return None
    
