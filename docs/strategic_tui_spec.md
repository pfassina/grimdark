# Strategic Layer TUI — UI/UX Specification (for a Shining Force–style SRPG)

> This spec defines the terminal UI (TUI) elements and interactions for the **strategic/battle layer** and maps them directly to your current **push-based, renderer-agnostic** framework (RenderContext, generic InputEvents, layered drawing). Where relevant, I call out the exact contract(s) and patterns from your rendering guide so implementation stays frictionless.

---

## 1) Goals, Scope, and Principles

**Goals**
- Deliver a complete, ergonomic terminal interface for tactical battles that feels faithful to SNES-era SRPGs.
- Keep **game logic fully separate** from presentation; UI is a *pure* consumer of `RenderContext` and a *pure* producer of `InputEvent`s.
- Enforce **unidirectional data flow**: State → `RenderContext` → Renderer → Display, with input events flowing back.

**Out-of-scope**
- Pre-battle party management, shops, story cutscenes. (Those can reuse the same primitives later.)

---

## 2) Tech-Stack Alignment (What the Renderer Consumes & Emits)

- **Render input**: one **`RenderContext` snapshot per frame**; we render what it describes and nothing else.  
  Key fields we rely on:
  - Camera/viewport: `camera_x`, `camera_y`, `viewport_width`, `viewport_height`  
  - World: `world_width`, `world_height`  
  - Draw lists: `tiles`, `units`, `overlays`, `cursor`, `menus`, `texts`
- **Renderable types** (already defined): Tiles, Units, Overlays, Menus, Texts (+ Cursor). We’ll reuse these for all components below.
- **Layering**: TERRAIN → OBJECTS → UNITS → EFFECTS → UI → OVERLAY. All component specs below assume this order.
- **Input**: Renderer converts terminal keystrokes/mouse to **generic `InputEvent`**: `KEY_PRESS`, `MOUSE_CLICK`, `MOUSE_MOVE`, `QUIT`. We’ll map controls to these.  
  **Standard controls** used by this spec: Movement (Arrows/WASD), Confirm (Enter/Space), Cancel (Esc/Q), Wait (W), Attack (A), End Turn (E).
- **Terminal renderer features**: Unicode + ANSI colors, interactive menus, raw terminal input—ideal for a modern TUI.

---

## 3) Screen Layout & Sizing (80×26 Baseline, Responsive)

**Baseline** (recommend): `80×26` characters (fits common terminals). Works up to widescreen (e.g., 120×36). The layout adapts:

```
┌─────────────────────────────────────┬─────────────────────────┐
│               MAP                   │      RIGHT SIDEBAR      │
│ (scrolls via camera_x/camera_y)     │  (context panels/menus) │
│                                     │                         │
│                                     │                         │
├─────────────────────────────────────┴─────────────────────────┤
│                      BOTTOM INFO STRIP / LOG                  │
└───────────────────────────────────────────────────────────────┘
```

- **Map viewport**: fills all space left of the **Right Sidebar** and above the **Bottom Strip**. Dimensions computed as:
  - `map_w = viewport_width - sidebar_w`
  - `map_h = viewport_height - bottom_h`
- **Right Sidebar**: fixed width **28 cols** (if `viewport_width ≥ 90`), else collapses to **24 cols** and some subpanels become toggleable overlays.
- **Bottom Strip / Log**: fixed height **3 rows** (collapsible to 1 row on very short terminals).

All positions are in **screen cells**, but mapping from world → screen uses the given camera/viewport in `RenderContext`.

---

## 4) Components (By Area)

### 4.1 Map Viewport (Grid, Cursor, Overlays)
**Purpose**: Draw terrain, units, ranges, and the targeting cursor.

- **Data**: `tiles`, `units`, `overlays`, `cursor` from `RenderContext`.
- **Drawing order**: TERRAIN → UNITS → (UI) → OVERLAY. (OVERLAY on top so ranges/cursor remain visible.)
- **Tile glyphs**: single wide glyph per tile (e.g., `░/▒/▓` for elevation/density), or letter codes (`.` plains, `^` mountains).  
- **Unit glyphs**: single letter + color by team (B/R/G/Y), bold when `is_selected`. HP below via tiny bar (see 4.5).
- **Cursor**: inverse video + bright border around the tile; **blink 2Hz** (renderer-timed). Cursor location comes from `cursor`.  
- **Overlays**:
  - `MOVEMENT_RANGE`: cyan fill on reachable tiles  
  - `ATTACK_RANGE`: red fill/hatch  
  - `DANGER_ZONE`: dim red background layer  
  These map to `OverlayTileRenderData` with `overlay_type` and optional team color.

**Keyboard behaviors**
- Arrow/WASD scrolls cursor; if cursor nears edges, pan camera by 1 tile (respect `world_width/height`).
- `Enter/Space`: confirm (select unit / confirm tile). `Esc/Q`: cancel/back. Emitted as `KEY_PRESS` events.

**Mouse (optional)**  
- `MOUSE_MOVE` sets hover tile; `MOUSE_CLICK` selects/targets. Renderer translates to generic events.

---

### 4.2 Right Sidebar (Context Panels)
Right panel hosts **Terrain Info**, **Unit Info**, and **Command Menus** in a vertical stack. Each is a `MenuRenderData` or `TextRenderData` block with box borders.

**Panel sizing (28w × variable h)**  
- Title row: 1  
- Body: variable  
- Box chars: Unicode box-drawing for clarity.

#### 4.2.1 Terrain Info (top; ~6–7 rows)
Shows tile under cursor or selected unit’s tile.
```
┌ Terrain: FOREST ┐
│ Move: 2  EVA: 15│
│ Blocks LOS: No  │
│ Height: 1       │
└─────────────────┘
```

#### 4.2.2 Unit Info (middle; ~10–12 rows)
When cursor is on a unit:
```
┌ Unit: Archer (Blue) ┐
│ LV 12  EXP 34       │
│ HP [██████░░]  24/38│
│ ATK 26  DEF 12  SPD 9│
│ Status: Can Act     │
│ Effects: Poison(2)  │
└─────────────────────┘
```

#### 4.2.3 Command Menu (bottom; ~6–10 rows)
Appears when a controllable unit is selected and has actions.
```
┌ Actions ┐
│ Move    │
│ Attack  │
│ Skill   │
│ Item    │
│ Wait    │
└─────────┘
```

---

### 4.3 Bottom Strip (Message Log)
**Height 3** (collapsible to 1). Displays most recent battle messages:
```
[Turn 5: Player Phase] Archer moved to (12,8).  Attacked Soldier for 14 (HIT 78% CRIT 6%).
```
- Data via `TextRenderData`; oldest lines fade (dim ANSI).
- Toggle detail (`Tab`) expands to show last ~20 lines in an overlay window.

---

### 4.4 Battle Forecast (Popup)
Appears during targeting to preview damage/hit/crit and support bonuses.
```
   ┌ Battle Forecast ┐
   │ Archer ▶ Soldier│
   │ Dmg 14  Hit 78% │
   │ Crit 6%  AS +3  │
   │ Counter: Yes    │
   └─────────────────┘
```

---

### 4.5 Bars & Gauges (HP/MP/Charge)
Rendered in text using a 10-cell bar:
- **Spec**: `[██████░░░]` where filled = `⌊(current/max)*10⌋`.
- Color: green (>60%), yellow (30–60%), red (<30%).

---

### 4.6 Turn/Phase Banner (Top-left ephemeral)
On phase change:
```
┌──────────────────┐
│   PLAYER PHASE    │
└──────────────────┘
```

---

### 4.7 Objectives / Help Overlays (full-screen modal)
- **Objectives (O)**: Victory/defeat conditions, turn limit, reinforcements hints.
- **Help (?)**: Key bindings.

---

### 4.8 Minimap (Optional toggle: M)
Compressed 2×1 chars per world tile. Current camera bounds shown as a rectangle; teams colored by ANSI.

---

### 4.9 Confirmation Dialogs
For irreversible actions (End Turn, Discard, Flee):
```
┌ End Player Turn? ┐
│  Yes     No      │
└──────────────────┘
```

---

## 5) Interaction States & Flows

**Global controls** (always):  
- **Arrows/WASD** move cursor / selection; **Esc/Q** backs out; **Enter/Space** confirms; **E** End Turn (with confirm).

**State machine (high-level):**
1) **Explore/Idle** → 2) **Unit Selected** → 3) **Move Targeting** → 4) **Action Menu** → 5) **Attack/Skill Targeting** → 6) **Confirm Attack** → 7) **Post-Action** → 8) **End Turn**

---

## 6) Data Contracts (UI → RenderContext Mapping)

We **do not** read game state “directly”; we only render what `RenderContext` tells us.

**We will use:**
- `tiles`, `units`, `overlays`, `cursor`, `menus`, `texts`

---

## 7) Visual Style Guide (Terminal)

- **Borders**: Unicode box-drawing.  
- **Colors**: Team colors, overlays in cyan/red, selection inverse video.  
- **Focus cues**: Active panel bold; inactive dim.

---

## 8) Performance & Update Rules

- Render every frame from the provided snapshot; optimize drawing.

---

## 9) Input Mapping (Renderer → Game)

Renderer translates terminal input to generic `InputEvent`s:

- Arrows/WASD → `KEY_PRESS`
- Enter/Space → `KEY_PRESS`
- Esc/Q → `KEY_PRESS`
- A/W/E → `KEY_PRESS`
- Mouse click → `MOUSE_CLICK`

---

## 10) Component Specs (Coordinates & Sizes)

| Component            | Anchor (x,y)                 | Size (w×h)                         | Data Type(s)            |
|---|---|---|---|
| Map Viewport         | `(0,0)`                      | `W - sidebar_w` × `H - bottom_h`   | `tiles`, `units`, `overlays`, `cursor` |
| Right Sidebar        | `(W - sidebar_w, 0)`         | `sidebar_w` × `H - bottom_h`       | `menus`, `texts`        |
| Terrain Panel        | same as Sidebar (top stack)  | `sidebar_w` × `6–7`                | `texts`                 |
| Unit Panel           | below Terrain                | `sidebar_w` × `10–12`              | `texts`                 |
| Command Menu         | bottom of Sidebar            | `sidebar_w` × `6–10`               | `menus`                 |
| Bottom Strip (Log)   | `(0, H - bottom_h)`          | `W` × `bottom_h`                   | `texts`                 |
| Forecast Popup       | near cursor (auto-fit)       | `24–28` × `5`                      | `menus`                 |
| Objectives Overlay   | centered                      | `min(64,W-4)` × `min(16,H-4)`      | `menus`/`texts`         |
| Help Overlay         | centered                      | `min(64,W-4)` × `min(20,H-4)`      | `menus`/`texts`         |
| Minimap              | top-right or overlay         | `≤ sidebar_w` × `≤ (H-bottom_h)`   | `texts`                 |

---

## 11) ASCII Mockups

(Examples omitted for brevity; see main text.)

---

## 12) Error States & Edge Cases

- Menu overflow scroll indicators.  
- Small terminal collapse modes.  
- Color fallback for no-ANSI.

---

## 13) Testing Checklist

- Layer correctness  
- Viewport scrolling  
- Input combos  
- Edge tile clipping  
- Menu disabled items/scrolling  
- Forecast numbers  
- Performance redraw

---

## 14) Implementation Notes

- Implement in `TerminalRenderer` (`render_frame` enumerates context lists by layer and draws; then `present()`).  
- Input: map terminal events to `InputEvent`s.  
- Extend framework by adding new Renderables if needed.

---

## 15) Future Extensions

- Animated cursor  
- Status effect icons  
- Contextual tooltips  
- Global “Danger Zone” overlay

---

### Appendix A — Control Map

- Move: Arrows / WASD  
- Confirm: Enter / Space  
- Cancel: Esc / Q  
- Attack: A  
- Wait: W  
- End Turn: E  
- Objectives: O  
- Help: ?  
- Minimap: M  
- Sidebar Tabs: Tab  

---

### Appendix B — Rendering Order

1) Terrain  
2) Units  
3) UI  
4) Overlays  

