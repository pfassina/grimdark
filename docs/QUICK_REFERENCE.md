# Grimdark SRPG Quick Reference

## Terrain Tile IDs

```
1 = Plain (.)      - Move: 1, Def: 0
2 = Forest (♣)     - Move: 2, Def: +1, Avoid: +20%
3 = Mountain (▲)   - Move: 3, Def: +2, Avoid: +30%
4 = Water (≈)      - Blocks movement
5 = Road (=)       - Move: 1, Def: 0
6 = Fort (■)       - Move: 1, Def: +3, Avoid: +10%
7 = Bridge (╬)     - Move: 1, Def: 0
8 = Wall (█)       - Blocks movement & vision
```

## Unit Classes

```
KNIGHT   - Tank: High HP/Def, Low Move (3)
WARRIOR  - Balanced: Medium all stats
ARCHER   - Ranged: Attack 2-3 tiles away
MAGE     - Ranged: High damage, fragile
CLERIC   - Support: Can heal allies
THIEF    - Scout: High Move (5), High Avoid
```

## Map File Structure

```
your_map/
├── ground.csv     # Required: Base terrain (use tile IDs)
├── walls.csv      # Optional: Overlay structures (0 = empty)
├── features.csv   # Optional: Decorations (0 = empty)
└── objects.yaml   # Optional: Spawns, regions, triggers
```

## Minimal Scenario

```yaml
name: Quick Battle
map:
  source: assets/maps/your_map

units:
  - name: Hero
    class: KNIGHT
    team: PLAYER
    position: [1, 1]
    
  - name: Enemy
    class: WARRIOR
    team: ENEMY
    position: [5, 5]

objectives:
  victory:
    - type: defeat_all_enemies
  defeat:
    - type: all_units_defeated
```

## Objects.yaml Quick Template

```yaml
spawns:
  - name: "Spawn1"
    team: PLAYER
    pos: [1, 1]
    class: KNIGHT    # Optional

regions:
  - name: "Safe Zone"
    rect: [0, 0, 3, 3]    # x, y, width, height
    defense_bonus: 2
    heal_per_turn: 1      # Optional

triggers:
  - name: "Turn 5 Event"
    type: "turn_start"
    condition: "turn:5"
    action: "display_message"
    data:
      message: "Reinforcements arrive!"
```

## Victory Objective Types

```yaml
defeat_all_enemies              # Kill all enemies
survive_turns: {turns: 10}      # Last X turns
reach_position: {position: [x,y], unit_name: "Hero"}
defeat_unit: {unit_name: "Boss"}
position_captured: {position: [x,y]}
```

## Defeat Objective Types

```yaml
protect_unit: {unit_name: "VIP"}     # Unit must survive
all_units_defeated                   # Don't lose all units
turn_limit: {turns: 20}              # Win within X turns
```

## Stat Override Options

```yaml
stats_override:
  # Health
  hp_max: 30
  hp_current: 30
  
  # Combat
  strength: 8
  defense: 5
  accuracy: 90
  evasion: 15
  critical: 10
  
  # Movement
  movement_points: 4
  
  # Range (archers/mages)
  range_min: 2
  range_max: 3
  
  # Speed (turn order)
  speed: 5
```

## Common YAML Anchors Pattern

```yaml
# Define reusable stats
_tank_stats: &tank_stats
  hp_max: 35
  defense: 8
  movement_points: 3

units:
  - name: Tank 1
    class: KNIGHT
    team: PLAYER
    position: [1, 1]
    stats_override:
      <<: *tank_stats
      
  - name: Tank 2
    class: KNIGHT
    team: PLAYER
    position: [2, 1]
    stats_override:
      <<: *tank_stats
      strength: 10    # Override specific stat
```

## Region Effect Options

```yaml
regions:
  - name: "Fortress"
    rect: [5, 5, 3, 3]
    defense_bonus: 3        # +3 defense
    avoid_bonus: 20         # +20% dodge
    heal_per_turn: 2        # Heal 2 HP/turn
    damage_per_turn: 0      # Damage per turn
    description: "Text"     # Tooltip
```

## Testing Commands

```bash
# Test your scenario
nix develop --command python demos/demo_scenario.py assets/scenarios/your_scenario.yaml

# Run in auto-play mode
nix develop --command python demos/demo.py

# Validate architecture
nix develop --command python tests/test_architecture.py
```

## File Path Examples

```yaml
# In scenarios - paths relative to project root
map:
  source: assets/maps/fortress

# Standard structure
assets/
├── maps/
│   └── fortress/
│       ├── ground.csv
│       └── objects.yaml
└── scenarios/
    └── siege.yaml
```

## Tips

1. **Start Simple**: Test with one unit per team first
2. **Use Spawn Points**: Let objects.yaml handle positions
3. **Layer Order**: Ground → Walls → Features
4. **Tile 0**: Means "empty" in overlay layers
5. **Unit Names**: Must be unique within a scenario
6. **Test Often**: Run scenario after each major change

## Debug Checklist

- [ ] CSV dimensions match across layers?
- [ ] All tile IDs valid (1-8)?
- [ ] Unit positions within map bounds?
- [ ] Spawn point names unique?
- [ ] Victory conditions achievable?
- [ ] File paths use forward slashes?