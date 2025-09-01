```markdown
# Migration Guide: From JSON/TXT to CSV + YAML for SRPG Content

This document describes how to migrate the current asset formats (ASCII TXT maps and JSON scenarios/templates) into a **CSV + YAML–based workflow**. The goal is to make map editing more structured, support layered maps, and keep configuration human-friendly, while ensuring an easy path to future sprite-based rendering.

---

## 1. Current State

- **Maps**: ASCII `.txt` files with glyphs (e.g., `#`, `.`, `~`) representing tiles.
- **Scenarios**: JSON files with units, objectives, and settings.
- **Unit templates**: JSON files with per-class stats.

Issues:
- ASCII maps are hard to scale to large maps or multiple layers.
- JSON is strict but verbose and lacks comments.
- Repetition in templates/scenarios leads to noisy diffs.

---

## 2. Target State

- **Maps**: Layered `.csv` files for tile IDs (integers).
- **Tileset metadata**: `tileset.yaml` that maps IDs → glyphs/colors (for TUI), plus gameplay properties.
- **Objects & spawns**: `objects.yaml` per map, listing spawns, triggers, regions.
- **Scenarios & templates**: YAML files for authoring (with comments, anchors), compiled to JSON for runtime.

---

## 3. Map Format

### 3.1. Example Map Directory

```

assets/maps/fortress/
ground.csv
walls.csv
decor.csv
objects.yaml
tileset.yaml

````

### 3.2. Example `ground.csv`

```csv
1,1,1,1,1,1
1,2,2,2,2,1
1,2,3,3,2,1
1,2,2,2,2,1
1,1,1,1,1,1
````

* Each cell = integer tile ID.
* Multiple CSVs = multiple layers (ground, walls, bridges, etc.).

### 3.3. Example `tileset.yaml`

```yaml
tiles:
  1:
    glyph: "#"
    fg: "gray"
    bg: "none"
    passable: false
    defense: 3
  2:
    glyph: "."
    fg: "white"
    bg: "none"
    passable: true
    move_cost: 1
  3:
    glyph: "~"
    fg: "cyan"
    bg: "none"
    passable: false
    move_cost: 99
```

Properties are shared between TUI (glyph, colors) and gameplay (passable, defense, costs). Later, sprite metadata can be added:

```yaml
sprite: { sheet: "terrain.png", u: 32, v: 64 }
```

### 3.4. Example `objects.yaml`

```yaml
spawns:
  - { name: "Sir Aldric", team: "PLAYER", pos: [2,2] }
  - { name: "Enemy Captain", team: "ENEMY", pos: [4,1] }

regions:
  - { name: "Keep", rect: [1,1, 2,2], defense_bonus: 2 }
```

---

## 4. Scenarios & Unit Templates

### 4.1. Scenario (YAML authoring)

```yaml
name: Defense of Fort Grimhold
map: assets/maps/fortress/

units:
  - { name: "Sir Aldric", class: KNIGHT, team: PLAYER, pos: [2,2] }
  - { name: "Archer Elena", class: ARCHER, team: PLAYER, pos: [3,2] }
  - { name: "Enemy Captain", class: WARRIOR, team: ENEMY, pos: [4,1] }

objectives:
  victory:
    - { type: survive_turns, turns: 10 }
    - { type: defeat_all_enemies }
  defeat:
    - { type: protect_unit, unit_name: "Sir Aldric" }

settings:
  turn_limit: 15
  starting_team: PLAYER
```

During the build step this YAML is compiled to JSON (matching your existing runtime schema).

### 4.2. Unit Templates (YAML with anchors)

```yaml
unit_templates:
  _melee_defaults: &melee_defaults
    movement: { points: 3 }
    combat: { range_min: 1, range_max: 1 }

  KNIGHT:
    <<: *melee_defaults
    health: { hp_max: 25 }
    combat: { <<: *melee_defaults.combat, strength: 7, defense: 5 }
    status: { speed: 3 }

  ARCHER:
    movement: { points: 4 }
    combat: { strength: 5, defense: 2, range_min: 2, range_max: 3 }
    health: { hp_max: 18 }
    status: { speed: 6 }
```

---

## 5. Using CSV + YAML in the Game

### 5.1. Loading Pipeline

1. **Read CSVs** into integer 2D arrays.
2. **Lookup IDs** in `tileset.yaml` → determine glyphs/colors + gameplay properties.
3. **Overlay layers** in order (ground → walls → decor).
4. **Apply `objects.yaml`**: place units, mark regions.
5. **Render**:

   * **TUI mode**: use glyph/fg/bg from `tileset.yaml`.
   * **Future sprite mode**: use sprite fields instead.

### 5.2. Example TUI Render Loop

```python
import csv, yaml

# load csv
with open("ground.csv") as f:
    grid = list(csv.reader(f))

# load tileset
tileset = yaml.safe_load(open("tileset.yaml"))["tiles"]

# draw
for y, row in enumerate(grid):
    for x, cell in enumerate(row):
        tile = tileset[int(cell)]
        glyph = tile["glyph"]
        fg = tile["fg"]
        bg = tile["bg"]
        draw_to_terminal(x, y, glyph, fg, bg)
```

---

## 6. Migration Steps

1. **Define a stable tileset.yaml** mapping your current ASCII glyphs → IDs.
2. **Write a converter**: ASCII `.txt` → `ground.csv` + `tileset.yaml`.

   * Replace glyphs with IDs according to the mapping.
3. **Split metadata**: move unit spawns/objectives out of maps into `objects.yaml` + scenario YAML.
4. **Add a build step**: YAML (scenarios/templates) → JSON (engine runtime).
5. **Update engine loader** to: load CSV grids + YAML tileset + YAML objects.

---

## 7. Benefits

* Human-friendly editing (CSV/YAML).
* Layers supported naturally (multiple CSVs).
* Comments, anchors, and reusable definitions via YAML.
* Same data feeds both TUI (glyphs/colors) and future sprite renderer.
* Source control friendly (diffs remain readable).
* Future-proof: straightforward to export/import to Tiled later if desired.

---

## 8. Future Work

* Add **schema validation** for YAML (ensure required fields).
* Optional **ASCII preview generator** (convert CSV back to ASCII for quick code reviews).
* Later, add a **Tiled export step** so maps can be visually edited in a GUI without breaking compatibility.
```
```

