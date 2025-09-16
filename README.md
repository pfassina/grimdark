# Grimdark SRPG - Timeline-Based Strategy Game

A grimdark Strategy RPG featuring timeline-based combat, persistent consequences, and event-driven architecture. Built in Python with clean separation between game logic and rendering.

## What This Game Is

Grimdark SRPG implements **tactical depth through time management** where every action has temporal consequences. Instead of traditional turn-based phases, units act on a **fluid timeline** based on action weights and speed. Fast units with quick actions can act multiple times before slow units with heavy actions get their turn.

**Core Principles:**
- **Timeline-based Combat**: Action weights determine when units act next
- **Persistent Consequences**: Wounds and morale carry across battles  
- **Information Warfare**: Hidden enemy intents create tactical uncertainty
- **Environmental Chaos**: Dynamic hazards make battlefields dangerous
- **No Perfect Victories**: Success means survival, not domination

## Architecture Overview

The system uses an **event-driven architecture** with timeline-based combat flow:

### Timeline System
- **Priority Queue**: Units scheduled by execution time (current_time + speed + action_weight)
- **Action Categories**: Quick (50-80), Normal (100), Heavy (150-200+), Prepared (120-140) weight
- **Discrete Ticks**: Integer time values for deterministic, reproducible behavior
- **Mixed Turns**: Player and AI units intermixed based on timeline, not phases

### Event-Driven Communication
- **EventManager**: Central message bus replacing direct manager dependencies
- **Publisher-Subscriber**: Managers communicate through events, not direct calls
- **Loose Coupling**: Each manager only knows EventManager and GameState
- **Event Types**: Timeline, Combat, Input, UI, System events with rich payloads

### Component-Based Units
- **ECS-like Design**: Units have modular components (Health, Movement, Combat, Morale, Wounds)
- **Vector2 Positioning**: Modern spatial operations with vectorized calculations
- **Status Effects**: Wounds, morale states, and environmental effects affect gameplay

## Key Systems

### Combat Resolution
- **Guaranteed Hits**: No hit/miss RNG, focus on positioning and timing
- **Damage Variance**: ±25% variance for unpredictability without extremes
- **Wound Generation**: Damage creates persistent injuries with body part targeting
- **Morale Integration**: Combat damage affects unit psychological state

### Morale & Psychology (WIP)
- **Individual Morale**: Each unit has base morale (0-150) with situational modifiers
- **Panic States**: Normal → Panicked → Routed with different recovery thresholds
- **Proximity Effects**: Ally deaths reduce morale, enemy deaths boost confidence
- **Combat Penalties**: Panicked units suffer attack/defense reductions

### Environmental Hazards (WIP)
- **Timeline Integration**: Hazards act on timeline entries with configurable weights
- **Spreading Mechanics**: Fire spreads to flammable materials, poison follows wind patterns
- **Dynamic Effects**: Collapsing terrain gives warnings then becomes impassable
- **Damage and Status**: Hazards apply damage, movement penalties, and visibility reduction

### Information Warfare - Hidden Intents (WIP)
- **Hidden Intents**: Enemy actions revealed gradually based on distance and time
- **Three Visibility Levels**: Hidden ("???"), Partial ("Preparing Attack"), Full ("Sword Strike → Knight")
- **Deception System**: Units can show false intents until exposed through proximity
- **Observer-Relative**: Intent visibility varies based on observing unit's position

### Wound & Scarring (WIP)
- **Persistent Injuries**: Wounds carry across battles and can become permanent scars
- **Body Part System**: Wounds affect specific parts (head, torso, arms, legs) with realistic penalties
- **Treatment System**: Medical intervention affects healing outcomes and scarring chances
- **Severity Levels**: Minor to Mortal wounds with escalating consequences

## Project Structure

### Core Systems (`src/core/`)
- **`timeline.py`**: Timeline queue and entry management
- **`actions.py`**: Action class hierarchy with weight categories
- **`events.py`**: Event definitions for inter-system communication
- **`event_manager.py`**: Publisher-subscriber event routing
- **`wounds.py`**: Wound types, severity, and healing mechanics
- **`hazards.py`**: Environmental hazard base classes and effects
- **`hidden_intent.py`**: Information warfare and intent revelation
- **`game_state.py`**: Centralized state management
- **`renderable.py`**: Data classes for renderer-agnostic display

### Game Logic (`src/game/`)
- **`game.py`**: Main orchestrator coordinating all manager systems
- **`timeline_manager.py`**: Timeline processing and unit activation
- **`combat_manager.py`**: Combat targeting, validation, and UI integration
- **`combat_resolver.py`**: Damage application and wound generation
- **`morale_manager.py`**: Morale calculations and panic state management
- **`hazard_manager.py`**: Environmental hazard processing and spreading
- **`escalation_manager.py`**: Time pressure through reinforcements and deterioration
- **`ai_controller.py`**: Timeline-aware AI with personality types
- **`input_handler.py`**: User input processing and action routing
- **`ui_manager.py`**: Overlays, dialogs, and modal UI state

### Map and Content (`src/game/`)
- **`map.py`**: Grid-based battlefield with vectorized operations and pathfinding
- **`unit.py`**: Component-based units with Vector2 positioning
- **`components.py`**: ECS-like components (Actor, Health, Movement, Combat, Morale, Wound)
- **`scenario_loader.py`**: YAML scenario parsing and game state initialization

### Renderers (`src/renderers/`)
- **`terminal_renderer.py`**: Interactive ASCII terminal interface
- **`simple_renderer.py`**: Minimal demo renderer for testing

## Getting Started

### Development Environment
This project uses Nix for development dependencies:

```bash
# Enter development shell (includes Python 3.11, pyright, ruff)
nix develop

# Or run commands directly
nix develop --command python run_tests.py
```

### Running the Game
```bash
# Interactive terminal gameplay (requires terminal that supports cursor control)
python main.py

# Unit tests (primary development workflow)
python run_tests.py                  # All tests with verbose output
python run_tests.py --quiet          # Minimal output
python run_tests.py --test timeline  # Specific test file
python run_tests.py --all            # Tests + linting + type checking
```

### Code Quality
```bash
# Type checking
nix develop --command pyright .

# Linting and formatting
nix develop --command ruff check . --fix  # Auto-fix issues
nix develop --command ruff check .        # Check remaining issues
```

### Development Testing
**Important**: `main.py` requires an interactive terminal that Claude Code cannot access. For development validation, use the unit test suite:

- **Default Testing**: `python run_tests.py` - runs all unit tests with verbose output
- **Specific Systems**: `python run_tests.py --test <name>` - test individual components
- **Full Validation**: `python run_tests.py --all` - tests + linting + type checking

## Asset System - Scenario-First Design

### Scenario Creation
Scenarios are the single source of truth for gameplay content. Create YAML files in `assets/scenarios/`:

```yaml
name: "Battle Name"
map:
  source: assets/maps/fortress        # References CSV map directory
units:
  - name: "Knight"
    class: KNIGHT
    team: PLAYER
    stats: { strength: 12, defense: 8 }  # Optional overrides
objects:
  - name: "Healing Fountain"
    type: HEALING_FOUNTAIN
placements:
  - unit: "Knight"
    at: [2, 5]                        # Direct coordinates
  - object: "Healing Fountain"  
    at_marker: FOUNTAIN_POSITION      # Named marker reference
markers:
  FOUNTAIN_POSITION: { at: [10, 10] } # Named coordinate anchors
objectives:
  victory:
    - type: defeat_all_enemies
  defeat:
    - type: all_units_defeated
settings:
  turn_limit: 20
  fog_of_war: false
```

### Map System (Geometry Only)
Maps contain only terrain geometry as CSV layers:

```
assets/maps/fortress/
├── ground.csv      # Required: base terrain tile IDs
├── walls.csv       # Optional: wall/obstacle layer  
└── features.csv    # Optional: terrain features
```

**No units, objects, or spawns in maps** - those belong in scenarios.

### Terrain Configuration
`assets/tileset.yaml` defines terrain properties:
```yaml
terrain_types:
  FOREST:
    tile_id: 2
    movement_cost: 2
    defense_bonus: 1
    flammable: true
```

## Game Controls (Terminal Version)

- **Arrow Keys/WASD**: Move cursor or unit
- **Enter/Space**: Confirm action or movement
- **W**: Quick wait (end turn immediately)
- **A**: Quick attack (skip to targeting)
- **X/Escape**: Cancel current action
- **L**: Toggle expanded combat log
- **Q**: Quit game

## Timeline Combat Flow

1. **Timeline Processing**: Next unit/hazard from priority queue activates
2. **Unit Turn**: Player selects movement and action with weight preview
3. **Action Execution**: Combat resolution with wound generation and morale effects
4. **Rescheduling**: Unit added back to timeline at `current_time + action_weight`
5. **Event Processing**: Systems react to combat through event subscriptions

**Action Weight Examples:**
- Quick Strike: 60 weight (fast, weak)
- Standard Attack: 100 weight (balanced) 
- Power Attack: 180 weight (slow, strong)
- Prepare Interrupt: 130 weight (sets up reaction)

## Dependencies

- **Python 3.11+** (managed through Nix)
- **numpy** - efficient grid operations and vectorized calculations
- **pyyaml** - scenario and configuration loading
- **Nix** - development environment and dependency management

**Runtime**: No graphics libraries required - terminal renderer uses only standard library.

## Testing

The codebase includes 475+ unit tests covering:
- **Timeline System**: Queue operations, scheduling, and edge cases
- **Action System**: Weight calculations, validation, and execution
- **Combat Resolution**: Damage variance, wound generation, morale integration
- **Event System**: Publisher-subscriber communication and event ordering
- **Manager Integration**: Cross-system coordination through events

Run `python run_tests.py --all` to validate functionality, code quality, and type safety.