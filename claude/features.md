# Adding Features

## New Game Features
When adding new game features, work through the event-driven manager system:
1. **Game Logic**: Update appropriate manager or create new specialized manager in `src/game/`
2. **Event Integration**: Define new event types and emission points
3. **Render Data**: Add necessary data to render context in `src/core/renderable.py`  
4. **Rendering**: Update renderers to display the new data
5. **Manager Coordination**: Wire new managers into main `Game` class with EventManager
6. **Testing**: Add comprehensive unit tests for new functionality

## New Managers
When creating new manager systems:
1. **EventManager Dependency**: Always require EventManager as constructor parameter (never optional)
2. **Event Subscriptions**: Set up subscriptions in `_setup_event_subscriptions()` method
3. **Single Responsibility**: Each manager handles one major concern (combat, morale, hazards, etc.)
4. **Event Emission**: Publish events after state changes for coordination
5. **Unit Testing**: Design for isolation with EventManager mocks
6. **Clear Boundaries**: Define clean interfaces and responsibilities

## Combat System Extensions
The combat system has distinct separation of concerns:
- **`battle_calculator.py`** - Damage prediction (read-only, no state changes)
- **`combat_resolver.py`** - Actual combat execution (applies damage, generates wounds)
- **`combat_manager.py`** - UI integration and orchestration between the two
- **Timeline Integration**: Combat actions scheduled based on action weights

## New Renderer
When adding a new renderer:
1. Inherit from `Renderer` base class
2. Implement required methods: `initialize()`, `render_frame()`, `get_input_events()`, `cleanup()`
3. Register it in main entry point
4. All visual decisions (colors, symbols, sprites) belong in the renderer

## New Scenarios (Single-file Authoring)
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

## New Maps (Geometry Only)
1. Create directories in `assets/maps/` with CSV layers
2. Required: `ground.csv` with terrain tile IDs
3. Optional: `walls.csv`, `features.csv` for additional terrain layers
4. **Do NOT add**: units, objects, spawns, or gameplay elements
5. Terrain properties defined in `assets/tileset.yaml`