from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import csv
import os

from ..core.game_enums import TerrainType, Team
from ..core.tileset_loader import get_tileset_config
from ..core.data_structures import Vector2
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
                self.tiles[y, x] = Tile(Vector2(y, x), TerrainType.PLAIN)
    
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
    
    def get_tile(self, position: Vector2) -> Optional[Tile]:
        if self.is_valid_position(position):
            return self.tiles[position.y, position.x]
        return None
    
    def set_tile(self, position: Vector2, terrain_type: TerrainType, elevation: int = 0):
        if self.is_valid_position(position):
            self.tiles[position.y, position.x] = Tile(position, terrain_type, elevation)
    
    def is_valid_position(self, position: Vector2) -> bool:
        return 0 <= position.x < self.width and 0 <= position.y < self.height
    
    def add_unit(self, unit: Unit) -> bool:
        if not self.is_valid_position(unit.position):
            return False
        
        if self.get_unit_at(unit.position):
            return False
        
        tile = self.get_tile(unit.position)
        if not tile or not tile.can_enter(unit):
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
        
        tile = self.get_tile(position)
        if not tile or not tile.can_enter(unit):
            return False
        
        unit.move_to(position)
        return True
    
    def calculate_movement_range(self, unit: Unit) -> set[Vector2]:
        if not unit or not unit.can_move:
            return set()
        
        movement = unit.movement.movement_points
        visited = set()
        reachable = set()
        frontier = [(unit.position, movement)]
        
        while frontier:
            pos, remaining = frontier.pop(0)
            
            if pos in visited:
                continue
            
            visited.add(pos)
            
            if pos != unit.position:
                existing_unit = self.get_unit_at(pos)
                if existing_unit and existing_unit.team != unit.team:
                    continue
            
            reachable.add(pos)
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_pos = Vector2(pos.y + dy, pos.x + dx)
                
                if not self.is_valid_position(next_pos):
                    continue
                
                tile = self.get_tile(next_pos)
                if not tile or tile.blocks_movement:
                    continue
                
                cost = tile.move_cost
                if remaining >= cost:
                    frontier.append((next_pos, remaining - cost))
        
        return reachable
    
    def calculate_attack_range(self, unit: Unit, from_position: Optional[Vector2] = None) -> set[Vector2]:
        if not unit or not unit.is_alive:
            return set()
        
        if from_position:
            pos = from_position
        else:
            pos = unit.position
        
        attack_range = set()
        min_range = unit.combat.attack_range_min
        max_range = unit.combat.attack_range_max
        
        for dy in range(-max_range, max_range + 1):
            for dx in range(-max_range, max_range + 1):
                distance = abs(dx) + abs(dy)
                
                if min_range <= distance <= max_range:
                    target_pos = Vector2(pos.y + dy, pos.x + dx)
                    if self.is_valid_position(target_pos):
                        attack_range.add(target_pos)
        
        return attack_range
    
    def calculate_aoe_tiles(self, center: Vector2, pattern: str) -> list[Vector2]:
        """Calculate AOE affected tiles from center position, clipped to map bounds.
        
        Args:
            center: Center position vector of the AOE
            pattern: AOE pattern type ("single", "cross", etc.)
            
        Returns:
            List of tiles affected by the AOE pattern
        """
        tiles = []
        
        if pattern == "cross":
            # Cross pattern: center plus 1 Manhattan distance
            candidates = [
                center,                                      # Center
                Vector2(center.y, center.x + 1),           # Right
                Vector2(center.y, center.x - 1),           # Left
                Vector2(center.y + 1, center.x),           # Down
                Vector2(center.y - 1, center.x),           # Up
            ]
            
            # Clip to map boundaries
            for pos in candidates:
                if self.is_valid_position(pos):
                    tiles.append(pos)
                    
        elif pattern == "single":
            # Single target only
            if self.is_valid_position(center):
                tiles.append(center)
        
        # Future patterns can be added here (square, line, etc.)
        
        return tiles
    
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
    
