```markdown
# ⚔️ The Grinding Wheel — Combat System Specification

## Overview
A **grimdark, turn-based tactical combat system** for an SRPG inspired by the SNES era.  
Core pillars:
- **Fluid turn order** — no rigid player/enemy phases, but not real-time.
- **Every action counts** — choices trade speed for power.
- **Prediction > reaction** — interrupts reward foresight, punish waste.
- **Imperfect information** — hidden intents, fog-of-war, uncertainty.
- **Escalation** — environments and enemies worsen if you stall.
- **Chaos, not dice rolls** — randomness emerges from the world, not coin flips.
- **Victory = survival with scars** — no perfect wins, only loss mitigation.

---

## 1. Timeline & Action Weights

### Mechanic
- The battle runs on a **fluid timeline queue**.
- Each unit has a **Base Speed** stat.
- Each action adds an **Action Weight** cost.
- Formula:
```

next\_turn = current\_time + base\_speed + action\_weight

```

### Action Weights
| Action Type      | Examples                 | Weight (approx.) | Effect |
|------------------|--------------------------|------------------|--------|
| **Quick**        | Dagger stab, step move   | +50–80           | Early return, weak effect |
| **Normal**       | Sword swing, arrow shot  | +100             | Standard pacing |
| **Heavy**        | Fireball, charge, AoE    | +150–200+        | Delayed turn, powerful |
| **Prepare**      | Overwatch, Shield Wall   | +120–140         | Delay, sets interrupt |

---

## 2. Interrupts & Prepared Actions

### Mechanic
- Units may **spend their turn preparing** an interrupt.
- Prepared actions are **pending triggers** until used or expired.

### Examples
| Interrupt Type     | Trigger Condition                | Result |
|--------------------|----------------------------------|--------|
| **Prepared Strike**| Enemy enters chosen tile/arc     | Immediate attack |
| **Counter-Spell**  | Enemy begins casting in LoS      | Chance to cancel |
| **Shield Wall**    | First adjacent attack this round | Block/reduce dmg |
| **Ambush**         | Enemy moves within fog-of-war    | Surprise strike |

👉 *Risk–reward*: lifesaving if guessed right, wasted if wrong.

---

## 3. Imperfect Information

### Mechanic
- The timeline shows **incomplete enemy intent**.
- Hidden actions appear as `???` until triggered or partially revealed.
- Some reveal intent but not target (“Preparing Charge”).

### Example
```

Now → Ilya (Quick Strike)
Next → Raider A (???)
Soon → Seren (Fireball Prep)
Later → Marrek (Dagger Throw)

```
- After 1 tick, Raider A’s `???` becomes **“Charge Attack → Direction North.”**

---

## 4. Escalation Pressure

### Mechanic
- **Environments deteriorate** the longer fights last.
- **Reinforcements**, **hazards**, and **morale decay** punish stalling.
- **Resources persist across battles**:
  - Wounds (scars, amputations).
  - Limited healing items.
  - Mana/stamina don’t fully reset.

### Examples
- Fire spreads in forest → blocks LoS, damages units.
- Collapsing wall → destroys cover, creates hazard.
- Bandit morale → some flee, others frenzy.

---

## 5. Randomness as Chaos

### Principle
- No % hit rolls: attacks land if in range/LoS.
- Chaos comes from:
  - **Damage variance** (6–10 dmg instead of flat 8).
  - **Environmental randomness** (fire spreads unpredictably).
  - **AI variance** (panic, disobedience, wild animals).

---

## 6. Victory = Cutting Losses

### Principle
- Rarely clean victories.
- Players must balance survival vs. sacrifice.
- Campaign progression remembers scars.

### Examples
- Save mage → lose supplies.
- Escape with 2 survivors → lose loot.
- Win fight → knight crippled.

---

## 7. Example Round (Forest Ambush)

### Setup
- **Allies**: Ilya (Knight), Marrek (Rogue), Seren (Mage)
- **Enemies**: Raider A, Raider B, Hidden Marksman

### Timeline Start
```

Now → Ilya (Shield Wall)
Next → Raider A (Charge Attack, Heavy)
Soon → Seren (Fireball Prep, Heavy)
???  → Enemy Hidden Action
Later → Marrek (Dagger Throw, Quick)

```

### Resolution
1. **Ilya** prepares Shield Wall → delays next turn.
2. **Raider A** charges → intercepted by Ilya’s shield (interrupt).
3. **Seren** preps Fireball → vulnerable during cast.
4. **??? Revealed**: Marksman → Aimed Shot at Seren.
5. **Marrek** dagger throw → staggers Marksman, cancels arrow.
6. **Fireball** lands → hits Raiders, ignites forest (🔥 hazard spreads).

---

## 8. UI Wireframes

### A. Timeline (Top Bar)
```

\[ Ilya 🛡 Shield Wall ] → \[ Raider A ⚔️ Charge ] → \[ Seren 🔥 Fireball (2) ]
→ \[ ??? Hidden Action ] → \[ Marrek 🗡 Dagger Throw ] → \[ 🔥 Fire Spread ]

```
- 🛡 = interrupts, 🔥 = prep spells, ??? = hidden intent.

---

### B. Battlefield Grid
```

.  .  .  .  .  .  .  .  .  .
.  🌲  🌲  🌲  🏹?  .  .  .  .
.  🌲  🪵  🌲  .  .  .  .  .  .
.  🌲  I🛡→→→R  .  .  .  .  .  .
.  .  M  .  R  .  .  .  .  .  .
.  .  .  .  .  .  .  .  .  .  .

```
- `I` = Ilya (🛡 arc = Shield Wall zone).  
- `R` = Raider (→ charge path).  
- `🏹?` = Hidden Marksman.  
- `🔥` = fire spreading hazard.  

---

### C. Full Player Turn HUD
```

──────────────────────────────────────────────
TIMELINE
\[ Ilya 🛡 Shield Wall ] → \[ Raider A ⚔️ Charge ]
→ \[ Seren 🔥 Fireball (2) ] → \[ ??? ] → \[ Marrek 🗡 Throw ]
──────────────────────────────────────────────
BATTLEFIELD
.   .   .   .   .   .   .   .   .   .
.   🌲  🌲  🔥  🏹🎯  .   .   .   .   .
.   🌲  🪵  🌲  .   .   .   .   .   .
.   🌲  I🛡→→→R   .   .   .   .   .
.   .   M   .   R   .   .   .   .   .
──────────────────────────────────────────────
UNIT PANEL
ILYA — Knight
HP: 32 / 45   Stamina: 18 / 20
Status: 🛡 Guard Active
Wounds: Arm Scar (-5 atk), Fatigued
Next Action: 120 ticks
──────────────────────────────────────────────
ACTION MENU
➤ Quick Strike (+70)
Normal Attack (+100)
Heavy Bash (+150)
Shield Wall (+130) \[ACTIVE]
Move (1–3 tiles, +80 each)
Item (Potion, Bandage)
──────────────────────────────────────────────

```

---

### D. Enemy Turn HUD
```

──────────────────────────────────────────────
TIMELINE
NOW → \[ Raider A ⚔️ Charge ] → \[ Seren 🔥 Fireball (1) ]
\[ Marksman 🏹 Aimed Shot → ??? ] → \[ Marrek 🗡 Throw ]
──────────────────────────────────────────────
BATTLEFIELD
.   .   .   .   .   .   .   .   .   .
.   🌲  🌲  🔥  🏹🎯  .   .   .   .   .
.   🌲  🪵  🌲  .   .   .   .   .   .
.   🌲  I🛡→→→R   .   .   .   .   .
.   .   M   .   R   .   .   .   .   .
──────────────────────────────────────────────
ENEMY INFO
Raider A — Charging
HP: 24 / 36
Status: Committed (cannot cancel)
──────────────────────────────────────────────
PLAYER INTERRUPTS
Ilya 🛡 Shield Wall (1 trigger, facing north)
Marrek — None
Seren — Fireball Prep (vulnerable)
──────────────────────────────────────────────

```

---

## 9. Design Philosophy Summary

- **Every action has weight** — time is the real currency.  
- **Interrupts are gambles** — you win or waste tempo.  
- **Imperfect info fuels tension** — `???` keeps paranoia alive.  
- **Escalation forces urgency** — waiting = death.  
- **Randomness = chaos, not dice** — world betrays you, not dice rolls.  
- **Victory = survival** — battles scar you, campaigns test endurance.  

---
```

