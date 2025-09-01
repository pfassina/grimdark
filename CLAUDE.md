# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grimdark SRPG is a Strategy Role-Playing Game built in Python with a clean, renderer-agnostic architecture. The codebase demonstrates complete separation between game logic and rendering through a push-based, data-driven design.

## Development Commands

```bash
# Run architecture validation test
python tests/test_architecture.py

# Run auto-playing demo with simple renderer (uses default scenario)
python demos/demo.py

# Play interactive terminal version (uses default scenario)
python main.py

# Play specific scenarios
python demos/demo_scenario.py assets/scenarios/tutorial.yaml
python demos/demo_scenario.py assets/scenarios/fortress_defense.yaml
python demos/demo_scenario.py assets/scenarios/escape_mission.yaml

# Test scenario loading and objectives
python tests/test_scenario.py
python tests/test_objectives.py
python tests/test_all_scenarios.py

# Load maps from CSV directories
python demos/demo_map_loader.py assets/maps/fortress

# Update Nix flake dependencies
nix flake update --update-input nixpkgs
```

## Development Environment

- This repository uses a Nix flake for development. You need to explicitly call it when running python scripts.
- Run commands with `nix develop` prefix for the development shell

## Architecture

The system uses a **push-based rendering architecture** where game logic and rendering are completely separated:

- **Game logic** updates state and builds a `RenderContext` containing all renderable data
- **Renderers** receive the context and draw it using their own implementation
- Communication happens only through simple data structures in `src/core/renderable.py`

### Core Components

1. **Core Layer** (`src/core/`)
   - `renderable.py` - Data classes for renderable entities (NO game logic)
   - `renderer.py` - Abstract base class all renderers must implement
   - `game_state.py` - Centralized state management
   - `input.py` - Generic input events (renderer-agnostic)
   - `tileset_loader.py` - Data-driven tileset configuration and terrain properties
   - `game_enums.py` - Centralized enums for teams, unit classes, terrain types
   - `data_structures.py` - Data conversion utilities and base structures
   - `game_info.py` - Game constants and lookup tables

2. **Game Logic** (`src/game/`)
   - `game.py` - Main game loop, turn management, state updates, objective checking
   - `map.py` - Grid-based battlefield, pathfinding, visibility, CSV map loading
   - `unit.py` - Character stats and properties
   - `tile.py` - Terrain types and effects
   - `scenario.py` - Scenario definitions and objective types
   - `scenario_loader.py` - YAML scenario loading and parsing
   - `map_objects.py` - Map objects: spawn points, regions, triggers
   - `unit_templates.py` - Unit class definitions and stat templates
   - `scenario_menu.py` - Scenario selection and management

3. **Renderers** (`src/renderers/`)
   - Each renderer independently decides HOW to display the render context
   - Terminal renderer uses ASCII characters
   - New renderers (pygame, web, etc.) can be added without touching game code

### Key Design Principles

- **No game logic in renderers** - Renderers only draw what they're told
- **No rendering code in game** - Game doesn't know how things look
- **Data-driven communication** - Only simple data structures cross the boundary
- **Input abstraction** - Renderers convert their input to generic `InputEvent` objects
- **Renderer-owned visuals** - Each renderer owns its display logic (colors, symbols, sprites)
- **Centralized gameplay data** - Terrain properties and gameplay rules in `assets/tileset.yaml`

## Asset System

The game uses a layered, data-driven asset system:

### Tileset Configuration (`assets/tileset.yaml`)
- Defines gameplay properties for all terrain types (move cost, defense, etc.)
- Maps terrain names to tile IDs
- **Does not** define visual properties (colors/symbols) - those are renderer-specific
- Single source of truth for terrain gameplay mechanics

### Map System
- **CSV-based layers**: `ground.csv` (required), `walls.csv`, `features.csv` (optional)  
- **Map objects**: `objects.yaml` defines spawn points, regions, triggers
- **Layer composition**: Higher layers override lower layers
- **Directory structure**: Each map is a directory in `assets/maps/`

### Scenario System  
- **YAML format**: Human-readable scenario definitions in `assets/scenarios/`
- **Map references**: Link to map directories, not embedded map data
- **Objective patterns**: Reusable YAML anchors for common objectives
- **Unit placement**: Via spawn points or direct coordinate specification

## Adding Features

When adding new game features:
1. Update game logic in `src/game/`
2. Add necessary data to render context in `src/core/renderable.py`
3. Update renderers to display the new data

When adding a new renderer:
1. Inherit from `Renderer` base class
2. Implement required methods: `initialize()`, `render_frame()`, `get_input_events()`, `cleanup()`
3. Register it in main entry point

When creating new scenarios:
1. Create YAML files in `assets/scenarios/` directory
2. Reference external CSV map directories in `assets/maps/`
3. Define spawn points and map objects in `objects.yaml`
4. Place units with optional stat overrides
5. Set victory/defeat objectives using objective patterns
6. Configure game settings (turn limits, etc.)

When creating new maps:
1. Create directories in `assets/maps/` with CSV layers
2. Required: `ground.csv` with terrain data
3. Optional: `walls.csv`, `features.csv` for additional layers
4. Optional: `objects.yaml` for spawn points and interactive elements
5. Terrain properties defined in `assets/tileset.yaml`

## Testing

Multiple test scripts validate different aspects:
- `tests/test_architecture.py` - Core architecture and rendering separation
- `tests/test_objectives.py` - Scenario objectives and victory/defeat conditions
- `tests/test_scenario.py` - Scenario loading and unit placement

When adding features:
- Ensure all existing tests still pass
- Test that both renderers display new features correctly
- Verify game logic works without any renderer (testability principle)
- Add scenario tests for new objective types