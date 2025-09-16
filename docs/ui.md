# 🖼 Mock 1 — Player Turn Screen

```
─────────────────────────────────────────────────────────────
 TIMELINE (Top of Screen)
 
 [ Ilya 🛡 Shield Wall ] → [ Raider A ⚔️ Charge ] 
   → [ Seren 🔥 Fireball (2 ticks) ] → [ ??? Hidden Action ] 
   → [ Marrek 🗡 Dagger Throw ] → [ 🔥 Fire Spread ]

─────────────────────────────────────────────────────────────
 BATTLEFIELD GRID (Center, 10x6 example)

 .   .   .   .   .   .   .   .   .   .
 .   🌲  🌲  🌲  🏹?  .   .   .   .   .
 .   🌲  🪵  🌲  .   .   .   .   .   .
 .   🌲  I🛡→→→R   .   .   .   .   .
 .   .   M   .   R   .   .   .   .   .
 .   .   .   .   .   .   .   .   .   .

 Overlays:
 - `🛡 arc` = Ilya’s Shield Wall interrupt zone.
 - `→→→` = Raider’s charge preview path.
 - `🏹?` = Fog-of-war enemy (Marksman silhouette).
 - AoE highlight: Seren targeting Fireball (3x3 tiles).

─────────────────────────────────────────────────────────────
 UNIT INFO PANEL (Bottom Left)

 SEREN — Mage
 HP: 22 / 28     Mana: 12 / 20
 Status: 🔥 Fireball Prep (2 ticks)
 Wounds: Burn Scar (-2 max HP)
 Next Action: in 280 ticks

─────────────────────────────────────────────────────────────
 ACTION MENU (Bottom Right)

 ➤ Fireball (Heavy, +180) [SELECTED]
    Quick Spark (Light, +70)
    Magic Bolt (Normal, +100)
    Ward (Prepare, +130)
    Move (1–3 tiles, +80 each)
    Item (Potion, Bandage)

─────────────────────────────────────────────────────────────
```

---

# 📊 Technical Specifications

### Layout

* **Screen Resolution Target**: 16:9 (baseline 1280x720 for SNES-style upscale).
* **Panels**:

  * Timeline: top bar, full width, height \~10–15% of screen.
  * Battlefield: center, \~65–70% of screen.
  * Unit Info: bottom-left, \~20% width, 20% height.
  * Action Menu: bottom-right, \~25% width, 20% height.

---

### Timeline

* **Data structure**: queue list.
* Each entry has:

  ```json
  {
    "unit": "Seren",
    "action": "Fireball",
    "icon": "🔥",
    "ticks_remaining": 2,
    "visibility": "full | partial | hidden"
  }
  ```
* Display order: sorted by next\_turn value.

---

### Battlefield

* **Grid-based** (recommended 10x6 or scalable).
* Each tile stores:

  ```json
  {
    "terrain": "tree | log | empty | fire",
    "unit": "Ilya | Marrek | Seren | Raider | null",
    "fog_state": "visible | silhouette | hidden",
    "overlay": ["interrupt_arc", "aoe_preview", "charge_path"]
  }
  ```

---

### Unit Info Panel

* Displays **current selected unit** (player-controlled).
* Data:

  ```json
  {
    "name": "Seren",
    "class": "Mage",
    "hp": { "current": 22, "max": 28 },
    "mana": { "current": 12, "max": 20 },
    "status": ["Fireball Prep (2 ticks)"],
    "wounds": ["Burn Scar (-2 max HP)"],
    "next_action": 280
  }
  ```

---

### Action Menu

* Vertical list of available actions.
* Each entry shows:

  * Name
  * Weight cost (+ticks)
  * Type (Quick/Normal/Heavy/Prepare)
* Highlighted action shows **preview overlays** on battlefield and updated timeline projection.

---

# 🎭 Gameplay Context for This Mock

* Seren is selected → shows her info, Fireball selected.
* Timeline preview reveals **delayed turn** (+180).
* Battlefield overlay shows **AoE zone** + **enemy charge path** + **interrupt arc**.
* Player must decide whether to risk committing to Fireball (heavy delay, vulnerability).

---

✅ This single mock already showcases:

* **Timeline mechanics**
* **Action weights preview**
* **Interrupt zone**
* **Fog-of-war enemy**
* **Unit wounds/status**
* **Environmental escalation slot (🔥 Fire Spread)**

