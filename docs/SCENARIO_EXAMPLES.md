# Grimdark SRPG Scenario Examples Gallery

This document provides ready-to-use scenario examples demonstrating different mission types, advanced features, and creative possibilities using the **new scenario-first placement system**.

> **Note**: This documentation is being updated for the new placement system. The first example has been updated to demonstrate the new approach. Additional examples will be converted gradually.

## Table of Contents

1. [Basic Mission Types](#basic-mission-types)
2. [Advanced Scenarios](#advanced-scenarios)
3. [Special Mechanics](#special-mechanics)
4. [Mini Campaigns](#mini-campaigns)
5. [Puzzle Scenarios](#puzzle-scenarios)
6. [Experimental Ideas](#experimental-ideas)

## Basic Mission Types

### 1. Classic Skirmish

**Concept**: Balanced forces meet on neutral ground.

```yaml
name: Open Field Battle
description: A straightforward tactical engagement
author: Example Designer

map:
  source: assets/maps/open_field

# Unit roster (no positions)
units:
  # Player Team
  - { name: Knight, class: KNIGHT, team: PLAYER }
  - { name: Archer 1, class: ARCHER, team: PLAYER }
  - { name: Archer 2, class: ARCHER, team: PLAYER }
  - { name: Mage, class: MAGE, team: PLAYER }
  - { name: Cleric, class: CLERIC, team: PLAYER }
  
  # Enemy Team - mirror match
  - { name: Enemy Knight, class: KNIGHT, team: ENEMY }
  - { name: Enemy Archer 1, class: ARCHER, team: ENEMY }
  - { name: Enemy Archer 2, class: ARCHER, team: ENEMY }
  - { name: Enemy Mage, class: MAGE, team: ENEMY }
  - { name: Enemy Cleric, class: CLERIC, team: ENEMY }

# All placements defined here
placements:
  # Player formation
  Knight: { at: [2, 5] }
  "Archer 1": { at: [1, 4] }
  "Archer 2": { at: [1, 6] }
  Mage: { at: [2, 7] }
  Cleric: { at: [3, 5] }
  
  # Enemy formation
  "Enemy Knight": { at: [12, 5] }
  "Enemy Archer 1": { at: [13, 4] }
  "Enemy Archer 2": { at: [13, 6] }
  "Enemy Mage": { at: [12, 7] }
  "Enemy Cleric": { at: [11, 5] }

objectives:
  victory:
    - type: defeat_all_enemies
  defeat:
    - type: all_units_defeated

settings:
  turn_limit: null  # No time pressure
  starting_team: PLAYER
```

### 1.5. Complete Modern Scenario (New System Showcase)

**Concept**: Demonstrates all new placement features: markers, regions, objects, and map overrides.

```yaml
name: Fortress Defense (Modern)
description: Showcase of the new scenario-first placement system
author: System Demo

map:
  source: assets/maps/fortress

# Named coordinate anchors
markers:
  COMMANDER_POST:
    at: [7, 2]
    description: Central command position
  HEALING_FOUNTAIN:
    at: [7, 3]
    description: Sacred fountain location
  MAIN_GATE:
    at: [7, 10]
    description: Primary fortress entrance

# Named regions for placement and triggers  
regions:
  FORTRESS_WALLS:
    rect: [4, 1, 7, 6]
    description: Defensive wall positions
  BATTLEFIELD:
    rect: [0, 8, 15, 3]
    description: Open combat area
  ENEMY_SPAWN:
    rect: [1, 10, 13, 1]
    description: Enemy reinforcement zone

# Unit roster (no positions!)
units:
  # Player defenders
  - name: Sir Commander
    class: KNIGHT
    team: PLAYER
    stats_override:
      hp_max: 40
      strength: 10
      defense: 7
      
  - name: Wall Archer Alpha
    class: ARCHER
    team: PLAYER
    
  - name: Wall Archer Beta
    class: ARCHER
    team: PLAYER
    
  - name: Battle Mage
    class: MAGE
    team: PLAYER
    
  # Initial enemies
  - name: Assault Captain
    class: KNIGHT
    team: ENEMY
    
  - name: Infantry Squad
    class: WARRIOR
    team: ENEMY

# Interactive objects
objects:
  SACRED_FOUNTAIN:
    type: healing_fountain
    properties:
      heal_amount: 3
      team_filter: PLAYER
      description: Restores 3 HP to friendly units

# Event-driven triggers
triggers:
  FOUNTAIN_HEALING:
    type: turn_start
    condition: unit_team:PLAYER
    action: heal_units_in_region
    data:
      region: FORTRESS_WALLS
      heal_amount: 2
      
  ENEMY_REINFORCEMENTS:
    type: turn_start
    condition: turn:5
    action: spawn_units
    data:
      units: ["Reinforcement Wave"]
      message: "Enemy reinforcements arrive!"

# New placement system in action
placements:
  # Using markers for key positions
  "Sir Commander":
    at_marker: COMMANDER_POST
    
  # Using regions with placement policies
  "Wall Archer Alpha":
    at_region: FORTRESS_WALLS
    policy: random_free_tile
    
  "Wall Archer Beta":
    at_region: FORTRESS_WALLS  
    policy: spread_evenly
    
  # Direct coordinates still supported
  "Battle Mage":
    at: [5, 3]
    
  # Enemy placements
  "Assault Captain":
    at_marker: MAIN_GATE
    
  "Infantry Squad":
    at_region: BATTLEFIELD
    policy: random_free_tile
    
  # Object placement
  SACRED_FOUNTAIN:
    at_marker: HEALING_FOUNTAIN

# Environmental modifications
map_overrides:
  tile_patches:
    - x: 6
      y: 8
      tile_id: 7  # Add bridge for tactical variety

objectives:
  victory:
    - type: survive_turns
      turns: 8
      description: Hold the fortress for 8 turns
    - type: defeat_all_enemies
      description: Or eliminate all threats
      
  defeat:
    - type: protect_unit
      unit_name: Sir Commander
      description: The commander must survive

settings:
  turn_limit: 12
  starting_team: PLAYER
```

This example demonstrates:
- **Markers**: Named positions for important locations
- **Regions**: Areas for dynamic placement and effects  
- **Objects**: Interactive environmental elements
- **Placement variety**: All three methods (at/at_marker/at_region)
- **Map overrides**: Non-destructive terrain modifications
- **Advanced triggers**: Event-driven gameplay

### 2. Survival Mission

**Concept**: Hold position against waves of enemies.

```yaml
name: Last Stand at Dawn
description: Survive until sunrise (10 turns)
author: Defense Master

map:
  source: assets/maps/hilltop_fort

# Defensive stat bonuses for player units
_defender_bonus: &defender
  hp_max: 35
  defense: 8

units:
  # Small elite player force
  - name: Captain
    class: KNIGHT
    team: PLAYER
    position: [7, 7]
    stats_override:
      <<: *defender
      hp_max: 40
      
  - name: Veteran Archer
    class: ARCHER
    team: PLAYER
    position: [6, 6]
    stats_override:
      <<: *defender
      accuracy: 100
      
  - name: Battle Cleric
    class: CLERIC
    team: PLAYER
    position: [8, 7]
    stats_override:
      <<: *defender

  # Initial enemies (more spawn via triggers)
  - { name: Scout 1, class: THIEF, team: ENEMY, position: [2, 2] }
  - { name: Scout 2, class: THIEF, team: ENEMY, position: [12, 2] }
  - { name: Scout 3, class: THIEF, team: ENEMY, position: [2, 12] }

objectives:
  victory:
    - type: survive_turns
      turns: 10
      description: Hold out until dawn (10 turns)
      
  defeat:
    - type: all_units_defeated
      description: The fort has fallen

settings:
  turn_limit: 15  # Extra turns to mop up
  starting_team: ENEMY  # Enemies attack first
```

### 3. Assassination Mission

**Concept**: Eliminate a specific target while avoiding/defeating guards.

```yaml
name: The Tyrant's End
description: Infiltrate and eliminate the enemy commander
author: Stealth Designer

map:
  source: assets/maps/enemy_camp

units:
  # Small strike team
  - name: Assassin
    class: THIEF
    team: PLAYER
    position: [1, 7]
    stats_override:
      movement_points: 6
      critical: 30
      evasion: 40
      
  - name: Ranger
    class: ARCHER
    team: PLAYER
    position: [1, 8]
    stats_override:
      range_max: 4
      movement_points: 5
      
  # Target and guards
  - name: Tyrant General
    class: KNIGHT
    team: ENEMY
    position: [13, 7]
    stats_override:
      hp_max: 50
      strength: 12
      defense: 10
      movement_points: 2  # Slow and confident
      
  # Multiple guards
  - { name: Guard 1, class: WARRIOR, team: ENEMY, position: [11, 6] }
  - { name: Guard 2, class: WARRIOR, team: ENEMY, position: [11, 8] }
  - { name: Guard 3, class: WARRIOR, team: ENEMY, position: [12, 7] }
  - { name: Patrol 1, class: THIEF, team: ENEMY, position: [7, 5] }
  - { name: Patrol 2, class: THIEF, team: ENEMY, position: [7, 9] }

objectives:
  victory:
    - type: defeat_unit
      unit_name: Tyrant General
      description: Eliminate the Tyrant General
      
  defeat:
    - type: all_units_defeated
    - type: turn_limit
      turns: 20
      description: Complete before reinforcements arrive

settings:
  turn_limit: 20
  starting_team: PLAYER
```

### 4. Escort Mission

**Concept**: Protect a weak unit while moving to destination.

```yaml
name: Royal Escape
description: Escort the prince to safety
author: Protection Expert

map:
  source: assets/maps/forest_road

# VIP stats - weak but must survive
_vip_stats: &vip
  hp_max: 15
  defense: 2
  movement_points: 3
  evasion: 5

units:
  # The VIP
  - name: Prince Aldric
    class: CLERIC  # Non-combat unit
    team: PLAYER
    position: [2, 7]
    stats_override:
      <<: *vip
      
  # Guards
  - name: Royal Guard 1
    class: KNIGHT
    team: PLAYER
    position: [2, 6]
    stats_override:
      hp_max: 35
      defense: 9
      
  - name: Royal Guard 2
    class: KNIGHT
    team: PLAYER
    position: [2, 8]
    stats_override:
      hp_max: 35
      defense: 9
      
  # Ambushers appear along the route
  - { name: Bandit 1, class: WARRIOR, team: ENEMY, position: [6, 5] }
  - { name: Bandit 2, class: WARRIOR, team: ENEMY, position: [6, 9] }
  - { name: Bandit Archer, class: ARCHER, team: ENEMY, position: [8, 7] }

objectives:
  victory:
    - type: reach_position
      position: [14, 7]
      unit_name: Prince Aldric
      description: Prince must reach the safe house
      
  defeat:
    - type: protect_unit
      unit_name: Prince Aldric
      description: The Prince must survive

settings:
  turn_limit: null
  starting_team: PLAYER
```

## Advanced Scenarios

### 5. Multi-Objective Complex Mission

**Concept**: Multiple paths to victory with bonus objectives.

```yaml
name: The Siege of Ironhold
description: Complex siege with multiple objectives
author: Advanced Designer

map:
  source: assets/maps/castle_siege

# Different unit roles
_siege_stats: &siege
  hp_max: 30
  strength: 8

_defender_stats: &defender
  defense: 7
  hp_max: 35

units:
  # Player siege force
  - name: Siege Commander
    class: KNIGHT
    team: PLAYER
    position: [2, 10]
    stats_override:
      <<: *siege
      hp_max: 40
      defense: 8
      
  - name: Battering Ram Escort 1
    class: WARRIOR
    team: PLAYER
    position: [3, 9]
    stats_override: *siege
    
  - name: Battering Ram Escort 2
    class: WARRIOR
    team: PLAYER
    position: [3, 11]
    stats_override: *siege
    
  - name: Siege Archer 1
    class: ARCHER
    team: PLAYER
    position: [1, 8]
    
  - name: Siege Archer 2
    class: ARCHER
    team: PLAYER
    position: [1, 12]
    
  - name: Infiltrator
    class: THIEF
    team: PLAYER
    position: [5, 15]
    stats_override:
      movement_points: 6
      evasion: 35
      
  # Castle defenders
  - name: Castle Lord
    class: KNIGHT
    team: ENEMY
    position: [12, 10]
    stats_override:
      <<: *defender
      hp_max: 45
      strength: 10
      
  - name: Wall Archer 1
    class: ARCHER
    team: ENEMY
    position: [10, 8]
    stats_override: *defender
    
  - name: Wall Archer 2
    class: ARCHER
    team: ENEMY
    position: [10, 12]
    stats_override: *defender
    
  - name: Gate Guard 1
    class: WARRIOR
    team: ENEMY
    position: [8, 9]
    stats_override: *defender
    
  - name: Gate Guard 2
    class: WARRIOR
    team: ENEMY
    position: [8, 11]
    stats_override: *defender

objectives:
  victory:
    # Multiple ways to win
    - type: defeat_unit
      unit_name: Castle Lord
      description: Defeat the Castle Lord
      
    - type: position_captured
      position: [12, 10]
      description: Capture the throne room
      
    - type: reach_position
      position: [14, 10]
      unit_name: Infiltrator
      description: Sneak past defenses with thief
      
  defeat:
    - type: protect_unit
      unit_name: Siege Commander
      description: Commander must survive
      
    - type: turn_limit
      turns: 25
      description: Win before reinforcements arrive

settings:
  turn_limit: 25
  starting_team: PLAYER
```

### 6. Puzzle Combat Scenario

**Concept**: Specific sequence of moves required to win.

```yaml
name: The Chess Master's Challenge
description: Defeat enemies in the correct order
author: Puzzle Designer

map:
  source: assets/maps/chess_board

units:
  # Player has limited resources
  - name: Tactical Knight
    class: KNIGHT
    team: PLAYER
    position: [4, 7]
    stats_override:
      hp_current: 20  # Damaged
      hp_max: 25
      strength: 8
      movement_points: 3
      
  - name: Precision Archer
    class: ARCHER
    team: PLAYER
    position: [3, 7]
    stats_override:
      hp_current: 15
      hp_max: 18
      range_max: 3
      strength: 6
      
  # Enemies in specific formation
  - name: Pawn 1
    class: WARRIOR
    team: ENEMY
    position: [4, 4]
    stats_override:
      hp_max: 10
      strength: 4
      
  - name: Pawn 2
    class: WARRIOR
    team: ENEMY
    position: [5, 4]
    stats_override:
      hp_max: 10
      strength: 4
      
  - name: Bishop
    class: MAGE
    team: ENEMY
    position: [3, 3]
    stats_override:
      hp_max: 15
      strength: 8
      range_max: 4
      
  - name: Rook
    class: KNIGHT
    team: ENEMY
    position: [6, 3]
    stats_override:
      hp_max: 25
      defense: 8
      strength: 6

objectives:
  victory:
    - type: defeat_all_enemies
      description: Solve the tactical puzzle
      
  defeat:
    - type: all_units_defeated
    - type: turn_limit
      turns: 6  # Exact solution required

settings:
  turn_limit: 6
  starting_team: PLAYER
```

## Special Mechanics

### 7. Fog of War Scenario

**Concept**: Limited visibility creates tension.

```yaml
name: Night Patrol
description: Navigate through enemy territory in darkness
author: Stealth Master

map:
  source: assets/maps/dark_forest

units:
  # Small scouting party
  - name: Scout Leader
    class: THIEF
    team: PLAYER
    position: [1, 8]
    stats_override:
      movement_points: 6
      vision_range: 4  # Future feature
      
  - name: Night Archer
    class: ARCHER
    team: PLAYER
    position: [2, 8]
    stats_override:
      vision_range: 5
      accuracy: 80  # Reduced in darkness
      
  # Hidden enemies (placed throughout map)
  - { name: Sentry 1, class: WARRIOR, team: ENEMY, position: [6, 6] }
  - { name: Sentry 2, class: WARRIOR, team: ENEMY, position: [8, 10] }
  - { name: Patrol 1, class: THIEF, team: ENEMY, position: [10, 7] }
  - { name: Hidden Archer, class: ARCHER, team: ENEMY, position: [12, 9] }

objectives:
  victory:
    - type: reach_position
      position: [15, 8]
      unit_name: Scout Leader
      description: Reach extraction point undetected
      
  defeat:
    - type: all_units_defeated

settings:
  turn_limit: null
  starting_team: PLAYER
  fog_of_war: true  # Future feature
```

### 8. Reinforcement Waves

**Concept**: Escalating difficulty through timed spawns.

```yaml
name: Hold the Line
description: Defend against increasingly difficult waves
author: Wave Designer

map:
  source: assets/maps/fortress_gates

# objects.yaml triggers handle the waves
# See triggers section for wave spawning

units:
  # Initial defenders
  - name: Gate Captain
    class: KNIGHT
    team: PLAYER
    position: [7, 10]
    stats_override:
      hp_max: 40
      defense: 9
      
  - name: Archer Tower 1
    class: ARCHER
    team: PLAYER
    position: [5, 9]
    stats_override:
      range_max: 4
      defense: 6  # Tower bonus
      
  - name: Archer Tower 2
    class: ARCHER
    team: PLAYER
    position: [9, 9]
    stats_override:
      range_max: 4
      defense: 6
      
  - name: Support Cleric
    class: CLERIC
    team: PLAYER
    position: [7, 11]
    
  # Wave 1 enemies (weak)
  - { name: Grunt 1, class: WARRIOR, team: ENEMY, position: [6, 2] }
  - { name: Grunt 2, class: WARRIOR, team: ENEMY, position: [8, 2] }

objectives:
  victory:
    - type: survive_turns
      turns: 15
      description: Hold for 15 turns
      
  defeat:
    - type: protect_unit
      unit_name: Gate Captain
      description: The Captain must not fall

settings:
  turn_limit: 20
  starting_team: ENEMY
```

## Mini Campaigns

### 9. Three-Part Story Arc

**Part 1: The Ambush**

```yaml
name: Forest Ambush (Part 1)
description: Survive the surprise attack
author: Campaign Designer

map:
  source: assets/maps/forest_road

units:
  # Caravan guards (become veterans in part 2)
  - name: Marcus the Bold
    class: KNIGHT
    team: PLAYER
    position: [5, 5]
    
  - name: Elena Quickshot
    class: ARCHER
    team: PLAYER
    position: [6, 5]
    
  - name: Brother Thomas
    class: CLERIC
    team: PLAYER
    position: [5, 6]
    
  # Ambushers
  - { name: Bandit Leader, class: WARRIOR, team: ENEMY, position: [2, 5] }
  - { name: Bandit 1, class: THIEF, team: ENEMY, position: [8, 3] }
  - { name: Bandit 2, class: THIEF, team: ENEMY, position: [8, 7] }

objectives:
  victory:
    - type: defeat_all_enemies
      
  defeat:
    - type: protect_unit
      unit_name: Marcus the Bold  # Main character

settings:
  turn_limit: null
  starting_team: ENEMY  # Surprise attack
```

**Part 2: The Pursuit**

```yaml
name: Hunting the Bandits (Part 2)
description: Track down the bandit camp
author: Campaign Designer

map:
  source: assets/maps/bandit_camp

units:
  # Same heroes, now experienced
  - name: Marcus the Bold
    class: KNIGHT
    team: PLAYER
    position: [2, 8]
    stats_override:
      hp_max: 35  # Leveled up
      strength: 9
      
  - name: Elena Quickshot
    class: ARCHER
    team: PLAYER
    position: [3, 8]
    stats_override:
      accuracy: 95  # Improved
      range_max: 4
      
  - name: Brother Thomas
    class: CLERIC
    team: PLAYER
    position: [2, 9]
    stats_override:
      hp_max: 25  # More durable
      
  # New ally joins
  - name: Reformed Bandit
    class: THIEF
    team: PLAYER
    position: [3, 9]
    
  # Bandit camp
  - { name: Bandit Chief, class: KNIGHT, team: ENEMY, position: [12, 5] }
  - { name: Guard 1, class: WARRIOR, team: ENEMY, position: [10, 4] }
  - { name: Guard 2, class: WARRIOR, team: ENEMY, position: [10, 6] }
  - { name: Lookout, class: ARCHER, team: ENEMY, position: [8, 5] }

objectives:
  victory:
    - type: defeat_unit
      unit_name: Bandit Chief
      
  defeat:
    - type: protect_unit
      unit_name: Marcus the Bold

settings:
  turn_limit: null
  starting_team: PLAYER
```

**Part 3: The Final Revelation**

```yaml
name: The Corrupt Noble (Part 3)
description: Confront the true villain
author: Campaign Designer

map:
  source: assets/maps/noble_manor

units:
  # Full party for finale
  - name: Marcus the Bold
    class: KNIGHT
    team: PLAYER
    position: [2, 10]
    stats_override:
      hp_max: 40  # Max level
      strength: 10
      defense: 9
      
  - name: Elena Quickshot
    class: ARCHER
    team: PLAYER
    position: [3, 10]
    stats_override:
      accuracy: 100
      range_max: 4
      critical: 15
      
  - name: Brother Thomas
    class: CLERIC
    team: PLAYER
    position: [2, 11]
    stats_override:
      hp_max: 30
      heal_power: 12  # Future feature
      
  - name: Shadow (Reformed Bandit)
    class: THIEF
    team: PLAYER
    position: [3, 11]
    stats_override:
      movement_points: 6
      critical: 25
      
  # The true villain and elite guards
  - name: Lord Blackheart
    class: KNIGHT
    team: ENEMY
    position: [12, 10]
    stats_override:
      hp_max: 50
      strength: 12
      defense: 10
      accuracy: 95
      
  - { name: Elite Guard 1, class: WARRIOR, team: ENEMY, position: [10, 9] }
  - { name: Elite Guard 2, class: WARRIOR, team: ENEMY, position: [10, 11] }
  - { name: Court Mage, class: MAGE, team: ENEMY, position: [11, 10] }

objectives:
  victory:
    - type: defeat_unit
      unit_name: Lord Blackheart
      description: Bring justice to the corrupt lord
      
  defeat:
    - type: protect_unit
      unit_name: Marcus the Bold
      description: The hero must survive

settings:
  turn_limit: null
  starting_team: PLAYER
```

## Puzzle Scenarios

### 10. The Bridge Puzzle

**Concept**: Use movement and positioning to solve.

```yaml
name: Bridge Constructor
description: Position units to form a bridge
author: Puzzle Master

map:
  source: assets/maps/broken_bridge

units:
  # Each unit has specific movement range
  - name: Stone Block 1
    class: KNIGHT
    team: PLAYER
    position: [2, 5]
    stats_override:
      movement_points: 2  # Limited movement
      hp_max: 100  # Can't die
      
  - name: Stone Block 2
    class: KNIGHT
    team: PLAYER
    position: [2, 7]
    stats_override:
      movement_points: 3
      hp_max: 100
      
  - name: Long Plank
    class: THIEF
    team: PLAYER
    position: [3, 6]
    stats_override:
      movement_points: 5  # More flexible
      hp_max: 100
      
  - name: The Crosser
    class: CLERIC
    team: PLAYER
    position: [1, 6]
    stats_override:
      movement_points: 10  # Needs to cross when ready
      hp_max: 10  # Fragile!

objectives:
  victory:
    - type: reach_position
      position: [12, 6]
      unit_name: The Crosser
      description: Get the Crosser across the gap
      
  defeat:
    - type: protect_unit
      unit_name: The Crosser
    - type: turn_limit
      turns: 10  # Efficiency matters

settings:
  turn_limit: 10
  starting_team: PLAYER
```

## Experimental Ideas

### 11. Pacifist Run

**Concept**: Win without defeating any enemies.

```yaml
name: The Peaceful Path
description: Reach the exit without combat
author: Peace Designer

map:
  source: assets/maps/guard_patrol

units:
  # Minimal combat ability
  - name: Pacifist Monk
    class: CLERIC
    team: PLAYER
    position: [1, 5]
    stats_override:
      movement_points: 4
      strength: 1  # Can't really fight
      defense: 5
      evasion: 30
      
  # Many guards with patrol patterns
  - { name: Guard 1, class: WARRIOR, team: ENEMY, position: [5, 3] }
  - { name: Guard 2, class: WARRIOR, team: ENEMY, position: [7, 7] }
  - { name: Guard 3, class: WARRIOR, team: ENEMY, position: [9, 5] }
  - { name: Patrol, class: THIEF, team: ENEMY, position: [6, 5] }

objectives:
  victory:
    - type: reach_position
      position: [14, 5]
      unit_name: Pacifist Monk
      
  defeat:
    - type: defeat_unit
      unit_name: Guard 1
      description: You chose violence - mission failed
    - type: defeat_unit  
      unit_name: Guard 2
      description: You chose violence - mission failed
    - type: defeat_unit
      unit_name: Guard 3
      description: You chose violence - mission failed

settings:
  turn_limit: null
  starting_team: PLAYER
```

### 12. King of the Hill

**Concept**: Control specific positions for points.

```yaml
name: Territory Control
description: Hold key positions to earn victory
author: Control Designer

map:
  source: assets/maps/control_points

# In objects.yaml, define control regions

units:
  # Two equal teams
  # Team A
  - { name: A Knight, class: KNIGHT, team: PLAYER, position: [2, 5] }
  - { name: A Archer, class: ARCHER, team: PLAYER, position: [2, 6] }
  - { name: A Thief, class: THIEF, team: PLAYER, position: [2, 7] }
  
  # Team B  
  - { name: B Knight, class: KNIGHT, team: ENEMY, position: [12, 5] }
  - { name: B Archer, class: ARCHER, team: ENEMY, position: [12, 6] }
  - { name: B Thief, class: THIEF, team: ENEMY, position: [12, 7] }

objectives:
  victory:
    # Multiple control points
    - type: position_captured
      position: [7, 3]
      description: Control North Point
    - type: position_captured
      position: [7, 9]
      description: Control South Point
    - type: position_captured
      position: [7, 6]
      description: Control Center Point
      
  defeat:
    - type: all_units_defeated
    - type: turn_limit
      turns: 20

settings:
  turn_limit: 20
  starting_team: PLAYER
```

## Tips for Using These Examples

1. **Mix and Match**: Combine elements from different examples
2. **Adjust Difficulty**: Modify stats and unit counts
3. **Add Story**: Use descriptions and messages to create narrative
4. **Test Balance**: Play both sides to ensure fairness
5. **Iterate**: Start simple and add complexity gradually

## Creating Your Own

When designing scenarios, consider:

- **Theme**: What story are you telling?
- **Challenge**: What tactical problem are you presenting?
- **Choice**: What meaningful decisions can players make?
- **Pacing**: How does tension build over time?
- **Reward**: What makes victory satisfying?

Remember: The best scenarios are those that create memorable moments and interesting decisions!