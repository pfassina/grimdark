# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grimdark SRPG is a Strategy Role-Playing Game built in Python with a clean, renderer-agnostic architecture. The codebase demonstrates complete separation between game logic and rendering through a push-based, data-driven design.

**⚠️ ACTIVE DEVELOPMENT**: This project is under active development. Breaking changes are expected and backward compatibility is NOT maintained. Feel free to refactor, redesign, or enhance any part of the codebase as needed, as long as it doesn't violate the core architectural principles and design premises outlined below.

## Development Commands

```bash
# ===== NEW COMPREHENSIVE TEST SUITE =====
# Run all tests with the convenient test runner
python run_tests.py --help           # Show all available options
python run_tests.py --quick          # Quick unit tests (default)
python run_tests.py --all            # All tests with coverage report
python run_tests.py --unit           # Unit tests only
python run_tests.py --integration    # Integration tests only
python run_tests.py --performance    # Performance benchmarks
python run_tests.py --quality        # Code quality checks (pyright + ruff)
python run_tests.py --ci             # Full CI pipeline

# Or use pytest directly
nix develop --command pytest tests/                    # All tests
nix develop --command pytest tests/unit/               # Unit tests
nix develop --command pytest tests/integration/        # Integration tests
nix develop --command pytest tests/performance/        # Performance benchmarks
nix develop --command pytest --cov=src --cov-report=html  # With coverage


# ===== DEMOS AND INTERACTIVE PLAY =====
# Run auto-playing demo with simple renderer (uses default scenario)
python demos/demo.py

# Play interactive terminal version (uses default scenario) - NOTE: Requires interactive terminal
python main.py

# Play specific scenarios
python demos/demo_scenario.py assets/scenarios/tutorial.yaml
python demos/demo_scenario.py assets/scenarios/fortress_defense.yaml
python demos/demo_scenario.py assets/scenarios/escape_mission.yaml

# Load maps from CSV directories
python demos/demo_map_loader.py assets/maps/fortress

# ===== DEVELOPMENT TOOLS =====
# Update Nix flake dependencies
nix flake update --update-input nixpkgs

# Code quality and linting
nix develop --command pyright .                    # Type checking and error detection
nix develop --command ruff check .                 # Code linting and style checking
nix develop --command ruff check . --fix           # Auto-fix linting issues where possible
nix develop --command ruff check . --select ARG    # Check for unused function/method parameters
```

## Testing Workflow for Claude Code

**IMPORTANT**: `main.py` uses `TerminalRenderer` which requires an interactive terminal that Claude Code cannot access. For testing during development, use the comprehensive test suite:

### Comprehensive Test Suite (Recommended)

The project now includes a modern, comprehensive test suite using pytest with extensive coverage:

1. **Quick Testing**: `python run_tests.py --quick`
   - Runs unit tests only (fastest option)
   - Skips slow tests and benchmarks
   - Perfect for rapid development iteration

2. **Full Test Suite**: `python run_tests.py --all`
   - Unit tests, integration tests, performance tests
   - Coverage reporting (HTML + terminal)
   - Comprehensive validation of all systems

3. **Code Quality**: `python run_tests.py --quality`
   - Type checking with pyright
   - Linting with ruff
   - Unused parameter detection

4. **Performance Monitoring**: `python run_tests.py --performance`
   - Benchmarks critical game systems
   - Pathfinding, combat, rendering performance
   - Regression detection

5. **CI Pipeline**: `python run_tests.py --ci`
   - Complete continuous integration pipeline
   - All quality checks + functional tests

### Test Categories

- **Unit Tests** (`tests/unit/`): Individual component testing
  - Core data structures (Vector2, VectorArray, GameState)
  - Game logic (GameMap, Unit, combat systems)
  - Manager systems (InputHandler, CombatManager, etc.)

- **Integration Tests** (`tests/integration/`): System interaction testing
  - Combat system integration
  - Manager coordination
  - Full game loop testing

- **Performance Tests** (`tests/performance/`): Benchmark testing
  - Pathfinding performance
  - Combat resolution speed
  - Rendering context generation
  - Memory usage profiling

- **Edge Case Tests** (`tests/edge_cases/`): Boundary condition testing
  - Error handling and edge cases
  - Resource limits and extreme values
  - Data structure boundary conditions

### Testing New Features

When implementing new features:

1. **Write unit tests first** in appropriate `tests/unit/` subdirectory
2. **Add integration tests** if feature involves multiple systems
3. **Include performance tests** for computationally intensive features
4. **Update fixtures** in `tests/conftest.py` for reusable test components
5. **Run full test suite** with `python run_tests.py --all`

### Interactive Testing (For Visual Features)

For features requiring visual verification:

1. **Demo Scripts**: Create targeted demos in `demos/` directory for manual testing
2. **Scenario Testing**: Use scenario-specific demos for complex interactions
3. **Unit Testing**: Ensure all game logic is thoroughly tested without requiring visual verification

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
   - `game_view.py` - Read-only game state adapter for objectives system
   - `events.py` - Game event definitions for objective tracking

2. **Game Logic** (`src/game/`)
   - `game.py` - **Main orchestrator** that coordinates all game systems
   - `map.py` - Grid-based battlefield, pathfinding, visibility, CSV map loading
   - `unit.py` - Character stats and properties
   - `tile.py` - Terrain types and effects
   - `scenario.py` - Scenario definitions and objective types
   - `scenario_loader.py` - YAML scenario loading and parsing
   - `map_objects.py` - Map objects: spawn points, regions, triggers
   - `unit_templates.py` - Unit class definitions and stat templates
   - `scenario_menu.py` - Scenario selection and management

3. **Game Manager Systems** (`src/game/`)
   - `input_handler.py` - All user input processing and routing
   - `combat_manager.py` - Combat targeting, validation, and UI integration
   - `combat_resolver.py` - Actual combat execution and damage application
   - `battle_calculator.py` - Damage prediction and forecasting
   - `turn_manager.py` - Turn flow and team management
   - `ui_manager.py` - Overlays, dialogs, banners, and modal UI
   - `render_builder.py` - Render context construction from game state

4. **Objective System** (`src/game/`)
   - `objectives.py` - Victory/defeat condition implementations
   - `objective_manager.py` - Event-driven objective tracking
   - `components.py` - Game component definitions for ECS-like patterns

5. **Renderers** (`src/renderers/`)
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
- **Manager-based architecture** - Specialized manager classes handle distinct responsibilities
- **Dependency injection** - Managers receive dependencies through constructors for testability
- **Event-driven design** - Game events flow through the objective system for loose coupling

## Refactored Architecture (2024 Update)

The codebase has been **extensively refactored** from a monolithic design into a clean manager-based architecture:

### Before Refactoring
- **game.py**: Monolithic code with mixed responsibilities
- Difficult to maintain, test, and extend
- All concerns (input, combat, UI, rendering) intertwined in one class

### After Refactoring  
- **game.py**: Focused purely on orchestration
- **6 specialized managers**: Each handling distinct responsibilities
- **Significant reduction** in main game file complexity
- **Clear separation of concerns** with well-defined boundaries

### Manager System Design

The `Game` class now acts as a **coordinator** that:
1. **Initializes** all manager systems with proper dependencies
2. **Coordinates** communication between managers through callbacks
3. **Orchestrates** the main game loop and high-level state management
4. **Delegates** all specific concerns to appropriate managers

### Manager Dependencies Flow
```
Game (Orchestrator)
├── UIManager (overlays, dialogs, banners)
├── InputHandler (user input → game actions)
│   ├── → CombatManager (combat coordination)  
│   └── → UIManager (show/hide overlays)
├── CombatManager (combat orchestration)
│   ├── → CombatResolver (damage application)
│   └── → BattleCalculator (damage prediction)
├── TurnManager (turn flow, team switching)
├── RenderBuilder (game state → render context)
└── All managers → GameState (shared state)
```

### Key Architectural Benefits
1. **Single Responsibility**: Each manager handles exactly one major concern
2. **Testability**: Managers can be unit tested in isolation
3. **Maintainability**: Easy to locate and modify specific functionality
4. **Extensibility**: New managers can be added without touching existing code
5. **Collaboration**: Multiple developers can work on different systems simultaneously
6. **Code Reuse**: Managers can potentially be reused in different contexts

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
- **Placement system**: Uses `at: [y,x]`, `at_marker: NAME`, or `at_region: NAME`
- **Markers**: Named coordinate anchors for readability (`KNIGHT_POSITION: { at: [2,7] }`)
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

### New Game Features
When adding new game features, work through the manager system:
1. **Game Logic**: Update appropriate manager or create new specialized manager in `src/game/`
2. **Render Data**: Add necessary data to render context in `src/core/renderable.py`  
3. **Rendering**: Update renderers to display the new data
4. **Integration**: Wire new managers into main `Game` class orchestration
5. **Events**: Add game events if needed for objective system integration

### New Managers
When creating new manager systems:
1. **Single Responsibility**: Each manager handles one major concern (input, combat, UI, etc.)
2. **Dependency Injection**: Receive dependencies through constructor parameters
3. **Callback Pattern**: Use optional callbacks for coordination with main Game class
4. **Clear Interfaces**: Define clean boundaries between managers
5. **Testability**: Design for unit testing in isolation

### Combat System Extensions
The combat system has distinct separation of concerns:
- **`battle_calculator.py`** - Damage prediction (read-only, no state changes)
- **`combat_resolver.py`** - Actual combat execution (applies damage, removes units)
- **`combat_manager.py`** - UI integration and orchestration between the two

### New Renderer
When adding a new renderer:
1. Inherit from `Renderer` base class
2. Implement required methods: `initialize()`, `render_frame()`, `get_input_events()`, `cleanup()`
3. Register it in main entry point
4. All visual decisions (colors, symbols, sprites) belong in the renderer

### New Scenarios (Single-file Authoring)
1. Create YAML files in `assets/scenarios/` directory
2. Reference external CSV map directories with `map: { source: assets/maps/mapname }`
3. Define `units:` section with unit roster (classes, teams, stat overrides)
4. Define `objects:` section for interactive elements (healing fountains, doors, etc.)
5. Define `markers:` for named coordinate anchors (optional, for readability)
6. Define `regions:` for named rectangular areas (optional, for triggers/placement)
7. Define `placements:` section binding units/objects to coordinates using:
   - `at: [y,x]` for explicit coordinates
   - `at_marker: NAME` for marker-based placement
   - `at_region: NAME` for region-based placement (with policies)
8. Set `objectives:` for victory/defeat conditions
9. Configure `settings:` (turn limits, fog of war, etc.)
10. Add `map_overrides:` if environmental changes needed (bridges, gates, etc.)

### New Maps (Geometry Only)
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
   python run_tests.py --quick                             # Quick unit tests
   python run_tests.py --all                               # Full test suite
   ```

**Never consider a task complete until both pyright and ruff report zero errors** (or only acceptable warnings with proper justification).

## Testing

The comprehensive test suite validates different aspects:
- **Unit Tests** - Core components and game logic
- **Integration Tests** - System interactions and workflows
- **Performance Tests** - Benchmarks and regression detection
- **Edge Case Tests** - Boundary conditions and error handling

When adding features:
- Ensure all existing tests still pass
- Write comprehensive unit tests for new functionality
- Add integration tests for multi-system features
- Verify game logic works without any renderer (testability principle)
- Include performance benchmarks for computationally intensive features
