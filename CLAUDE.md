# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grimdark SRPG is a timeline-based Strategy RPG built in Python with event-driven architecture and renderer-agnostic design. The codebase demonstrates complete separation between game logic and rendering through a timeline-based combat system where tactical depth comes from time management.

**⚠️ ACTIVE DEVELOPMENT**: This project is under active development. Breaking changes are expected and backward compatibility is NOT maintained. Feel free to refactor, redesign, or enhance any part of the codebase as needed, as long as it doesn't violate the core architectural principles and design premises outlined below.

## Development Commands

```bash
# ===== SIMPLE UNIT TESTING =====
# Run all unit tests (primary testing method)
python run_tests.py                  # Run all unit tests with verbose output
python run_tests.py --quiet          # Run tests with minimal output
python run_tests.py --test timeline  # Run specific test file (test_timeline.py)
python run_tests.py --lint           # Run code linting only
python run_tests.py --types          # Run type checking only  
python run_tests.py --all            # Run tests + linting + type checking
python run_tests.py --help           # Show all available options

# Or use pytest directly
nix develop --command pytest tests/                    # All unit tests
nix develop --command pytest tests/test_timeline.py    # Specific test file
nix develop --command pytest tests/ -v                 # Verbose output

# ===== INTERACTIVE PLAY =====
# Play interactive terminal version (uses default scenario) - NOTE: Requires interactive terminal
python main.py

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

**IMPORTANT**: `main.py` uses `TerminalRenderer` which requires an interactive terminal that Claude Code cannot access. For testing during development, use the unit test suite:

### Simple Unit Testing (Recommended)

The project uses a streamlined unit testing approach focused on the timeline-based architecture:

1. **Default Testing**: `python run_tests.py`
   - Runs all unit tests with verbose output
   - Tests core systems: Timeline, EventManager, Data Structures, Components, Managers
   - Perfect for development validation

2. **Specific Tests**: `python run_tests.py --test <name>`
   - Run individual test files (e.g., `--test timeline` for test_timeline.py)
   - Useful for focused development on specific systems

3. **Code Quality**: `python run_tests.py --all`
   - Unit tests + linting (ruff) + type checking (pyright)
   - Ensures both functionality and code quality

### Test Structure - **Mirrors the package hierarchy**

- **Core Tests** (`tests/core/`) - **Foundation systems with comprehensive coverage**
  - `tests/core/engine/test_timeline.py`: Core Timeline system tests
  - `tests/core/engine/test_actions.py`: Complete action hierarchy, validation, execution (56 tests)
  - `tests/core/events/test_event_manager.py`: Event Manager and communication tests
  - `tests/core/data/test_data_structures.py`: Vector2, GameState, and core data tests
- **Game Tests** (`tests/game/`) - **Game logic systems with extensive coverage**
  - `tests/game/test_game.py`: Game orchestrator, manager coordination, lifecycle (20 tests)
  - `tests/game/entities/test_components.py`: Unit components and ECS system tests
  - `tests/game/managers/test_managers.py`: Manager systems and integration tests
  - `tests/game/combat/test_combat_resolver.py`: Combat execution, damage, wounds (23 tests)
  - `tests/game/combat/test_battle_calculator.py`: Damage prediction, forecasting (30 tests)
- **Test Utilities**
  - `tests/conftest.py`: Basic fixtures and test utilities

**Note**: Test structure mirrors the source code package organization for easier navigation and maintenance. **Recent expansion added 129 new tests** covering critical systems previously untested.

### Testing New Features

When implementing new features:

1. **Write unit tests** in the appropriate test file or create a new one
2. **Update fixtures** in `tests/conftest.py` if needed for reusable test components  
3. **Run tests** with `python run_tests.py` to validate functionality
4. **Check code quality** with `python run_tests.py --all`

### Test Design Principles

- **Focus on unit testing**: Test individual components and systems in isolation
- **Mock external dependencies**: Use mocks for complex dependencies to keep tests fast and focused
- **Test the timeline architecture**: Emphasize testing the new timeline and event-driven systems
- **Simple and maintainable**: Keep tests straightforward and easy to understand
- **Type safety compliance**: All tests must pass pyright type checking with 0 errors
- **Mock unit compatibility**: Use `# type: ignore[arg-type]` for MockUnit parameters when needed
- **Comprehensive coverage**: New major systems require 85%+ test coverage before merge

## Development Environment

- This repository uses a Nix flake for development. You need to explicitly call it when running python scripts.
- Run commands with `nix develop` prefix for the development shell
- The development environment includes:
  - Python 3.11 with required packages (numpy, pandas, pyyaml)
  - **Pyright** for static type checking
  - **Ruff** for fast linting and code formatting
  - All development tools are pre-configured and ready to use

## Architecture

The system uses an **event-driven architecture** with timeline-based combat flow where game logic and rendering are completely separated:

- **Game logic** updates state and builds a `RenderContext` containing all renderable data
- **Renderers** receive the context and draw it using their own implementation
- **Communication** happens through EventManager for inter-system coordination
- **Timeline system** replaces traditional turn-based phases with fluid action-weight scheduling

### Core Architecture Principles

- **Event-Driven Communication**: All managers communicate through EventManager, never direct dependencies
- **Timeline-Based Combat**: Action weights determine when units act next, creating tactical depth through time management
- **Hybrid Component System**: ECS with type-safe Unit wrapper providing clean property access and component management
- **Push-Based Rendering**: Game builds render contexts, renderers display them independently
- **Single Source of Truth**: GameState holds all persistent data, EventManager coordinates behavior

### Timeline System

- **Priority Queue**: Units scheduled by execution time (current_time + speed + action_weight)
- **Action Categories**: Quick (50-80), Normal (100), Heavy (150-200+), Prepared (120-140) weight
- **Discrete Ticks**: Integer time values for deterministic, reproducible behavior
- **Mixed Turns**: Player and AI units intermixed based on timeline, not phases
- **Event Integration**: Timeline events trigger manager reactions through EventManager

### Event-Driven Communication

- **EventManager**: Central message bus replacing all direct manager dependencies
- **Publisher-Subscriber**: Managers emit events, subscribe to relevant events only
- **Loose Coupling**: Each manager only knows EventManager and GameState
- **Event Types**: Timeline, Combat, Input, UI, System events with rich payloads
- **Required Dependency**: EventManager is mandatory constructor parameter for all managers

### Core Components

1. **Core Layer** (`src/core/`) - **Organized into focused subpackages**
   - **Engine** (`src/core/engine/`)
     - `timeline.py` - Timeline queue and entry management for fluid turn order
     - `actions.py` - Action class hierarchy with weight categories and validation
     - `game_state.py` - Centralized state management
   - **Events** (`src/core/events/`)
     - `events.py` - Event definitions for inter-system communication
     - `event_manager.py` - Publisher-subscriber event routing and coordination
   - **Entities** (`src/core/entities/`)
     - `components.py` - Base Component and Entity classes for ECS system
     - `renderable.py` - Data classes for renderable entities (NO game logic)
   - **Data** (`src/core/data/`)
     - `data_structures.py` - Vector2 and VectorArray for efficient spatial operations
     - `game_enums.py` - Centralized enums for teams, unit classes, terrain types, and ComponentType for type-safe ECS
     - `game_info.py` - Static game data and lookup tables
   - **Other** (remaining in core root)
     - `renderer.py` - Abstract base class all renderers must implement
     - `input.py` - Generic input events (renderer-agnostic)
     - `wounds.py` - Wound types, severity, and healing mechanics **(WIP)**
     - `hazards.py` - Environmental hazard base classes and spreading effects **(WIP)**
     - `hidden_intent.py` - Information warfare and intent revelation system **(WIP)**

2. **Game Logic** (`src/game/`) - **Organized into focused subpackages**
   - **Core Game Files** (in `src/game/` root)
     - `game.py` - **Main orchestrator** that coordinates all manager systems through EventManager
     - `map.py` - Grid-based battlefield with vectorized operations, pathfinding, CSV map loading
     - `tile.py` - Tile data structures and terrain handling
     - `input_handler.py` - User input processing and action routing
     - `render_builder.py` - Render context construction from game state
   - **Managers** (`src/game/managers/`)
     - `timeline_manager.py` - Timeline processing, unit activation, and turn flow coordination
     - `combat_manager.py` - Combat targeting, validation, and UI integration
     - `morale_manager.py` - Morale calculations, panic state management **(WIP)**
     - `hazard_manager.py` - Environmental hazard processing and timeline integration **(WIP)**
     - `escalation_manager.py` - Time pressure through reinforcements **(WIP)**
     - `ui_manager.py` - Overlays, dialogs, banners, and modal UI state
     - `scenario_manager.py` - Scenario loading, map creation, and game state initialization
     - `selection_manager.py` - Cursor positioning and unit selection state management
     - `objective_manager.py` - Event-driven objective tracking
     - `phase_manager.py` - Game phase transitions and state management
     - `log_manager.py` - Logging and debug message handling
   - **Combat** (`src/game/combat/`)
     - `combat_resolver.py` - Damage application, wound generation, and combat execution
     - `battle_calculator.py` - Damage prediction and forecasting (read-only)
   - **AI** (`src/game/ai/`)
     - `ai_controller.py` - Timeline-aware AI with personality types and tactical assessment
     - `ai_behaviors.py` - AI behavior patterns and decision-making logic
   - **Entities** (`src/game/entities/`)
     - `unit.py` - Hybrid Unit wrapper with type-safe component access and clean property interface
     - `components.py` - Type-safe ECS components using ComponentType enum (Actor, Health, Movement, Combat, Morale, Wound, Interrupt)
     - `unit_templates.py` - Unit class definitions and base stats
     - `map_objects.py` - Interactive map objects and environmental elements
   - **Scenarios** (`src/game/scenarios/`)
     - `scenario_loader.py` - YAML scenario parsing and game state initialization
     - `scenario.py` - Scenario data structures and validation
     - `scenario_structures.py` - Data classes for scenario definitions
     - `scenario_menu.py` - Scenario selection interface
     - `objectives.py` - Victory/defeat condition implementations
   - **Systems** (`src/game/systems/`)
     - `interrupt_system.py` - Prepared actions and reaction system **(WIP)**

3. **Renderers** (`src/renderers/`)
   - Each renderer independently decides HOW to display the render context
   - Terminal renderer uses ASCII characters
   - New renderers (pygame, web, etc.) can be added without touching game code

### Manager System Design

The `Game` class acts as a **lean coordinator** that:
1. **Initializes** all manager systems with EventManager and GameState dependencies
2. **Coordinates** communication between managers through EventManager
3. **Orchestrates** the main game loop and high-level state management
4. **Delegates** all specific concerns to specialized managers

### Core Manager Responsibilities

- **ScenarioManager**: Scenario loading, map creation, unit placement, and objective system initialization
- **SelectionManager**: Cursor positioning, unit selection state, and selection validation
- **TimelineManager**: Timeline processing, unit activation, turn flow, and AI coordination
- **CombatManager**: Combat targeting, validation, UI integration, and action execution
- **UIManager**: Modal overlays, dialogs, banners, and UI state management
- **InputHandler**: User input processing, action routing, and input context management

### Manager Communication Flow
```
All Managers → EventManager ← All Managers
     ↓               ↓             ↑
GameState       Event Routing   Event Subscriptions
(shared data)   (coordination)  (reactive behavior)
```

### Key Architectural Benefits
1. **Single Responsibility**: Each manager handles exactly one major concern
2. **Testability**: Managers can be unit tested in isolation with EventManager mocks
3. **Maintainability**: Easy to locate and modify specific functionality
4. **Extensibility**: New managers can be added without touching existing code
5. **Event Traceability**: All communication is traceable through event emissions

## Mandatory Development Workflow

### **Code Quality Enforcement (CRITICAL)**

**ZERO TOLERANCE POLICY**: Always complete any coding task by running both linting tools and fixing ALL diagnostic errors:

1. **Run pyright for type checking**:
   ```bash
   nix develop --command pyright .
   ```
   - Fix ALL type errors, undefined variables, and import issues
   - Use proper type annotations and Optional types
   - Resolve circular imports with TYPE_CHECKING pattern
   - Use ComponentType enum for type-safe component access
   - **No exceptions**: Every type error must be resolved

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

3. **Update unit tests**:
   ```bash
   python run_tests.py                       # Verify all tests pass
   python run_tests.py --all                 # Full validation
   ```
   - **Required**: Update unit tests for every code change
   - Add new tests for new functionality
   - Ensure existing tests still pass
   - Test event-driven interactions properly

4. **Update documentation**:
   - **Required**: Update CLAUDE.md and README.md when affecting system behavior or architecture
   - Document new event types and manager responsibilities
   - Update development patterns and workflows

**Never consider a task complete until pyright and ruff report zero errors AND tests pass AND documentation is updated.**

### **Best Practices Enforcement**

**Write Simple, Readable, Maintainable Code**:
- **Prefer early returns and guard clauses** over deep nesting
- **Avoid defensive programming** that obscures actual errors - let errors surface clearly
- **Keep functions focused** on single responsibilities
- **Use descriptive variable and function names**
- **Limit indentation levels** - prefer flat code structure

**Anti-Patterns to Avoid**:
- ❌ **Multiple levels of indentation**: Use early returns instead
- ❌ **Defensive try/catch blocks**: Let errors propagate with clear messages
- ❌ **Direct manager-to-manager dependencies**: Use EventManager only
- ❌ **Complex nested structures**: Break into smaller, focused functions
- ❌ **Optional EventManager parameters**: EventManager is always required

**Event-Driven Patterns to Follow**:
- ✅ **Emit events after state changes**: `self.event_manager.publish(UnitMoved(...))`
- ✅ **Subscribe to relevant events**: `self.event_manager.subscribe(EventType.UNIT_MOVED, self._handle_unit_moved)`
- ✅ **Include rich event payloads**: Provide full context in event data
- ✅ **Use event priorities**: Critical events (combat) before UI updates

## Timeline-Based Development Patterns

### **Adding New Actions**

1. **Create Action Class** in `src/core/actions.py`:
   ```python
   class NewAction(Action):
       category = ActionCategory.NORMAL
       base_weight = 100
       
       def validate(self, unit, target, game_map) -> ActionValidation:
           # Validation logic
           
       def execute(self, unit, target, game_map) -> ActionResult:
           # Execution logic
           # Emit events for side effects
   ```

2. **Consider Action Weight**: 
   - Quick (50-80): Fast, weak actions
   - Normal (100): Standard balanced actions
   - Heavy (150-200+): Slow, powerful actions
   - Prepared (120-140): Set up interrupts/reactions

3. **Emit Appropriate Events**: Actions should emit events for state changes

### **Working with Timeline System**

- **Timeline Scheduling**: Units added at `current_time + action_weight`
- **Event Integration**: Timeline events trigger through EventManager
- **Mixed Turn Order**: Player and AI units intermixed based on execution time
- **Discrete Ticks**: Use integer time values for deterministic behavior

### **Component-Based Development**

The game uses a hybrid Entity-Component System with a clean Unit wrapper for type-safe access:

#### **Component Architecture**
- **ComponentType Enum**: Type-safe component identification replacing string-based access
- **Entity + Components**: Core ECS with Actor, Health, Movement, Combat, Status components
- **Unit Wrapper**: High-level interface providing both direct properties and component access
- **Optional Components**: Morale, Wound, Interrupt, AI components for extended functionality

#### **Unit Access Patterns**
```python
# Direct property access (most frequent operations)
unit.x = 5                    # Position access
unit.hp_current = 20          # Health access
if unit.is_alive and unit.can_move:  # Status checks
    # Perform action

# Component access (less frequent operations)
unit.combat.strength = 10     # Combat stats
unit.health.hp_max = 25       # Health configuration
unit.actor.unit_class         # Unit classification
unit.morale.modify_morale(-5, "fear")  # Optional components
```

#### **Component Management**
```python
# Adding optional components dynamically
morale_comp = MoraleComponent(unit.entity)
unit.add_component(morale_comp)

# Type-safe component checking
if unit.has_component(ComponentType.MORALE):
    unit.morale.modify_morale(5, "victory")

# Component removal
unit.remove_component(ComponentType.WOUND)
```

#### **Key Components**
- **Actor Component**: Identity, team affiliation, unit class information
- **Health Component**: HP management, life/death state, damage tracking
- **Movement Component**: Position, facing, movement points, mobility
- **Combat Component**: Attack/defense stats, damage calculation, range validation
- **Status Component**: Turn state, action availability, temporary effects
- **Morale Component**: Psychological state affecting combat effectiveness (optional)
- **Wound Component**: Persistent injuries affecting unit performance (optional)
- **Interrupt Component**: Prepared actions and reaction capabilities (optional)
- **AI Component**: Behavior patterns and decision-making logic (optional)

### **Action Validation System**

The game uses a unified validation system through Action classes for consistent behavior:

#### **Validation Architecture**
- **Single Validation Path**: All attack/action validation goes through Action classes, not component methods
- **Action.validate()**: Returns ActionValidation with detailed validation results
- **Consistent Logic**: Same validation used by both player input and AI decision-making
- **Type Safety**: Actions use Unit objects directly, not Entity references

#### **Validation Examples**
```python
# AI decision making (unified with player actions)
attack_action = StandardAttack()
validation = attack_action.validate(unit, game_map, target_position)
if validation.is_valid:
    # Execute attack
    result = attack_action.execute(unit, target_position, game_map)

# Component separation of concerns
# ❌ Old approach: unit.combat.can_attack(target) - mixed health/status checks
# ✅ New approach: Action handles all validation logic consistently
```

#### **Component Responsibilities**
- **Components**: Manage their own state and properties only
- **Actions**: Handle complex validation logic and cross-component coordination
- **Unit Class**: Provides convenient property access and basic status queries
- **Managers**: Use Action validation for consistent behavior across systems

### **Manager Integration**

When creating new managers:
1. **Require EventManager**: Always mandatory constructor parameter
2. **Subscribe to Events**: Set up event subscriptions in `_setup_event_subscriptions()`
3. **Emit State Changes**: Publish events after modifying GameState
4. **Single Responsibility**: Each manager handles one major concern
5. **Unit Testing**: Design for isolation with EventManager mocks

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
When adding new game features, work through the event-driven manager system:
1. **Game Logic**: Update appropriate manager or create new specialized manager in `src/game/`
2. **Event Integration**: Define new event types and emission points
3. **Render Data**: Add necessary data to render context in `src/core/renderable.py`  
4. **Rendering**: Update renderers to display the new data
5. **Manager Coordination**: Wire new managers into main `Game` class with EventManager
6. **Testing**: Add comprehensive unit tests for new functionality

### New Managers
When creating new manager systems:
1. **EventManager Dependency**: Always require EventManager as constructor parameter (never optional)
2. **Event Subscriptions**: Set up subscriptions in `_setup_event_subscriptions()` method
3. **Single Responsibility**: Each manager handles one major concern (combat, morale, hazards, etc.)
4. **Event Emission**: Publish events after state changes for coordination
5. **Unit Testing**: Design for isolation with EventManager mocks
6. **Clear Boundaries**: Define clean interfaces and responsibilities

### Combat System Extensions
The combat system has distinct separation of concerns:
- **`battle_calculator.py`** - Damage prediction (read-only, no state changes)
- **`combat_resolver.py`** - Actual combat execution (applies damage, generates wounds)
- **`combat_manager.py`** - UI integration and orchestration between the two
- **Timeline Integration**: Combat actions scheduled based on action weights

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
- **Avoid deep nesting**: Use early returns and guard clauses
- **Keep code flat**: Prefer simple, linear flow over complex nested structures

### Code Quality Tools
- **Pyright**: Static type checker for comprehensive type analysis
- **Ruff**: Fast Python linter for code style and quality issues
- Both tools are included in the Nix development environment
- Use `TYPE_CHECKING` imports to resolve circular dependency issues

## Documentation Guidelines

**Maintain Documentation**: Always update CLAUDE.md and README.md when making code changes that affect system behavior or architecture.

- **Update after changes**: When refactoring, adding features, or changing APIs, update relevant documentation
- **Keep it practical**: Focus on how the system works, not marketing language or aspirations
- **Be objective**: Document actual implementation and behavior, avoid verbose descriptions
- **Explain usage**: Include practical examples and workflow guidance for developers

Documentation should help developers understand and work with the system effectively.

## Testing

The comprehensive test suite validates different aspects with **extensive coverage** of critical systems:

### Current Test Coverage (238+ tests)
- **Core Engine Tests** (84+ tests) - Foundation systems
  - **Actions System** (56 tests) - Complete action hierarchy, validation, execution, timeline integration
  - **Timeline System** (14 tests) - Priority queue, scheduling, time management
  - **Event System** (14+ tests) - Publisher-subscriber communication patterns
- **Game Logic Tests** (154+ tests) - Core gameplay systems  
  - **Game Orchestrator** (20 tests) - Manager coordination, initialization, lifecycle
  - **Combat Systems** (53 tests) - Battle execution, damage calculation, forecasting
  - **Component System** (30+ tests) - ECS architecture, unit management
  - **Manager Systems** (51+ tests) - Individual manager functionality in isolation

### Critical Systems Coverage
- ✅ **Actions System**: ~95% coverage - All action types, validation, execution
- ✅ **Game Orchestrator**: ~90% coverage - Manager wiring, event coordination
- ✅ **Combat Systems**: ~85% coverage - Damage resolution, battle forecasting
- ✅ **Timeline System**: ~90% coverage - Priority scheduling, turn management
- ✅ **Event System**: ~85% coverage - Publisher-subscriber patterns

### Testing Requirements
When adding features:
- **Update unit tests** for every code change (mandatory)
- Write comprehensive unit tests for new functionality
- Add integration tests for multi-system features
- Test event-driven interactions properly
- Verify game logic works without any renderer (testability principle)
- Include performance benchmarks for computationally intensive features

### Event-Driven Testing Patterns
- Mock EventManager for isolated unit tests
- Test event emission and subscription patterns
- Verify event payloads contain required data
- Test event ordering and priority handling
- Use type ignore comments for MockUnit compatibility: `# type: ignore[arg-type]`

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
