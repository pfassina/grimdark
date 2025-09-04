# Project Structure

Clean, organized layout for the Grimdark SRPG codebase.

## Directory Layout

```
grimdark/
├── src/                    # Core source code
│   ├── core/              # Architecture abstractions
│   │   ├── game_state.py  # Centralized state management
│   │   ├── input.py       # Generic input events
│   │   ├── renderable.py  # Data structures for rendering
│   │   ├── renderer.py    # Abstract renderer base class
│   │   ├── tileset_loader.py # Tileset configuration loader
│   │   ├── game_enums.py  # Centralized enums
│   │   ├── data_structures.py # Data conversion utilities
│   │   ├── game_info.py   # Game constants
│   │   ├── game_view.py   # Read-only game state adapter
│   │   └── events.py      # Game event definitions
│   ├── game/              # Game logic and managers
│   │   ├── game.py        # Main orchestrator
│   │   ├── input_handler.py    # User input processing
│   │   ├── combat_manager.py   # Combat coordination
│   │   ├── combat_resolver.py  # Combat execution
│   │   ├── battle_calculator.py # Damage prediction
│   │   ├── turn_manager.py     # Turn flow management
│   │   ├── ui_manager.py       # UI overlays and dialogs
│   │   ├── render_builder.py   # Render context building
│   │   ├── map.py         # Grid-based battlefield and CSV map loading
│   │   ├── scenario.py    # Scenario definitions and objectives
│   │   ├── scenario_loader.py # YAML scenario parsing
│   │   ├── objectives.py  # Victory/defeat condition implementations
│   │   ├── objective_manager.py # Event-driven objective tracking
│   │   ├── components.py  # Game component definitions
│   │   ├── map_objects.py # Map objects and spawn points
│   │   ├── unit_templates.py # Unit class definitions
│   │   ├── scenario_menu.py # Scenario selection
│   │   ├── tile.py        # Terrain types and effects
│   │   └── unit.py        # Character stats and properties
│   └── renderers/         # Rendering implementations
│       ├── simple_renderer.py   # Debug/testing renderer
│       └── terminal_renderer.py # Interactive terminal renderer
├── demos/                  # Demo scripts
│   ├── demo.py            # Auto-playing demo
│   ├── demo_scenario.py   # Scenario system demo
│   └── demo_map_loader.py # Map loading demo
├── tests/                  # Test scripts
│   ├── test_architecture.py # Core architecture validation
│   ├── test_objectives.py   # Scenario system tests
│   └── test_*.py            # Additional test files
├── assets/                 # Game assets
│   ├── maps/              # Map directories with CSV layers
│   │   ├── tutorial/      # Tutorial map
│   │   │   ├── ground.csv # Ground terrain layer
│   │   │   ├── walls.csv  # Walls layer
│   │   │   └── objects.yaml # Spawn points and objects
│   │   ├── fortress/      # Fortress siege map
│   │   └── sample/        # Simple test map
│   ├── scenarios/         # Scenario files (.yaml format)
│   │   ├── tutorial.yaml  # Combat tutorial
│   │   ├── fortress_defense.yaml # Fortress defense
│   │   ├── escape_mission.yaml   # Escape objective
│   │   └── default_test.yaml     # Default test scenario
│   ├── tileset.yaml       # Terrain properties and gameplay data
│   └── data/              # Additional game data
│       ├── units/         # Unit templates
│       ├── items/         # Item definitions
│       └── skills/        # Skill definitions
├── main.py                 # Interactive game entry point
├── README.md              # Complete project documentation
├── CLAUDE.md              # Development guidance
└── flake.*                # Nix development environment
```

## Key Files

### Entry Points
- **`main.py`** - Interactive terminal game
- **`demos/demo.py`** - Auto-playing demonstration
- **`demos/demo_scenario.py`** - Play specific YAML scenarios

### Testing
- **`tests/test_architecture.py`** - Core architecture validation
- **`tests/test_objectives.py`** - Scenario objectives testing
- **`tests/test_all_scenarios.py`** - Test all scenario loading

### Documentation
- **`README.md`** - Complete project documentation
- **`CLAUDE.md`** - Development commands and guidance

## Architecture Notes

### Manager-Based Design (2024 Refactor)
The `src/game/` directory now follows a **manager-based architecture**:
- **game.py** - Main orchestrator that coordinates all systems
- **6 specialized managers** - Each handles one major responsibility
- **Significant reduction** in main game file complexity
- **Clean separation**: Input, combat, UI, turns, rendering all isolated

### Manager Responsibilities
- **InputHandler** - All user input processing and routing
- **CombatManager** - Combat targeting and UI integration  
- **CombatResolver** - Actual damage application and unit removal
- **TurnManager** - Turn flow and team management
- **UIManager** - Overlays, dialogs, banners
- **RenderBuilder** - Converts game state to render contexts

## Benefits of This Structure

✓ **Clean Root**: Only essential files in project root  
✓ **Logical Grouping**: Related files organized together  
✓ **Easy Navigation**: Clear purpose for each directory  
✓ **Scalable**: Easy to add new demos/tests without cluttering  
✓ **Professional**: Industry-standard project layout  
✓ **Clear Separation**: Source code vs demos vs tests vs content  
✓ **Manager Architecture**: Single responsibility principle with clean interfaces  
✓ **Maintainable**: Easy to locate and modify specific functionality