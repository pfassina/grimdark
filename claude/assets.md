# Asset System - Scenario-First Design

The game uses a **scenario-first asset system** where scenarios are the single source of truth for all gameplay content (units, objects, placements), while maps contain only geometry:

## Tileset Configuration (`assets/tileset.yaml`)
- Defines gameplay properties for all terrain types (move cost, defense, etc.)
- Maps terrain names to tile IDs
- **Does not** define visual properties (colors/symbols) - those are renderer-specific
- Single source of truth for terrain gameplay mechanics

## Map System (Geometry Only)
- **CSV-based layers**: `ground.csv` (required), `walls.csv`, `features.csv` (optional)  
- **Pure geometry**: Maps contain ONLY terrain tile IDs - no units, objects, or spawns
- **Layer composition**: Higher layers override lower layers
- **Directory structure**: Each map is a directory in `assets/maps/`
- **Reusable**: Same map can be used across multiple scenarios with different gameplay

## Scenario System (Complete Gameplay Definition)
- **YAML format**: Human-readable scenario definitions in `assets/scenarios/`
- **Map references**: Link to map directories for geometry
- **Complete gameplay**: All units, objects, placements, objectives in one file
- **Placement system**: Uses `at: [y,x]`, `at_marker: NAME`, or `at_region: NAME`
- **Markers**: Named coordinate anchors for readability (`KNIGHT_POSITION: { at: [2,7] }`)
- **Regions**: Named rectangular areas for placement policies and triggers
- **Objects**: Scenario-specific interactive elements (healing fountains, doors, etc.)
- **Map overrides**: Optional non-destructive tile patches for environmental variation

## Data Templates (`assets/data/`)
- **Unit templates**: Class definitions and base stats in `assets/data/units/`
- **Reusable definitions**: Never contain placements - only stat templates
- **Centralized balance**: Single place to adjust unit class properties

## Key Benefits of Scenario-First Design
- **Single-file authoring**: Create new scenarios by editing one file, no map changes needed
- **No redundancy**: Coordinates and placements exist in exactly one place
- **High reusability**: Same map supports many different scenarios and gameplay setups
- **Zero merge conflicts**: Multiple designers can work on scenarios using the same map
- **Deterministic builds**: Scenario loader resolves placement intents into concrete game state