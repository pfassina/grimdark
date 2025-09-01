# Complete Guide to Creating Maps and Scenarios for Grimdark SRPG

This guide covers everything you need to know about creating maps and scenarios for Grimdark SRPG, from basic concepts to advanced features.

## Table of Contents

1. [Overview](#overview)
2. [Map Creation](#map-creation)
   - [Basic Map Structure](#basic-map-structure)
   - [Terrain Types and Tile IDs](#terrain-types-and-tile-ids)
   - [Multi-Layer Maps](#multi-layer-maps)
   - [Map Objects](#map-objects)
3. [Scenario Creation](#scenario-creation)
   - [Basic Scenario Structure](#basic-scenario-structure)
   - [Unit Placement](#unit-placement)
   - [Objectives](#objectives)
   - [Game Settings](#game-settings)
4. [Complete Examples](#complete-examples)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)

## Overview

Grimdark SRPG uses a data-driven approach with three main components:

1. **Maps**: CSV files defining terrain layouts with optional layers
2. **Objects**: YAML files defining spawn points, regions, and triggers
3. **Scenarios**: YAML files defining units, objectives, and game rules

### Directory Structure

```
assets/
├── maps/                          # Map directories
│   └── your_map_name/
│       ├── ground.csv            # Required: Base terrain
│       ├── walls.csv             # Optional: Blocking structures
│       ├── features.csv          # Optional: Decorative elements
│       └── objects.yaml          # Optional: Spawn points, regions, triggers
└── scenarios/                     # Scenario files
    └── your_scenario.yaml
```

## Map Creation

### Basic Map Structure

Maps use CSV format with integer tile IDs. Each map requires at least a `ground.csv` file.

#### Example: Simple 5x5 Map (ground.csv)

```csv
1,1,1,1,1
1,2,2,2,1
1,2,6,2,1
1,2,2,2,1
1,1,1,1,1
```

This creates a map with:
- Plains (1) around the border
- Forest (2) in the inner area
- A fort (6) in the center

### Terrain Types and Tile IDs

The tileset configuration (`assets/tileset.yaml`) defines all terrain types:

| Tile ID | Terrain Type | Symbol | Movement Cost | Defense | Special Properties |
|---------|--------------|--------|---------------|---------|-------------------|
| 1 | Plain | . | 1 | 0 | Basic terrain |
| 2 | Forest | ♣ | 2 | +1 | +20% avoid |
| 3 | Mountain | ▲ | 3 | +2 | +30% avoid |
| 4 | Water | ≈ | 99 | 0 | Blocks movement |
| 5 | Road | = | 1 | 0 | Fast movement |
| 6 | Fort | ■ | 1 | +3 | +10% avoid |
| 7 | Bridge | ╬ | 1 | 0 | Crosses water |
| 8 | Wall | █ | 99 | 0 | Blocks movement & vision |

### Multi-Layer Maps

Maps support multiple layers that composite together:

1. **ground.csv** - Base terrain (required)
2. **walls.csv** - Structures that override terrain (optional)
3. **features.csv** - Decorative elements (optional)

#### Example: Map with Walls

**ground.csv:**
```csv
1,1,1,1,1,1,1,1
1,2,2,2,2,2,2,1
1,2,6,6,6,6,2,1
1,2,6,1,1,6,2,1
1,2,6,1,1,6,2,1
1,2,6,6,6,6,2,1
1,2,2,2,2,2,2,1
1,1,1,1,1,1,1,1
```

**walls.csv:**
```csv
0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0
0,0,8,8,8,8,0,0
0,0,8,0,0,8,0,0
0,0,8,0,0,8,0,0
0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0
```

This creates a fort with walls on three sides, leaving the south open.

### Map Objects

The `objects.yaml` file defines interactive elements on the map.

#### Complete objects.yaml Example

```yaml
# Map Objects Configuration
# Defines spawn points, regions, and triggers

spawns:
  # Player spawn points
  - name: "Knight Start"
    team: PLAYER
    pos: [1, 1]
    class: KNIGHT        # Optional: Force specific class
    facing: "east"       # Optional: Initial facing direction
    
  - name: "Archer Start"
    team: PLAYER
    pos: [2, 1]
    
  # Enemy spawn points
  - name: "Boss Spawn"
    team: ENEMY
    pos: [6, 6]
    class: WARRIOR
    
  # Neutral spawn points  
  - name: "Villager"
    team: NEUTRAL
    pos: [4, 4]

regions:
  # Defensive positions
  - name: "Castle Keep"
    rect: [3, 3, 2, 2]    # x, y, width, height
    defense_bonus: 3
    avoid_bonus: 20
    description: "The heart of the castle provides excellent defense"
    
  # Hazardous areas
  - name: "Poison Swamp"
    rect: [5, 1, 3, 2]
    damage_per_turn: 2
    description: "Toxic waters damage units each turn"
    
  # Healing areas
  - name: "Healing Spring"
    rect: [1, 5, 2, 2]
    heal_per_turn: 3
    description: "Sacred waters restore health"
    
  # Mixed effects
  - name: "Ancient Shrine"
    rect: [4, 0, 1, 1]
    defense_bonus: 2
    heal_per_turn: 1
    avoid_bonus: 10
    description: "A mystical shrine grants multiple boons"

triggers:
  # Area triggers
  - name: "Ambush Trigger"
    type: "enter_region"
    region: "Castle Keep"
    condition: "unit_team:ENEMY"
    action: "spawn_reinforcements"
    data:
      spawn_points: ["Knight Start", "Archer Start"]
      units: ["KNIGHT", "ARCHER"]
      message: "Defenders emerge from the castle!"
      
  # Position triggers
  - name: "Treasure Chest"
    type: "interact"
    pos: [7, 7]
    condition: "unit_team:PLAYER"
    action: "give_item"
    data:
      item: "Healing Potion"
      message: "Found a Healing Potion!"
      
  # Turn-based triggers
  - name: "Reinforcement Wave 1"
    type: "turn_start"
    condition: "turn:5"
    action: "spawn_unit"
    data:
      spawn_point: "Boss Spawn"
      unit_class: "WARRIOR"
      team: "ENEMY"
      
  # Unit triggers
  - name: "Boss Defeated"
    type: "unit_defeated"
    condition: "unit_name:Dark Lord"
    action: "display_message"
    data:
      message: "The Dark Lord falls! The castle is saved!"
      
  # Escape triggers
  - name: "Escape Point"
    type: "enter_region"
    region: "Exit Zone"
    condition: "unit_name:Princess"
    action: "escape_unit"
    data:
      victory_on_escape: true
```

## Scenario Creation

### Basic Scenario Structure

Scenarios are YAML files that define the battle setup, units, and objectives.

#### Minimal Scenario Example

```yaml
name: Basic Battle
description: A simple skirmish
author: Your Name

# Map reference
map:
  source: assets/maps/your_map_name

# Unit definitions
units:
  - name: Hero
    class: KNIGHT
    team: PLAYER
    position: [1, 1]
    
  - name: Enemy
    class: WARRIOR
    team: ENEMY
    position: [5, 5]

# Objectives
objectives:
  victory:
    - type: defeat_all_enemies
      description: Defeat all enemies
      
  defeat:
    - type: all_units_defeated
      description: Don't lose all your units
```

### Unit Placement

Units can be placed in several ways:

#### 1. Direct Position (Traditional Method)

```yaml
units:
  - name: Sir Galahad
    class: KNIGHT
    team: PLAYER
    position: [2, 3]    # Direct x, y coordinates
```

#### 2. Using Spawn Points (Recommended)

If your map has `objects.yaml` with spawn points, units will automatically use matching spawn points:

```yaml
units:
  # Will use spawn point named "Sir Galahad" if it exists
  - name: Sir Galahad
    class: KNIGHT
    team: PLAYER
    position: [0, 0]    # Fallback if spawn point not found
    
  # Will use any available PLAYER team spawn point
  - name: Archer Robin
    class: ARCHER
    team: PLAYER
    position: [0, 0]
```

#### 3. With Stat Overrides

```yaml
units:
  - name: Elite Guard
    class: KNIGHT
    team: PLAYER
    position: [3, 3]
    stats_override:
      hp_max: 40        # Normal knight has 25
      strength: 10      # Normal knight has 7
      defense: 8        # Normal knight has 5
      speed: 5          # Normal knight has 3
      movement_points: 4  # Normal knight has 3
```

#### 4. Complete Unit Definition

```yaml
units:
  - name: Lord Commander
    class: KNIGHT
    team: PLAYER
    position: [5, 5]
    stats_override:
      # Health
      hp_max: 50
      hp_current: 50    # Optional, defaults to hp_max
      
      # Combat stats
      strength: 12
      defense: 10
      accuracy: 95
      evasion: 15
      critical: 10
      
      # Movement
      movement_points: 5
      
      # Range (for ranged units)
      range_min: 1
      range_max: 1
      
      # Status
      speed: 6
```

### Objectives

Grimdark SRPG supports multiple objective types that can be combined:

#### Victory Objectives

```yaml
objectives:
  victory:
    # Defeat all enemies
    - type: defeat_all_enemies
      description: Eliminate all hostile forces
      
    # Survive for X turns
    - type: survive_turns
      turns: 10
      description: Hold out for 10 turns
      
    # Reach a specific position
    - type: reach_position
      position: [15, 0]
      unit_name: Princess Aria    # Optional: specific unit
      description: Escape through the eastern exit
      
    # Defeat specific unit
    - type: defeat_unit
      unit_name: Dark Lord
      description: Defeat the Dark Lord
      
    # Capture and hold position
    - type: position_captured
      position: [7, 7]
      description: Capture the throne room
```

#### Defeat Objectives

```yaml
objectives:
  defeat:
    # Protect specific unit
    - type: protect_unit
      unit_name: Princess Aria
      description: Princess Aria must survive
      
    # Don't lose all units
    - type: all_units_defeated
      description: Don't let all units fall
      
    # Turn limit
    - type: turn_limit
      turns: 20
      description: Complete within 20 turns
```

### Game Settings

```yaml
settings:
  turn_limit: 30              # Optional: Maximum turns (null for unlimited)
  starting_team: PLAYER       # Which team goes first
  fog_of_war: false          # Enable fog of war (not implemented yet)
  
  # Future settings (not implemented)
  weather: rain              # Weather effects
  time_of_day: night         # Lighting conditions
  reinforcements_enabled: true
```

## Complete Examples

### Example 1: Defense Mission

```yaml
# fortress_siege.yaml
name: Siege of Ironhold
description: Defend the fortress against overwhelming odds
author: Battle Designer

map:
  source: assets/maps/fortress

# Use YAML anchors for common patterns
_defender_stats: &defender_stats
  hp_max: 30
  defense: 7

units:
  # Defenders
  - name: Captain Marcus
    class: KNIGHT
    team: PLAYER
    position: [7, 5]
    stats_override:
      <<: *defender_stats
      strength: 9
      
  - name: Archer Elena
    class: ARCHER
    team: PLAYER
    position: [5, 3]
    stats_override:
      <<: *defender_stats
      accuracy: 100
      
  - name: Cleric Johan
    class: CLERIC
    team: PLAYER
    position: [7, 3]
    
  # Attackers (will use spawn points from objects.yaml)
  - name: Siege Captain
    class: WARRIOR
    team: ENEMY
    position: [7, 12]
    stats_override:
      hp_max: 35
      strength: 8
      
  # More enemies...
  - name: Raider 1
    class: WARRIOR
    team: ENEMY
    position: [0, 0]  # Will use spawn points
    
objectives:
  victory:
    - type: survive_turns
      turns: 15
      description: Hold the fortress for 15 turns
      
    - type: defeat_all_enemies
      description: Alternative - defeat all attackers
      
  defeat:
    - type: protect_unit
      unit_name: Captain Marcus
      description: Captain Marcus must survive
      
    - type: position_captured
      position: [7, 3]
      description: Don't let enemies capture the keep

settings:
  turn_limit: 20
  starting_team: ENEMY    # Attackers move first
```

### Example 2: Escape Mission

```yaml
# prison_break.yaml
name: Escape from Shadow Prison
description: Break out of the enemy prison and reach freedom
author: Stealth Master

map:
  source: assets/maps/prison_complex

units:
  # Prisoners (weakened stats)
  - name: Aria Swiftwind
    class: THIEF
    team: PLAYER
    position: [1, 8]
    stats_override:
      hp_current: 10      # Starts wounded
      hp_max: 18
      movement_points: 5  # Thief is fast
      
  - name: Broken Knight
    class: KNIGHT  
    team: PLAYER
    position: [2, 8]
    stats_override:
      hp_current: 15
      hp_max: 25
      strength: 5         # Weakened without weapons
      defense: 3          # No armor
      
  # Guards
  - name: Prison Guard 1
    class: WARRIOR
    team: ENEMY
    position: [5, 5]
    
  - name: Warden
    class: KNIGHT
    team: ENEMY
    position: [10, 2]
    stats_override:
      hp_max: 40
      strength: 10
      defense: 8

objectives:
  victory:
    # Primary objective
    - type: reach_position
      position: [14, 0]
      unit_name: Aria Swiftwind
      description: Aria must reach the exit
      
    # Optional objective
    - type: defeat_unit
      unit_name: Warden
      description: Optional - Defeat the Warden for bonus

  defeat:
    - type: protect_unit
      unit_name: Aria Swiftwind
      description: Aria must survive
      
    - type: turn_limit
      turns: 25
      description: Escape before reinforcements arrive

settings:
  turn_limit: 25
  starting_team: PLAYER
```

### Example 3: Complex Multi-Objective Battle

```yaml
# the_final_stand.yaml
name: The Final Stand
description: Multiple objectives in an epic confrontation
author: Epic Designer

map:
  source: assets/maps/battlefield

# Reusable unit templates
_elite_stats: &elite_stats
  hp_max: 35
  strength: 9
  defense: 7
  accuracy: 95

_boss_stats: &boss_stats
  hp_max: 60
  strength: 12
  defense: 10
  speed: 8
  evasion: 20
  critical: 15

units:
  # Heroes
  - name: Lord Alexander
    class: KNIGHT
    team: PLAYER
    position: [7, 10]
    stats_override:
      <<: *elite_stats
      hp_max: 40
      
  - name: Archmage Zelda
    class: MAGE
    team: PLAYER
    position: [6, 10]
    stats_override:
      <<: *elite_stats
      strength: 6
      range_max: 4
      
  - name: Holy Priest Luna
    class: CLERIC
    team: PLAYER
    position: [8, 10]
    
  - name: Scout Raven
    class: THIEF
    team: PLAYER
    position: [7, 11]
    stats_override:
      movement_points: 6
      evasion: 30
      
  # Villains
  - name: Dark Emperor
    class: WARRIOR
    team: ENEMY
    position: [7, 2]
    stats_override:
      <<: *boss_stats
      
  - name: Shadow Assassin
    class: THIEF
    team: ENEMY
    position: [5, 3]
    stats_override:
      <<: *elite_stats
      movement_points: 5
      critical: 25
      
  # Neutral units to protect
  - name: Village Elder
    class: CLERIC
    team: NEUTRAL
    position: [3, 7]
    stats_override:
      hp_max: 15
      movement_points: 2

objectives:
  victory:
    # Primary path - defeat the boss
    - type: defeat_unit
      unit_name: Dark Emperor
      description: Defeat the Dark Emperor
      
    # Alternative path - capture throne
    - type: position_captured
      position: [7, 1]
      description: Capture the Dark Throne
      
    # Hidden objective - save everyone
    - type: protect_unit
      unit_name: Village Elder
      description: Bonus - Save the Village Elder

  defeat:
    - type: protect_unit
      unit_name: Lord Alexander
      description: Lord Alexander must survive
      
    - type: all_units_defeated
      description: Don't lose all your forces
      
    - type: turn_limit
      turns: 30
      description: Win before enemy reinforcements

settings:
  turn_limit: 30
  starting_team: PLAYER
```

## Advanced Features

### Using YAML Anchors for Efficiency

```yaml
# Define reusable patterns
_movement_defaults: &movement_defaults
  movement_points: 3

_combat_defaults: &combat_defaults
  accuracy: 85
  evasion: 10
  critical: 5

_tank_build: &tank_build
  <<: *movement_defaults
  hp_max: 40
  strength: 8
  defense: 10
  <<: *combat_defaults

units:
  - name: Tank 1
    class: KNIGHT
    team: PLAYER
    position: [1, 1]
    stats_override:
      <<: *tank_build
      
  - name: Tank 2
    class: KNIGHT
    team: PLAYER  
    position: [2, 1]
    stats_override:
      <<: *tank_build
      hp_max: 45  # Override specific stat
```

### Regional Effects Strategy

Design maps with strategic regions:

```yaml
# In objects.yaml
regions:
  # Choke point with defensive advantage
  - name: "Bridge Defense"
    rect: [7, 5, 1, 3]
    defense_bonus: 4
    avoid_bonus: 25
    description: "Narrow bridge provides excellent defense"
    
  # High ground advantage
  - name: "Hill Top"
    rect: [10, 2, 3, 3]
    defense_bonus: 2
    avoid_bonus: 15
    accuracy_bonus: 10    # Future feature
    description: "Height advantage improves accuracy"
    
  # Dangerous terrain
  - name: "Lava Field"
    rect: [0, 0, 5, 3]
    damage_per_turn: 5
    movement_cost_multiplier: 2    # Future feature
    description: "Molten rock burns and slows movement"
```

### Spawn Point Strategies

```yaml
spawns:
  # Wave-based spawns
  - name: "Wave1_Spawn1"
    team: ENEMY
    pos: [0, 5]
    
  - name: "Wave1_Spawn2"
    team: ENEMY
    pos: [0, 6]
    
  - name: "Wave2_Spawn1"
    team: ENEMY
    pos: [14, 5]
    
  # Class-specific spawns
  - name: "Archer_Position_1"
    team: PLAYER
    pos: [7, 10]
    class: ARCHER
    
  - name: "Archer_Position_2"
    team: PLAYER
    pos: [8, 10]
    class: ARCHER
```

### Trigger Combinations

```yaml
triggers:
  # Chain triggers
  - name: "Open Gate"
    type: "interact"
    pos: [5, 5]
    action: "modify_terrain"
    data:
      positions: [[6, 5], [7, 5]]
      new_terrain: 1  # Change to plain
      message: "The gate opens!"
      
  # Conditional spawns
  - name: "Boss Phase 2"
    type: "unit_defeated"
    condition: "unit_name:Dark Lord"
    action: "spawn_unit"
    data:
      spawn_point: "Boss Spawn"
      unit_class: "WARRIOR"
      unit_name: "Dark Lord Reborn"
      stats_override:
        hp_max: 80
        strength: 15
```

## Best Practices

### Map Design

1. **Start Small**: Begin with 10x10 or 15x15 maps
2. **Clear Objectives**: Place visual landmarks near objective locations
3. **Strategic Variety**: Mix open areas with choke points
4. **Height Variation**: Use mountains and walls for tactical depth
5. **Safe Zones**: Provide defensive positions for tactical retreats

### Scenario Balance

1. **Action Economy**: Balance unit counts between teams
2. **Progressive Difficulty**: Start with easier enemies
3. **Multiple Paths**: Provide different strategies to win
4. **Resource Management**: Balance healing opportunities
5. **Turn Limits**: Set realistic limits that allow exploration

### File Organization

```
your_campaign/
├── maps/
│   ├── mission1_prison/
│   │   ├── ground.csv
│   │   ├── walls.csv
│   │   └── objects.yaml
│   ├── mission2_forest/
│   │   ├── ground.csv
│   │   └── objects.yaml
│   └── mission3_castle/
│       ├── ground.csv
│       ├── walls.csv
│       ├── features.csv
│       └── objects.yaml
└── scenarios/
    ├── 01_prison_break.yaml
    ├── 02_forest_ambush.yaml
    └── 03_castle_siege.yaml
```

### Testing Your Content

1. **Test Each Objective**: Verify all victory/defeat conditions work
2. **Edge Cases**: Test map boundaries and impassable terrain
3. **Balance Testing**: Play both sides to ensure fairness
4. **Performance**: Large maps (30x30+) may impact performance

### Common Patterns

#### Defense Mission Template
```yaml
objectives:
  victory:
    - type: survive_turns
      turns: 15
  defeat:
    - type: protect_unit
      unit_name: Commander
```

#### Escape Mission Template
```yaml
objectives:
  victory:
    - type: reach_position
      position: [14, 0]
      unit_name: VIP
  defeat:
    - type: turn_limit
      turns: 20
```

#### Assassination Template
```yaml
objectives:
  victory:
    - type: defeat_unit
      unit_name: Target
  defeat:
    - type: all_units_defeated
```

## Troubleshooting

### Common Issues

1. **Units not appearing**: Check spawn point names match
2. **Invalid terrain**: Verify tile IDs exist in tileset.yaml
3. **Objectives not triggering**: Ensure unit names match exactly
4. **Map not loading**: Verify file paths are relative to project root

### Validation Checklist

- [ ] All CSV files have consistent dimensions
- [ ] Tile IDs are valid (1-8)
- [ ] Spawn points don't overlap
- [ ] Unit positions are within map bounds
- [ ] Objectives reference existing units/positions
- [ ] File paths use forward slashes (/)

## Future Features (Planned)

These features are defined in the system but not yet implemented:

1. **Advanced Triggers**: Complex conditions and actions
2. **Weather Effects**: Rain, fog, snow affecting gameplay
3. **Dynamic Terrain**: Destructible walls, bridges
4. **Multi-Height**: True 3D elevation with line-of-sight
5. **Campaign Connections**: Carry units between scenarios
6. **Custom Scripts**: Python scripts for complex events

---

This guide covers all current features of the Grimdark SRPG map and scenario system. For the latest updates and examples, check the `assets/scenarios/` and `assets/maps/` directories in the project repository.