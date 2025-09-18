import json
import os
import random
from pathlib import Path
from typing import Any, Optional

import yaml

from ...core.data.data_structures import DataConverter, Vector2
from ...core.events.events import LogMessage, UnitSpawned
from ..map import GameMap
from .objectives import (
    AllUnitsDefeatedObjective,
    DefeatAllEnemiesObjective,
    DefeatUnitObjective,
    Objective,
    PositionCapturedObjective,
    ProtectUnitObjective,
    ReachPositionObjective,
)
from .scenario import Scenario
from .scenario_structures import (
    ActorPlacement,
    ScenarioMarker,
    ScenarioObject,
    ScenarioRegion,
    ScenarioSettings,
    ScenarioTrigger,
    UnitData,
)


class ScenarioLoader:
    """Handles loading scenarios from YAML files."""

    @staticmethod
    def load_from_file(file_path: str) -> Scenario:
        """Load a scenario from a YAML file."""
        path_obj = Path(file_path)

        # Load YAML file

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            print(f"Loaded scenario from YAML: {path_obj.name}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Scenario file not found: {file_path}")
        except Exception as e:
            raise ValueError(f"Failed to parse YAML scenario: {e}")

        # Get the directory of the scenario file for relative paths
        scenario_dir = os.path.dirname(file_path)

        scenario = ScenarioLoader._parse_scenario(data, scenario_dir)

        # Validate the scenario
        if scenario.map_file:
            try:
                # Create the map to validate against
                temp_map = GameMap.from_csv_layers(scenario.map_file)
                validation_errors = ScenarioLoader.validate_scenario(scenario, temp_map)

                if validation_errors:
                    print(f"Scenario validation warnings for {path_obj.name}:")
                    for error in validation_errors:
                        print(f"  - {error}")
            except Exception as e:
                print(f"Warning: Could not validate scenario against map: {e}")

        return scenario

    @staticmethod
    def _parse_scenario(data: dict[str, Any], base_dir: str = "") -> Scenario:
        """Parse scenario data from a dictionary."""
        scenario = Scenario(
            name=data.get("name", "Unnamed Scenario"),
            description=data.get("description", ""),
            author=data.get("author", "Unknown"),
        )

        # Parse map data
        if "map" in data:
            map_data = data["map"]
            if isinstance(map_data, dict) and "source" in map_data:
                # External map file
                map_path = map_data["source"]
                if not os.path.isabs(map_path):
                    # Try relative to project root first, then relative to scenario directory
                    if os.path.exists(map_path):
                        scenario.map_file = map_path
                    else:
                        scenario.map_file = os.path.join(base_dir, map_path)
                else:
                    scenario.map_file = map_path
            else:
                raise ValueError(
                    "Map must reference an external file with 'source' field"
                )

        # Parse markers
        if "markers" in data:
            for marker_name, marker_data in data["markers"].items():
                marker = ScenarioMarker.from_dict(marker_name, marker_data)
                scenario.markers[marker_name] = marker

        # Parse regions
        if "regions" in data:
            for region_name, region_data in data["regions"].items():
                region = ScenarioRegion.from_dict(region_name, region_data)
                scenario.regions[region_name] = region

        # Parse units (definitions only, no positions for now)
        if "units" in data:
            for unit_data in data["units"]:
                # Support both old format (with position) and new format (without position)
                if "position" in unit_data:
                    # Old format - keep for backward compatibility
                    unit = UnitData(
                        name=unit_data["name"],
                        unit_class=unit_data["class"],
                        team=unit_data["team"],
                        position=Vector2.from_list(unit_data["position"]),
                        stats_override=unit_data.get("stats_override"),
                    )
                else:
                    # New format - no position, will be resolved from placements
                    unit = UnitData(
                        name=unit_data["name"],
                        unit_class=unit_data["class"],
                        team=unit_data["team"],
                        position=Vector2(
                            0, 0
                        ),  # Temporary, will be overridden by placement
                        stats_override=unit_data.get("stats_override"),
                    )
                scenario.units.append(unit)

        # Parse objects
        if "objects" in data:
            for obj_name, obj_data in data["objects"].items():
                obj = ScenarioObject.from_dict(obj_name, obj_data)
                scenario.objects.append(obj)

        # Parse triggers
        if "triggers" in data:
            for trigger_name, trigger_data in data["triggers"].items():
                trigger = ScenarioTrigger.from_dict(trigger_name, trigger_data)
                scenario.triggers.append(trigger)

        # Parse placements
        if "placements" in data:
            for actor_name, placement_data in data["placements"].items():
                placement = ActorPlacement.from_dict(actor_name, placement_data)
                scenario.placements.append(placement)

        # Parse map overrides
        if "map_overrides" in data:
            scenario.map_overrides = data["map_overrides"]

        # Parse objectives
        if "objectives" in data:
            obj_data = data["objectives"]

            # Victory objectives
            if "victory" in obj_data:
                for obj in obj_data["victory"]:
                    parsed_obj = ScenarioLoader._parse_objective(obj)
                    if parsed_obj:
                        scenario.victory_objectives.append(parsed_obj)

            # Defeat objectives
            if "defeat" in obj_data:
                for obj in obj_data["defeat"]:
                    parsed_obj = ScenarioLoader._parse_objective(obj)
                    if parsed_obj:
                        scenario.defeat_objectives.append(parsed_obj)

        # Parse settings
        if "settings" in data:
            settings_data = data["settings"]
            scenario.settings = ScenarioSettings(
                turn_limit=settings_data.get("turn_limit"),
                starting_team=settings_data.get("starting_team", "PLAYER"),
                fog_of_war=settings_data.get("fog_of_war", False),
            )

        return scenario

    @staticmethod
    def resolve_placements(scenario: Scenario, game_map: GameMap) -> None:
        """Resolve placement intents into actual coordinates for all actors.

        This method processes the placement information and assigns actual
        coordinates to units and objects based on markers, regions, and placement policies.
        """

        # Create lookup tables for actors
        units_by_name = {unit.name: unit for unit in scenario.units}
        objects_by_name = {obj.name: obj for obj in scenario.objects}

        # Process each placement
        for placement in scenario.placements:
            actor_name = placement.actor_name

            # Find the actor (unit or object)
            if actor_name in units_by_name:
                actor = units_by_name[actor_name]
                is_unit = True
            elif actor_name in objects_by_name:
                actor = objects_by_name[actor_name]
                is_unit = False
            else:
                raise ValueError(
                    f"Actor '{actor_name}' referenced in placements but not found in units or objects. Check scenario configuration."
                )

            # Resolve placement to coordinates
            coordinates = ScenarioLoader._resolve_placement_to_coordinates(
                placement, scenario, game_map
            )

            # Apply coordinates to the actor
            if is_unit:
                actor.position = coordinates
            else:
                # For objects, set position directly now that ScenarioObject has Vector2
                actor.position = coordinates

    @staticmethod
    def _resolve_placement_to_coordinates(
        placement: ActorPlacement, scenario: Scenario, game_map: GameMap
    ) -> Vector2:
        """Resolve a single placement intent to coordinates."""

        if placement.placement_at:
            return placement.placement_at

        if placement.placement_marker:
            marker = scenario.markers.get(placement.placement_marker)
            if not marker:
                raise ValueError(
                    f"Marker '{placement.placement_marker}' not found in scenario"
                )
            return marker.position

        if not placement.placement_region:
            raise ValueError(
                "Placement must specify either 'at', 'marker', or 'region'"
            )

        region = scenario.regions.get(placement.placement_region)
        if not region:
            raise ValueError(
                f"Region '{placement.placement_region}' not found in scenario"
            )

        free_positions = region.get_free_positions(game_map)
        if not free_positions:
            raise ValueError(
                f"No free positions available in region '{placement.placement_region}'"
            )

        if placement.placement_policy == placement.placement_policy.RANDOM_FREE_TILE:
            return random.choice(free_positions)

        if placement.placement_policy == placement.placement_policy.SPREAD_EVENLY:
            # For now, just use random. A more sophisticated implementation would
            # track previously placed units and spread them out evenly
            return random.choice(free_positions)

        if placement.placement_policy == placement.placement_policy.LINE_LEFT_TO_RIGHT:
            # Sort by x coordinate, then by y
            free_positions.sort(key=lambda pos: (pos[0], pos[1]))
            return free_positions[0]

        if placement.placement_policy == placement.placement_policy.LINE_TOP_TO_BOTTOM:
            # Sort by y coordinate, then by x
            free_positions.sort(key=lambda pos: (pos[1], pos[0]))
            return free_positions[0]

        return random.choice(free_positions)

    @staticmethod
    def _parse_objective(obj_data: dict[str, Any]) -> Optional[Objective]:
        """Parse a single objective from data."""
        obj_type = obj_data.get("type")

        if obj_type == "defeat_all_enemies":
            return DefeatAllEnemiesObjective(
                description=obj_data.get("description", "Defeat all enemies")
            )

        if obj_type == "reach_position":
            position = obj_data.get("position", [0, 0])
            return ReachPositionObjective(
                position=Vector2(position[0], position[1]),
                unit_name=obj_data.get("unit_name"),
                description=obj_data.get("description"),
            )

        if obj_type == "defeat_unit":
            return DefeatUnitObjective(
                unit_name=obj_data["unit_name"], description=obj_data.get("description")
            )

        if obj_type == "protect_unit":
            return ProtectUnitObjective(
                unit_name=obj_data["unit_name"], description=obj_data.get("description")
            )

        if obj_type == "position_captured":
            position = obj_data.get("position", [0, 0])
            return PositionCapturedObjective(
                position=Vector2(position[0], position[1]),
                description=obj_data.get("description"),
            )

        if obj_type == "all_units_defeated":
            return AllUnitsDefeatedObjective(
                description=obj_data.get("description", "Keep at least one unit alive")
            )

        raise ValueError(
            f"Unknown objective type: '{obj_type}'. Supported types: defeat_all_enemies, turn_limit, all_units_defeated"
        )

    @staticmethod
    def apply_map_overrides(game_map: GameMap, overrides: dict[str, Any]) -> None:
        """Apply map overrides to modify the map non-destructively.

        Supported override types:
        - tile_patches: List of coordinate-based tile changes
        - region_patches: Region-based tile changes
        """
        from ...core.tileset_loader import get_tileset_config
        from ..tile import TerrainType

        tileset_config = get_tileset_config()

        # Apply tile patches
        if "tile_patches" in overrides:
            for patch in overrides["tile_patches"]:
                x = patch["x"]
                y = patch["y"]
                tile_id = patch["tile_id"]

                # Validate coordinates
                if not game_map.is_valid_position(Vector2(x, y)):
                    print(f"Warning: Invalid position for tile patch: ({x}, {y})")
                    continue

                # Get terrain type from tile ID
                tile_config = tileset_config.get_tile_config(tile_id)
                if tile_config:
                    terrain_type_str = tile_config.get("terrain_type", "plain")
                    terrain_type = TerrainType[terrain_type_str.upper()]
                    game_map.set_tile(Vector2(x, y), terrain_type)
                else:
                    print(f"Warning: Unknown tile ID in patch: {tile_id}")

        # Apply region patches
        if "region_patches" in overrides:
            for patch in overrides["region_patches"]:
                rect = patch["rect"]  # [x, y, width, height]
                tile_id = patch["tile_id"]

                x, y, width, height = rect

                # Get terrain type from tile ID
                tile_config = tileset_config.get_tile_config(tile_id)
                if not tile_config:
                    print(f"Warning: Unknown tile ID in region patch: {tile_id}")
                    continue

                terrain_type_str = tile_config.get("terrain_type", "plain")
                terrain_type = TerrainType[terrain_type_str.upper()]

                # Apply to all tiles in the region
                for patch_x in range(x, x + width):
                    for patch_y in range(y, y + height):
                        pos = Vector2(patch_x, patch_y)
                        if game_map.is_valid_position(pos):
                            game_map.set_tile(pos, terrain_type)

    @staticmethod
    def validate_scenario(
        scenario: Scenario, game_map: Optional[GameMap] = None
    ) -> list[str]:
        """Validate a scenario for common errors.

        Returns a list of validation error messages. Empty list means valid.
        """
        errors = []

        # Create lookup tables for actors
        unit_names = {unit.name for unit in scenario.units}
        object_names = {obj.name for obj in scenario.objects}
        all_actor_names = unit_names | object_names

        # Validate placements
        placement_actor_names = set()
        for placement in scenario.placements:
            actor_name = placement.actor_name

            # Check if actor exists
            if actor_name not in all_actor_names:
                errors.append(f"Placement for unknown actor: '{actor_name}'")
                continue

            # Check for duplicate placements
            if actor_name in placement_actor_names:
                errors.append(f"Duplicate placement for actor: '{actor_name}'")
            placement_actor_names.add(actor_name)

            # Validate marker references
            if placement.placement_marker:
                if placement.placement_marker not in scenario.markers:
                    errors.append(
                        f"Placement '{actor_name}' references unknown marker: '{placement.placement_marker}'"
                    )

            # Validate region references
            if placement.placement_region:
                if placement.placement_region not in scenario.regions:
                    errors.append(
                        f"Placement '{actor_name}' references unknown region: '{placement.placement_region}'"
                    )

            # Validate coordinates are in bounds (if map provided)
            if game_map and placement.placement_at:
                x, y = placement.placement_at
                if not game_map.is_valid_position(Vector2(x, y)):
                    errors.append(
                        f"Placement '{actor_name}' has out-of-bounds coordinates: ({x}, {y})"
                    )
                else:
                    # Check if tile is passable for units
                    if actor_name in unit_names:
                        tile = game_map.get_tile(Vector2(x, y))
                        if tile.blocks_movement:
                            errors.append(
                                f"Unit placement '{actor_name}' on impassable tile at ({x}, {y})"
                            )

        # Check for actors without placements (in new format)
        actors_without_placements = all_actor_names - placement_actor_names
        # Only warn about units without placements if there are placements defined
        # (allows backward compatibility with old format)
        if scenario.placements and actors_without_placements:
            for actor_name in actors_without_placements:
                if actor_name in unit_names:
                    # For units, check if they have old-style position
                    unit = next(u for u in scenario.units if u.name == actor_name)
                    if unit.position == Vector2(
                        0, 0
                    ):  # Default values indicate no position set
                        errors.append(f"Unit '{actor_name}' has no placement defined")

        # Validate marker coordinates are in bounds (if map provided)
        if game_map:
            for marker_name, marker in scenario.markers.items():
                x, y = marker.position
                if not game_map.is_valid_position(Vector2(x, y)):
                    errors.append(
                        f"Marker '{marker_name}' has out-of-bounds coordinates: ({x}, {y})"
                    )

        # Validate region bounds (if map provided)
        if game_map:
            for region_name, region in scenario.regions.items():
                x, y, width, height = region.rect
                if not game_map.is_valid_position(Vector2(x, y)):
                    errors.append(
                        f"Region '{region_name}' has out-of-bounds starting coordinates: ({x}, {y})"
                    )
                if not game_map.is_valid_position(
                    Vector2(x + width - 1, y + height - 1)
                ):
                    errors.append(f"Region '{region_name}' extends beyond map bounds")

        return errors

    @staticmethod
    def create_game_map(scenario: Scenario, event_manager=None) -> GameMap:
        """Create a GameMap from scenario data."""
        if scenario.map_file:
            # Load from CSV directory format
            game_map = GameMap.from_csv_layers(scenario.map_file)

            # Apply map overrides if present
            if scenario.map_overrides:
                ScenarioLoader.apply_map_overrides(game_map, scenario.map_overrides)

            return game_map
        else:
            raise ValueError("Scenario must have a map_file reference")

    @staticmethod
    def place_units(scenario: Scenario, game_map: GameMap, event_manager=None) -> None:
        """Place units from scenario data onto the map.

        Uses the new placement system to resolve unit positions from
        placement intents (markers, regions, direct coordinates).
        """
        # First, resolve all placements to actual coordinates
        ScenarioLoader.resolve_placements(scenario, game_map)

        # Now place all units on the map
        for unit_data in scenario.units:
            try:
                # Use centralized converter to create unit from scenario data
                unit = DataConverter.scenario_data_to_unit(unit_data)

                # Add unit to map
                if game_map.add_unit(unit):
                    # Emit unit spawned event
                    if event_manager:
                        event_manager.publish(
                            UnitSpawned(
                                turn=0,  # Initial placement
                                unit_name=unit.name,
                                team=unit.team,
                                position=(unit.position.x, unit.position.y),
                            ),
                            source="ScenarioLoader",
                        )
                        event_manager.publish(
                            LogMessage(
                                turn=0,
                                message=f"Unit {unit.name} spawned at {unit.position}",
                                category="SCENARIO",
                                level="INFO",
                                source="ScenarioLoader",
                            ),
                            source="ScenarioLoader",
                        )
                else:
                    raise ValueError(
                        f"Could not place unit '{unit.name}' at ({unit.position.x}, {unit.position.y}). Position may be blocked or invalid."
                    )
            except (KeyError, ValueError) as e:
                raise ValueError(f"Error creating unit '{unit_data.name}': {e}") from e

    @staticmethod
    def save_scenario(scenario: Scenario, file_path: str) -> None:
        """Save a scenario to a JSON file."""
        data = {
            "name": scenario.name,
            "description": scenario.description,
            "author": scenario.author,
            "map": {},
            "units": [],
            "objectives": {"victory": [], "defeat": []},
            "settings": {
                "turn_limit": scenario.settings.turn_limit,
                "starting_team": scenario.settings.starting_team,
                "fog_of_war": scenario.settings.fog_of_war,
            },
        }

        # Map data
        if scenario.map_file:
            data["map"]["source"] = scenario.map_file
        else:
            raise ValueError("Scenario must have a map_file to save")

        # Units
        for unit in scenario.units:
            unit_dict = {
                "name": unit.name,
                "class": unit.unit_class,
                "team": unit.team,
                "position": [unit.position.x, unit.position.y],
            }
            if unit.stats_override:
                unit_dict["stats_override"] = unit.stats_override
            data["units"].append(unit_dict)

        # Save to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

