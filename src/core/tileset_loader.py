"""Tileset configuration loader for data-driven rendering.

This module provides utilities to load tileset configuration from YAML files,
enabling data-driven rendering where display properties are defined externally
rather than hardcoded in the game logic or renderers.
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


class TilesetConfig:
    """Container for tileset configuration data."""

    def __init__(self, config_data: dict[str, Any]):
        self.tiles = config_data.get("tiles", {})
        self.symbol_to_tile_id = config_data.get("symbol_to_tile_id", {})
        self.terrain_to_tile_id = config_data.get("terrain_to_tile_id", {})

    def get_tile_config(self, tile_id: int) -> Optional[dict[str, Any]]:
        """Get configuration for a specific tile ID."""
        return self.tiles.get(tile_id)

    def get_terrain_gameplay_info(self, terrain_type: str) -> dict[str, Any]:
        """Get gameplay info for a terrain type.

        Args:
            terrain_type: Can be lowercase ("plain") or uppercase ("PLAIN")

        Returns:
            Dict with gameplay properties (move_cost, defense_bonus, etc.)
        """
        # Normalize terrain type to lowercase for lookup
        terrain_key = terrain_type.lower()
        tile_id = self.terrain_to_tile_id.get(terrain_key)
        if tile_id is None:
            return {
                "move_cost": 1,
                "defense_bonus": 0,
                "avoid_bonus": 0,
                "blocks_movement": False,
                "blocks_vision": False,
            }

        tile_config = self.tiles.get(tile_id, {})
        return {
            "move_cost": tile_config.get("move_cost", 1),
            "defense_bonus": tile_config.get("defense_bonus", 0),
            "avoid_bonus": tile_config.get("avoid_bonus", 0),
            "blocks_movement": tile_config.get("blocks_movement", False),
            "blocks_vision": tile_config.get("blocks_vision", False),
        }


class TilesetLoader:
    """Loader for tileset configuration files with caching and fallbacks."""

    def __init__(self, tileset_path: Optional[str] = None):
        self.tileset_path = tileset_path or self._find_default_tileset_path()
        self._cached_config: Optional[TilesetConfig] = None

    def _find_default_tileset_path(self) -> str:
        """Find the default tileset.yaml file relative to the project."""
        # Start from this file's directory and walk up to find assets/tileset.yaml
        current_dir = Path(__file__).parent
        for _ in range(5):  # Limit search depth
            tileset_path = current_dir / "assets" / "tileset.yaml"
            if tileset_path.exists():
                return str(tileset_path)
            current_dir = current_dir.parent

        # Fallback: assume it's in the project root
        return "assets/tileset.yaml"

    def load_config(self, force_reload: bool = False) -> TilesetConfig:
        """Load tileset configuration, using cache if available."""
        if self._cached_config is not None and not force_reload:
            return self._cached_config

        try:
            if os.path.exists(self.tileset_path):
                with open(self.tileset_path, "r") as file:
                    config_data = yaml.safe_load(file)
                    self._cached_config = TilesetConfig(config_data)
            else:
                # print(f"Warning: Tileset file not found at {self.tileset_path}, using fallback configuration")
                self._cached_config = self._create_fallback_config()

        except Exception:
            # print(f"Error loading tileset configuration: {e}")
            # print("Using fallback configuration")
            self._cached_config = self._create_fallback_config()

        return self._cached_config

    def _create_fallback_config(self) -> TilesetConfig:
        """Create a basic fallback configuration with gameplay properties only."""
        fallback_data = {
            "tiles": {
                1: {
                    "terrain_type": "plain",
                    "move_cost": 1,
                    "defense_bonus": 0,
                    "avoid_bonus": 0,
                    "blocks_movement": False,
                    "blocks_vision": False,
                },
                2: {
                    "terrain_type": "forest",
                    "move_cost": 2,
                    "defense_bonus": 1,
                    "avoid_bonus": 20,
                    "blocks_movement": False,
                    "blocks_vision": False,
                },
                3: {
                    "terrain_type": "mountain",
                    "move_cost": 3,
                    "defense_bonus": 2,
                    "avoid_bonus": 30,
                    "blocks_movement": False,
                    "blocks_vision": False,
                },
                4: {
                    "terrain_type": "water",
                    "move_cost": 99,
                    "defense_bonus": 0,
                    "avoid_bonus": 0,
                    "blocks_movement": True,
                    "blocks_vision": False,
                },
                5: {
                    "terrain_type": "road",
                    "move_cost": 1,
                    "defense_bonus": 0,
                    "avoid_bonus": 0,
                    "blocks_movement": False,
                    "blocks_vision": False,
                },
                6: {
                    "terrain_type": "fort",
                    "move_cost": 1,
                    "defense_bonus": 3,
                    "avoid_bonus": 10,
                    "blocks_movement": False,
                    "blocks_vision": False,
                },
                7: {
                    "terrain_type": "bridge",
                    "move_cost": 1,
                    "defense_bonus": 0,
                    "avoid_bonus": 0,
                    "blocks_movement": False,
                    "blocks_vision": False,
                },
                8: {
                    "terrain_type": "wall",
                    "move_cost": 99,
                    "defense_bonus": 0,
                    "avoid_bonus": 0,
                    "blocks_movement": True,
                    "blocks_vision": True,
                },
            },
            "terrain_to_tile_id": {
                "plain": 1,
                "forest": 2,
                "mountain": 3,
                "water": 4,
                "road": 5,
                "fort": 6,
                "bridge": 7,
                "wall": 8,
            },
        }
        return TilesetConfig(fallback_data)


# Global loader instance for easy access
_default_loader = TilesetLoader()


def get_tileset_config(force_reload: bool = False) -> TilesetConfig:
    """Get the default tileset configuration."""
    return _default_loader.load_config(force_reload)
