import json
import os
from typing import Optional, Any
from pathlib import Path

from ..core.data_structures import DataConverter
from ..core.game_enums import UnitClass, Team

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .scenario import (
    Scenario, UnitData, ScenarioSettings, Objective,
    DefeatAllEnemiesObjective, SurviveTurnsObjective, ReachPositionObjective,
    DefeatUnitObjective, ProtectUnitObjective, PositionCapturedObjective,
    TurnLimitObjective, AllUnitsDefeatedObjective
)
from .map import GameMap
from .unit import Unit
from .map_objects import load_map_objects, SpawnPoint


class ScenarioLoader:
    """Handles loading scenarios from YAML files."""
    
    @staticmethod
    def load_from_file(file_path: str) -> Scenario:
        """Load a scenario from a YAML file."""
        path_obj = Path(file_path)
        
        if not HAS_YAML:
            raise ImportError("PyYAML is required for scenario loading. Please install pyyaml.")
        
        # Load YAML file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            print(f"Loaded scenario from YAML: {path_obj.name}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Scenario file not found: {file_path}")
        except Exception as e:
            raise ValueError(f"Failed to parse YAML scenario: {e}")
        
        # Get the directory of the scenario file for relative paths
        scenario_dir = os.path.dirname(file_path)
        
        return ScenarioLoader._parse_scenario(data, scenario_dir)
    
    @staticmethod
    def _parse_scenario(data: dict[str, Any], base_dir: str = "") -> Scenario:
        """Parse scenario data from a dictionary."""
        scenario = Scenario(
            name=data.get("name", "Unnamed Scenario"),
            description=data.get("description", ""),
            author=data.get("author", "Unknown")
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
                raise ValueError("Map must reference an external file with 'source' field")
        
        # Parse units
        if "units" in data:
            for unit_data in data["units"]:
                unit = UnitData(
                    name=unit_data["name"],
                    unit_class=unit_data["class"],
                    team=unit_data["team"],
                    x=unit_data["position"][0],
                    y=unit_data["position"][1],
                    stats_override=unit_data.get("stats_override")
                )
                scenario.units.append(unit)
        
        # Parse objectives
        if "objectives" in data:
            obj_data = data["objectives"]
            
            # Victory objectives
            if "victory" in obj_data:
                for obj in obj_data["victory"]:
                    parsed_obj = ScenarioLoader._parse_objective(obj, is_victory=True)
                    if parsed_obj:
                        scenario.victory_objectives.append(parsed_obj)
            
            # Defeat objectives
            if "defeat" in obj_data:
                for obj in obj_data["defeat"]:
                    parsed_obj = ScenarioLoader._parse_objective(obj, is_victory=False)
                    if parsed_obj:
                        scenario.defeat_objectives.append(parsed_obj)
        
        # Parse settings
        if "settings" in data:
            settings_data = data["settings"]
            scenario.settings = ScenarioSettings(
                turn_limit=settings_data.get("turn_limit"),
                starting_team=settings_data.get("starting_team", "PLAYER"),
                fog_of_war=settings_data.get("fog_of_war", False)
            )
        
        return scenario
    
    @staticmethod
    def _parse_objective(obj_data: dict[str, Any], is_victory: bool) -> Optional[Objective]:
        """Parse a single objective from data."""
        obj_type = obj_data.get("type")
        
        if obj_type == "defeat_all_enemies":
            return DefeatAllEnemiesObjective(
                description=obj_data.get("description", "Defeat all enemies")
            )
        
        elif obj_type == "survive_turns":
            turns = obj_data.get("turns", 10)
            return SurviveTurnsObjective(
                turns=turns,
                description=obj_data.get("description")
            )
        
        elif obj_type == "reach_position":
            position = obj_data.get("position", [0, 0])
            return ReachPositionObjective(
                x=position[0],
                y=position[1],
                unit_name=obj_data.get("unit_name"),
                description=obj_data.get("description")
            )
        
        elif obj_type == "defeat_unit":
            return DefeatUnitObjective(
                unit_name=obj_data["unit_name"],
                description=obj_data.get("description")
            )
        
        elif obj_type == "protect_unit":
            return ProtectUnitObjective(
                unit_name=obj_data["unit_name"],
                description=obj_data.get("description")
            )
        
        elif obj_type == "position_captured":
            position = obj_data.get("position", [0, 0])
            return PositionCapturedObjective(
                x=position[0],
                y=position[1],
                description=obj_data.get("description")
            )
        
        elif obj_type == "turn_limit":
            turns = obj_data.get("turns", 20)
            return TurnLimitObjective(
                turns=turns,
                description=obj_data.get("description")
            )
        
        elif obj_type == "all_units_defeated":
            return AllUnitsDefeatedObjective(
                description=obj_data.get("description", "Keep at least one unit alive")
            )
        
        return None
    
    @staticmethod
    def create_game_map(scenario: Scenario) -> GameMap:
        """Create a GameMap from scenario data."""
        if scenario.map_file:
            # Load from CSV directory format
            return GameMap.from_csv_layers(scenario.map_file)
        else:
            raise ValueError("Scenario must have a map_file reference")
    
    @staticmethod
    def place_units(scenario: Scenario, game_map: GameMap) -> None:
        """Place units from scenario data onto the map.
        
        This method will try to use spawn points from objects.yaml if available,
        falling back to positions defined in the scenario file.
        """
        # Load map objects if available
        map_objects = None
        if scenario.map_file:
            map_objects = load_map_objects(scenario.map_file)
        
        # Track which spawn points have been used
        used_spawn_points = set()
        
        for unit_data in scenario.units:
            try:
                # Use centralized converter to create unit from scenario data
                unit = DataConverter.scenario_data_to_unit(unit_data)
                
                # Try to find a spawn point for this unit
                spawn_point = None
                if map_objects:
                    # First, try to find spawn point by exact name match
                    spawn_point = map_objects.get_spawn_point(unit.name)
                    
                    # If not found by name, find an unused spawn point for the team
                    if not spawn_point:
                        team_spawns = map_objects.get_spawn_points_for_team(Team[unit_data.team])
                        for sp in team_spawns:
                            if sp.name not in used_spawn_points:
                                # Optionally check if class matches
                                if sp.unit_class and sp.unit_class != unit_data.unit_class:
                                    continue
                                spawn_point = sp
                                break
                
                # Use spawn point position if found
                if spawn_point:
                    # Move unit to spawn point position before adding to map
                    x, y = spawn_point.position
                    unit_data.x = x
                    unit_data.y = y
                    used_spawn_points.add(spawn_point.name)
                    
                    # Override class if specified in spawn point
                    if spawn_point.unit_class:
                        unit_data.unit_class = spawn_point.unit_class
                    
                    # Recreate unit with updated position
                    unit = DataConverter.scenario_data_to_unit(unit_data)
                
                # Add unit to map
                if not game_map.add_unit(unit):
                    print(f"Warning: Could not place unit '{unit.name}' at ({unit.x}, {unit.y})")
            except (KeyError, ValueError) as e:
                print(f"Warning: Error creating unit '{unit_data.name}': {e}")
                continue
    
    @staticmethod
    def save_scenario(scenario: Scenario, file_path: str) -> None:
        """Save a scenario to a JSON file."""
        data = {
            "name": scenario.name,
            "description": scenario.description,
            "author": scenario.author,
            "map": {},
            "units": [],
            "objectives": {
                "victory": [],
                "defeat": []
            },
            "settings": {
                "turn_limit": scenario.settings.turn_limit,
                "starting_team": scenario.settings.starting_team,
                "fog_of_war": scenario.settings.fog_of_war
            }
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
                "class": unit.actor.unit_class,
                "team": unit.team,
                "position": [unit.x, unit.y]
            }
            if unit.stats_override:
                unit_dict["stats_override"] = unit.stats_override
            data["units"].append(unit_dict)
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)