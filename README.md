# Grimdark SRPG - Renderer-Agnostic Architecture

A clean, extensible Strategy RPG game architecture in Python with complete separation between game logic and rendering.

## Architecture Overview

The system uses a **push-based, data-driven rendering architecture** where:
- Game logic knows nothing about HOW things are rendered
- Renderers only know WHAT to render, not game rules
- Communication happens through simple data structures
- Input handling is abstracted and renderer-independent

## Key Components

### Core Abstractions (`src/core/`)
- **`renderable.py`**: Data classes for anything that can be rendered (tiles, units, UI)
- **`renderer.py`**: Abstract base class that all renderers implement
- **`input.py`**: Generic input event system
- **`game_state.py`**: Centralized game state management

### Game Logic (`src/game/`) - Manager-Based Architecture
- **`game.py`**: Main orchestrator coordinating all game systems
- **`input_handler.py`**: All user input processing and routing
- **`combat_manager.py`**: Combat targeting and UI integration
- **`combat_resolver.py`**: Actual combat execution and damage
- **`turn_manager.py`**: Turn flow and team management
- **`ui_manager.py`**: Overlays, dialogs, and banners
- **`render_builder.py`**: Converts game state to render contexts
- **`map.py`**: Grid-based battlefield with pathfinding, CSV map loading
- **`scenario.py`**: Scenario definitions and victory/defeat objectives
- **`scenario_loader.py`**: YAML scenario loading and parsing

### Renderer Implementations (`src/renderers/`)
- **`terminal_renderer.py`**: Interactive terminal-based renderer
- **`simple_renderer.py`**: Demo renderer for testing

## Quick Start

```bash
# Run demo with auto-playing simple renderer (uses default scenario)
python demos/demo.py

# Play interactively in terminal (uses default scenario)
python main.py

# Play specific scenarios
python demos/demo_scenario.py assets/scenarios/tutorial.yaml
python demos/demo_scenario.py assets/scenarios/fortress_defense.yaml

# Load maps from CSV directories
python demos/demo_map_loader.py assets/maps/fortress
```

## How It Works

1. **Game Updates**: Game logic updates based on input and time
2. **Build Context**: Game builds a `RenderContext` with all visible entities
3. **Render**: Renderer draws the context using its own implementation
4. **Input**: Renderer captures input and passes generic events to game

### Example Flow
```python
# Game builds render context
context = RenderContext()
context.tiles = [TileRenderData(x=0, y=0, terrain_type="forest")]
context.units = [UnitRenderData(x=5, y=5, unit_type="knight", team=0)]

# Renderer draws it however it wants
renderer.render_frame(context)  # Terminal shows "F" and "@"
                                # Pygame could show sprites
                                # Web could show SVG
```

## Game Controls (Terminal Version)

- **Arrow Keys/WASD**: Move cursor
- **Z/Space/Enter**: Confirm/Select
- **X/Escape**: Cancel/Back
- **Q**: Quit game

## Scenario System

The game supports YAML-based scenarios that define maps, unit placement, and objectives:

### Creating Scenarios
Create YAML files in `assets/scenarios/` directory with:
```yaml
name: "Scenario Name"
map:
  source: assets/maps/map_directory
units:
  - name: "Hero"
    class: KNIGHT
    team: PLAYER
    position: [y, x]
objectives:
  victory:
    - type: defeat_all_enemies
  defeat:
    - type: all_units_defeated
```

## Dependencies

- Python 3.11+
- numpy (for efficient grid operations)
- No graphics dependencies in core (renderer-specific only)
