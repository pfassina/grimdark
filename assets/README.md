# Game Assets Directory

This directory contains all game assets organized by type.

## Structure

```
assets/
├── data/                    # Game configuration data
│   ├── units/              # Unit-related data
│   │   └── templates.json  # Unit class templates (Knight, Archer, etc.)
│   ├── items/              # (Future) Item definitions
│   └── skills/             # (Future) Skill definitions
├── scenarios/              # Scenario definitions
│   └── (scenario files)  # JSON scenario definitions
└── maps/                   # Map directories (CSV format)
    ├── tutorial/          # Tutorial map (ground.csv)
    ├── fortress/          # Fortress defense map
    ├── escape_mission/    # Escape mission map
    └── default_test/      # Default test map
```

## File Formats

### Unit Templates (data/units/templates.json)
Defines base stats for each unit class:
- Health points
- Movement range
- Combat stats (strength, defense, attack range)
- Speed

### Scenarios (scenarios/*.json)
JSON files defining:
- Map reference or embedded map data
- Unit placement
- Victory/defeat objectives
- Turn limits and other settings

### Maps (maps/*/ground.csv)
CSV files with tile ID data and tileset configuration:
- Each directory contains `ground.csv` with integer tile IDs
- `tileset.yaml` in root assets/ maps IDs to terrain properties
- Supports layered maps (future: walls.csv, features.csv)

Tile IDs:
  - `1` Plains (.)
  - `2` Forest (♣)  
  - `3` Mountain (▲)
  - `4` Water (≈)
  - `5` Road (=)
  - `6` Fort (■)
  - `7` Bridge (╬)
  - `8` Wall (█)

## Adding Content

1. **New Unit Classes**: Edit `data/units/templates.json`
2. **New Scenarios**: Create JSON in `scenarios/` directory
3. **New Maps**: Create CSV directories in `maps/` with `ground.csv` files

## Organization Benefits

- **Centralized Assets**: All game data in one location
- **Clear Categories**: Separated by asset type
- **Future-Ready**: Structure supports campaign mode
- **Easy Modding**: Users can add custom content