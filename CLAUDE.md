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

# Play interactive terminal version (uses default scenario) - NOTE: Requires interactive terminal
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

# Code quality and linting
pyright .              # Type checking and error detection
ruff check .           # Code linting and style checking
ruff check . --fix     # Auto-fix linting issues where possible
ruff check . --select ARG  # Check for unused function/method parameters
```

## Testing Workflow for Claude Code

**IMPORTANT**: `main.py` uses `TerminalRenderer` which requires an interactive terminal that Claude Code cannot access. For testing during development, use the following workflow:

### Available Testing Methods

1. **Quick Demo Testing**: `python demos/demo.py`
   - Uses `SimpleRenderer` (non-interactive)
   - Auto-plays for 10 frames then quits
   - Limited input (only moves cursor right)
   - Good for basic functionality verification

2. **Architecture Tests**: `python tests/test_architecture.py`
   - Validates core architecture principles
   - Tests rendering separation
   - No visual output required

3. **Scenario Tests**: Run scenario-specific tests
   - `python tests/test_scenario.py`
   - `python tests/test_objectives.py` 
   - `python tests/test_all_scenarios.py`

### Testing New Features

When implementing new features that require specific user interactions:

1. **Create feature-specific demo scripts** in `demos/` directory
2. **Extend SimpleRenderer** with scripted input sequences if needed
3. **Add unit tests** for game logic components
4. **Verify through existing test suite** that architecture is maintained

Current `demos/demo.py` limitations:
- Only sends RIGHT key every 3 frames
- Quits after 10 frames  
- Won't exercise combat, abilities, objectives, or complex interactions

For comprehensive feature testing, create targeted demo scripts or enhance the simple renderer with configurable input sequences.

## Development Environment

- This repository uses a Nix flake for development. You need to explicitly call it when running python scripts.
- Run commands with `nix develop` prefix for the development shell
- The development environment includes:
  - Python 3.11 with required packages (numpy, pandas, pyyaml)
  - **Pyright** for static type checking
  - **Ruff** for fast linting and code formatting
  - All development tools are pre-configured and ready to use

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

## Asset System - Scenario-First Design

The game uses a **scenario-first asset system** where scenarios are the single source of truth for all gameplay content (units, objects, placements), while maps contain only geometry:

### Tileset Configuration (`assets/tileset.yaml`)
- Defines gameplay properties for all terrain types (move cost, defense, etc.)
- Maps terrain names to tile IDs
- **Does not** define visual properties (colors/symbols) - those are renderer-specific
- Single source of truth for terrain gameplay mechanics

### Map System (Geometry Only)
- **CSV-based layers**: `ground.csv` (required), `walls.csv`, `features.csv` (optional)  
- **Pure geometry**: Maps contain ONLY terrain tile IDs - no units, objects, or spawns
- **Layer composition**: Higher layers override lower layers
- **Directory structure**: Each map is a directory in `assets/maps/`
- **Reusable**: Same map can be used across multiple scenarios with different gameplay

### Scenario System (Complete Gameplay Definition)
- **YAML format**: Human-readable scenario definitions in `assets/scenarios/`
- **Map references**: Link to map directories for geometry
- **Complete gameplay**: All units, objects, placements, objectives in one file
- **Placement system**: Uses `at: [x,y]`, `at_marker: NAME`, or `at_region: NAME`
- **Markers**: Named coordinate anchors for readability (`KNIGHT_POSITION: { at: [7,2] }`)
- **Regions**: Named rectangular areas for placement policies and triggers
- **Objects**: Scenario-specific interactive elements (healing fountains, doors, etc.)
- **Map overrides**: Optional non-destructive tile patches for environmental variation

### Data Templates (`assets/data/`)
- **Unit templates**: Class definitions and base stats in `assets/data/units/`
- **Reusable definitions**: Never contain placements - only stat templates
- **Centralized balance**: Single place to adjust unit class properties

### Key Benefits of Scenario-First Design
- **Single-file authoring**: Create new scenarios by editing one file, no map changes needed
- **No redundancy**: Coordinates and placements exist in exactly one place
- **High reusability**: Same map supports many different scenarios and gameplay setups
- **Zero merge conflicts**: Multiple designers can work on scenarios using the same map
- **Deterministic builds**: Scenario loader resolves placement intents into concrete game state

## Adding Features

When adding new game features:
1. Update game logic in `src/game/`
2. Add necessary data to render context in `src/core/renderable.py`
3. Update renderers to display the new data

When adding a new renderer:
1. Inherit from `Renderer` base class
2. Implement required methods: `initialize()`, `render_frame()`, `get_input_events()`, `cleanup()`
3. Register it in main entry point

When creating new scenarios (single-file authoring):
1. Create YAML files in `assets/scenarios/` directory
2. Reference external CSV map directories with `map: { source: assets/maps/mapname }`
3. Define `units:` section with unit roster (classes, teams, stat overrides)
4. Define `objects:` section for interactive elements (healing fountains, doors, etc.)
5. Define `markers:` for named coordinate anchors (optional, for readability)
6. Define `regions:` for named rectangular areas (optional, for triggers/placement)
7. Define `placements:` section binding units/objects to coordinates using:
   - `at: [x,y]` for explicit coordinates
   - `at_marker: NAME` for marker-based placement
   - `at_region: NAME` for region-based placement (with policies)
8. Set `objectives:` for victory/defeat conditions
9. Configure `settings:` (turn limits, fog of war, etc.)
10. Add `map_overrides:` if environmental changes needed (bridges, gates, etc.)

When creating new maps (geometry only):
1. Create directories in `assets/maps/` with CSV layers
2. Required: `ground.csv` with terrain tile IDs
3. Optional: `walls.csv`, `features.csv` for additional terrain layers
4. **Do NOT add**: units, objects, spawns, or gameplay elements
5. Terrain properties defined in `assets/tileset.yaml`

## Code Style

This project follows modern Python conventions. When writing or modifying code:

### Type Hints
- **Use built-in type conventions** (Python 3.9+):
  - `dict[str, Any]` instead of `Dict[str, Any]`
  - `list[str]` instead of `List[str]`
  - `tuple[int, int]` instead of `Tuple[int, int]`
  - `set[str]` instead of `Set[str]`
- Only import from `typing` module for advanced types like `Optional`, `Union`, `TYPE_CHECKING`, etc.
- Always include type hints for function parameters and return values
- Use `Optional[Type]` for nullable values instead of `Union[Type, None]`

### General Style
- Follow PEP 8 conventions for naming and formatting
- Use descriptive variable and function names
- Add docstrings for public methods and classes
- Keep functions focused on single responsibilities
- Prefer composition over inheritance where appropriate

### Code Quality Tools
- **Pyright**: Static type checker for comprehensive type analysis
- **Ruff**: Fast Python linter for code style and quality issues
- Both tools are included in the Nix development environment
- Use `TYPE_CHECKING` imports to resolve circular dependency issues

### Mandatory Code Quality Workflow
**CRITICAL**: Always complete any coding task by running both linting tools and fixing all diagnostic errors:

1. **Run pyright for type checking**:
   ```bash
   nix develop --command pyright .
   ```
   - Fix all type errors, undefined variables, and import issues
   - Use proper type annotations and Optional types
   - Resolve circular imports with TYPE_CHECKING pattern

2. **Run ruff for linting and style**:
   ```bash
   nix develop --command ruff check . --fix  # Auto-fix what's possible
   nix develop --command ruff check .        # Check remaining issues
   nix develop --command ruff check . --select ARG  # Check for unused parameters
   ```
   - Fix unused imports, undefined variables, and style violations
   - Remove or properly use unused function/method parameters
   - Ensure proper import ordering and formatting
   - Address any remaining manual fixes needed

3. **Verify functionality**:
   ```bash
   nix develop --command python tests/test_architecture.py  # Core functionality
   nix develop --command python demos/demo.py              # Basic game demo
   ```

**Never consider a task complete until both pyright and ruff report zero errors** (or only acceptable warnings with proper justification).

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
