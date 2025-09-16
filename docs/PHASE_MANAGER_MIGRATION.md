# Phase Manager Migration - Remaining Work

## Overview
We've successfully created a PhaseManager with event-driven state machine logic to centralize all phase transitions. However, there's still work needed to complete the migration and fix the original L key issue.

## Current Status
✅ **Completed:**
- Created PhaseManager with readable rule-based transition logic
- Updated Game class to initialize PhaseManager
- Updated Game class to emit events instead of direct phase transitions (partial)

## Remaining Work

### 1. Finish Game Class Migration
**File:** `src/game/game.py`

**Tasks:**
- Remove the old `_transition_game_phase()` and `_transition_battle_phase()` methods (lines 285-337)
- Remove the old `_emit_log()` method since PhaseManager has its own
- Update any remaining direct phase assignments to use events instead
- Clean up the battle phase transition in `_initialize_additional_managers` (line 518)

### 2. Update TimelineManager 
**File:** `src/game/timeline_manager.py`

**Critical Issue:** TimelineManager has 7 direct `self.state.battle.phase =` assignments that bypass the PhaseManager.

**Direct assignments to fix:**
- Line 265: `self.state.battle.phase = BattlePhase.UNIT_MOVING`
- Line 345: `self.state.battle.phase = BattlePhase.TIMELINE_PROCESSING`  
- Line 368: `self.state.battle.phase = BattlePhase.TIMELINE_PROCESSING`
- Line 378: `self.state.battle.phase = BattlePhase.TIMELINE_PROCESSING`
- Line 503: `self.state.battle.phase = BattlePhase.TIMELINE_PROCESSING`
- Line 839: `self.state.battle.phase = BattlePhase.TIMELINE_PROCESSING`

**Solution:** Replace these with appropriate event emissions:
- Emit `UnitTurnStarted` instead of setting UNIT_MOVING
- Emit `UnitTurnEnded` or `TimelineProcessed` instead of setting TIMELINE_PROCESSING

### 3. Update InputHandler
**File:** `src/game/input_handler.py`

**Critical Issue:** InputHandler has 10 direct phase assignments.

**Direct assignments to fix:**
- Line 253: `self.state.battle.phase = BattlePhase.UNIT_ACTING`
- Line 337: `self.state.battle.phase = BattlePhase.UNIT_ACTING`
- Line 346: `self.state.battle.phase = BattlePhase.ACTION_TARGETING`
- Line 374: `self.state.battle.phase = BattlePhase.UNIT_MOVING`
- Line 408: `self.state.battle.phase = BattlePhase.UNIT_ACTION_SELECTION`
- Line 518: `self.state.battle.phase = BattlePhase.UNIT_MOVING`
- Line 528: `self.state.battle.phase = BattlePhase.ACTION_MENU`
- Line 533: `self.state.battle.phase = BattlePhase.UNIT_ACTION_SELECTION`
- Line 544: `self.state.battle.phase = BattlePhase.ACTION_MENU`

**Solution:** Replace with appropriate event emissions:
- Emit `ActionSelected` when user selects an action
- Emit `MovementCompleted` when movement is done
- Emit `ActionExecuted` when actions complete

### 4. Update Input System Commands
**File:** `src/core/input_system/commands.py`

**Issue:** 7 direct phase assignments in command classes.

**Direct assignments to fix:**
- Line 137: `handler.state.battle.phase = handler.state.battle.previous_phase`
- Line 140: `handler.state.battle.phase = BattlePhase.TIMELINE_PROCESSING`
- Line 223: `handler.state.battle.phase = BattlePhase.UNIT_ACTING`
- Line 228: `handler.state.battle.phase = BattlePhase.UNIT_ACTING`
- Line 267: `handler.state.battle.phase = handler.state.battle.previous_phase`
- Line 271: `handler.state.battle.phase = BattlePhase.TIMELINE_PROCESSING`
- Line 278: `handler.state.battle.phase = BattlePhase.INSPECT`

**Solution:** Commands should emit events instead of directly setting phases.

### 5. Update TurnManager (if still used)
**File:** `src/game/turn_manager.py`

**Issue:** 2 direct phase assignments.
- Line 46: `self.state.battle.phase = BattlePhase.UNIT_SELECTION`
- Line 88: `self.state.battle.phase = BattlePhase.UNIT_SELECTION`

### 6. Missing Event Types
**Issue:** Some events referenced in PhaseManager rules may not exist yet.

**Events that need to be created or verified:**
- `MovementCompleted` - emitted when unit finishes moving
- `ActionSelected` - emitted when user selects an action
- `ActionExecuted` - emitted when action is completed
- `UnitTurnEnded` - emitted when unit's turn ends

**File:** `src/core/events.py` - check if these exist and create if needed.

### 7. Testing Strategy

**Priority 1: L Key Test**
- Create a test that loads a scenario and presses L key
- Verify that PhaseManager transitions from MAIN_MENU -> BATTLE correctly
- Verify that L key opens expanded log in BATTLE phase

**Priority 2: Phase Transition Test**
- Test each transition rule in PhaseManager
- Verify events properly trigger transitions
- Test that direct phase assignments are eliminated

## Root Cause of L Key Issue

The L key stopped working because:

1. **Game stayed in MAIN_MENU phase** after scenario loading
2. **RenderBuilder checks `state.phase == GamePhase.MAIN_MENU`** and takes early return
3. **No UI elements rendered** when in MAIN_MENU mode
4. **PhaseManager now handles the transition** from MAIN_MENU -> BATTLE via ScenarioLoaded event

## Expected Outcome

After completing this migration:
- All phase transitions will be centralized in PhaseManager
- Phase changes will be event-driven and traceable
- L key will work correctly because game will properly transition to BATTLE phase
- System will be more maintainable and easier to debug
- No managers will directly modify phase state

## Migration Order

**Recommended sequence:**
1. Finish Game class cleanup
2. Fix TimelineManager (most critical - handles turn flow)
3. Fix InputHandler (handles user input)
4. Fix Input System Commands
5. Test L key functionality
6. Test complete phase transition system
7. Clean up any remaining references