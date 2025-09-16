# Event-Driven Architecture Migration Guide

## Why This Migration?

### The Problem: "Spaghettification"
The original manager system had become a complex web of cross-dependencies where managers directly imported and called each other:

```
TimelineManager → LogManager, UIManager
CombatManager → LogManager, MoraleManager, EscalationManager  
InputHandler → CombatManager, UIManager, LogManager
MoraleManager → LogManager, EscalationManager
EscalationManager → LogManager, HazardManager, MoraleManager
```

This created several critical issues:
- **Circular Dependencies**: Managers importing each other created import cycles
- **Tight Coupling**: Changes to one manager broke multiple other managers
- **Testing Difficulty**: Unit testing required mocking numerous manager dependencies
- **Code Complexity**: Understanding data flow required tracing through multiple managers
- **Maintainability**: Adding features required touching multiple interconnected systems

### The Solution: Event-Driven Architecture
Replace all cross-dependencies with a centralized EventManager that coordinates communication:

```
All Managers → EventManager ← All Managers
     ↓                           ↑
GameState (shared data)    Events (coordination)
```

**Benefits Achieved**:
- **Single Responsibility**: Each manager handles exactly one domain
- **Loose Coupling**: Managers only know about EventManager and GameState
- **Easy Testing**: Managers can be unit tested in complete isolation
- **Clear Data Flow**: All communication is traceable through event emissions
- **Extensibility**: New managers can be added without touching existing code

## Major Design Decisions

### 1. **EventManager is Required, Not Optional**
**Decision**: EventManager must be a required constructor parameter for all managers
**Rationale**: 
- Eliminates "hybrid mode" where some features work without events
- Forces consistent architecture across all managers
- Makes event-driven communication the primary pattern
- Prevents accidental fallback to direct manager calls

### 2. **Pure Data Structures vs Decision-Making Managers**
**Decision**: Map and core data structures emit NO events; managers emit events after data operations
**Architecture**:
```python
# WRONG - Data structure emitting events
def move_unit(self, unit_id, position):
    # ... move logic ...
    self.event_manager.publish(UnitMoved(...))  # NO!

# RIGHT - Manager emits events  
def handle_movement(self, unit_id, position):
    if self.game_map.move_unit(unit_id, position):  # Pure data operation
        self.event_manager.publish(UnitMoved(...))  # Manager decision
```
**Rationale**:
- Clear separation between data storage and business logic
- Map can be tested without event dependencies
- Managers control when and why events are emitted
- Data structures remain simple and focused

### 3. **Immediate vs Queued Event Processing**
**Decision**: Support both immediate dispatch and queued processing
**Implementation**:
```python
# Immediate - for real-time coordination
event_manager.publish(UnitMoved(...))  

# Queued - for batch processing
event_manager.queue_event(TurnProcessed(...))
event_manager.process_queue()
```
**Rationale**:
- Immediate events for tight coordination (combat, UI updates)
- Queued events for turn-based processing and ordering control
- Prevents infinite event loops and stack overflow

### 4. **Rich Event Payloads with Context**
**Decision**: Events include full context, not just minimal data
**Example**:
```python
UnitMoved(
    turn=5,
    unit_name="Knight",
    unit_id="unit_123", 
    team=Team.PLAYER,
    from_position=(3, 4),
    to_position=(5, 6),
    movement_cost=2,
    remaining_movement=1
)
```
**Rationale**:
- Subscribers get all context needed for decisions
- Reduces need for additional data lookups
- Makes events self-contained and debuggable
- Supports rich logging and analytics

### 5. **Priority-Based Event Handling**
**Decision**: Events can be processed with priority ordering
**Implementation**:
```python
event_manager.subscribe(EventType.UNIT_MOVED, callback, priority=10)
event_manager.subscribe(EventType.UNIT_MOVED, callback, priority=5)
# Priority 10 callback runs first
```
**Rationale**:
- Critical systems (combat, safety checks) process first
- UI updates happen after game state changes
- Logging happens after all game logic
- Deterministic event processing order

### 6. **No Backward Compatibility**
**Decision**: "Breaking and fixing over making it compatible with previous and new systems"
**Approach**:
- Convert managers completely, not incrementally
- Remove old callback parameters entirely
- Force compilation errors until fixed properly
- No hybrid callback/event modes

**Rationale**:
- Clean architecture without legacy cruft
- Forces complete adoption of new patterns
- Prevents gradual degradation back to old patterns
- Simpler codebase without compatibility layers

### 7. **GameState as Single Source of Truth**
**Decision**: All persistent state lives in GameState; events coordinate behavior
**Pattern**:
```python
# State changes go through GameState
game_state.battle.current_turn += 1

# Coordination happens through events  
event_manager.publish(TurnStarted(turn=new_turn))
```
**Rationale**:
- Clear separation between state and behavior
- Events don't carry persistent state, just notifications
- GameState can be serialized/restored independently
- Event system is stateless and replayable

## Overview
This document tracks the migration from the legacy callback-based manager system to the new EventManager-based architecture. The goal is to eliminate ALL cross-dependencies between managers, with each manager only knowing about EventManager and GameState.

## Migration Status

### ✅ Completed Components

#### Core Infrastructure
- [x] **EventManager** (`src/core/event_manager.py`)
  - Publisher-subscriber pattern with priority queues
  - Event routing and debug logging
  - Immediate and queued event processing

- [x] **Event System** (`src/core/events.py`)
  - 25+ event types defined
  - Timeline, Combat, Input, UI, System events
  - Rich event payloads with context

#### Fully Migrated Managers
- [x] **TimelineManager** (`src/game/timeline_manager.py`)
  - Uses EventManager instead of log_manager
  - Emits timeline and turn events
  - No direct manager dependencies

- [x] **CombatManager** (`src/game/combat_manager.py`)
  - Uses EventManager for all events
  - Emits combat and targeting events
  - Clean separation from other managers

- [x] **InputHandler** (`src/game/input_handler.py`)
  - EventManager for movement and input events
  - No direct log_manager calls
  - Event-driven UI interactions

- [x] **UIManager** (`src/game/ui_manager.py`)
  - EventManager for UI state changes
  - Subscribes to relevant game events
  - No cross-manager dependencies

- [x] **LogManager** (`src/game/log_manager.py`)
  - Subscribes to all event types for logging
  - Updates GameState with log data
  - Centralized logging through events

#### Architecture Changes
- [x] **GameMap** (`src/game/map.py`)
  - Removed ALL event emission code
  - Pure data structure with no EventManager dependency
  - Managers emit events after map operations

- [x] **Game Orchestrator** (`src/game/game.py`)
  - Creates and wires EventManager
  - Passes EventManager to all managers
  - No more direct event callbacks

## 🚧 Remaining Migration Work

### Managers Still Using Callbacks

#### 1. **MoraleManager** (`src/game/morale_manager.py`)
- [ ] Replace `event_callback: Optional[Callable]` with `event_manager: EventManager`
- [ ] Update constructor signature to require EventManager
- [ ] Convert all `self.event_callback(event)` to `self.event_manager.publish(event)`
- [ ] Add event subscriptions in `_setup_event_subscriptions()`
- [ ] Subscribe to: `UnitTookDamage`, `UnitDefeated`, `BattlePhaseChanged`
- [ ] Remove log_manager parameter and dependencies
- [ ] Convert log calls to `LogMessage` event emissions

#### 2. **EscalationManager** (`src/game/escalation_manager.py`)
- [ ] Replace `event_callback: Optional[Callable]` with `event_manager: EventManager`
- [ ] Update constructor signature to require EventManager
- [ ] Convert all event callback calls to EventManager publishes
- [ ] Add event subscriptions for escalation triggers
- [ ] Subscribe to: `TurnStarted`, `UnitDefeated`, `ObjectiveCompleted`
- [ ] Emit new events: `ThreatLevelChanged`, `ReinforcementsArrived`, `EscalationTriggered`
- [ ] Remove any direct manager references

#### 3. **HazardManager** (`src/game/hazard_manager.py`)
- [ ] Add EventManager as required constructor parameter
- [ ] Remove any log_manager dependencies
- [ ] Convert hazard effects to events
- [ ] Create new events: `HazardCreated`, `HazardTriggered`, `HazardRemoved`, `HazardSpread`
- [ ] Subscribe to: `UnitMoved`, `TurnStarted`, `ExplosionOccurred`
- [ ] Emit events for hazard damage and effects

#### 4. **InterruptSystem** (`src/game/interrupt_system.py`)
- [ ] Add EventManager integration
- [ ] Create events: `InterruptPrepared`, `InterruptTriggered`, `InterruptExecuted`
- [ ] Subscribe to movement and attack events for trigger conditions
- [ ] Remove direct manager dependencies if any

#### 5. **AIController** (`src/game/ai_controller.py`)
- [ ] Add EventManager as required parameter
- [ ] Subscribe to: `EnemyTurnStarted`, `AIDecisionRequested`
- [ ] Emit: `AIDecisionMade`, `AIActionExecuted`
- [ ] Remove any direct manager calls

#### 6. **ObjectiveManager** (`src/game/objective_manager.py`)
- [ ] Verify EventManager integration is complete
- [ ] Ensure all objective checks use event subscriptions
- [ ] Remove any remaining direct manager queries

### New Events to Create

#### Combat Events
- [ ] `CombatForecastRequested` - Request damage prediction
- [ ] `CombatForecastReady` - Forecast calculation complete
- [ ] `CounterAttackTriggered` - Unit counterattacks
- [ ] `CriticalHitOccurred` - Critical strike landed

#### Morale Events  
- [ ] `MoraleCheckRequired` - Unit needs morale check
- [ ] `UnitRallied` - Unit recovered from panic
- [ ] `UnitRouted` - Unit fled battlefield
- [ ] `MoraleAuraApplied` - Leadership bonus applied

#### Hazard Events
- [ ] `HazardCreated` - New hazard placed on map
- [ ] `HazardTriggered` - Unit triggered hazard
- [ ] `HazardSpread` - Fire/poison spreads
- [ ] `HazardDamageDealt` - Hazard caused damage

#### AI Events
- [ ] `AITurnStarted` - AI begins processing
- [ ] `AIDecisionMade` - AI selected action
- [ ] `AITargetSelected` - AI chose target
- [ ] `AIMovementPlanned` - AI pathfinding complete

### Test Suite Updates

#### Unit Test Fixes Required
- [ ] Fix MockUnit objects in timeline tests (add `status` attribute)
- [ ] Update HazardManager test initialization with EventManager
- [ ] Fix HiddenIntentManager test initialization
- [ ] Update integration test fixtures for new signatures
- [ ] Add EventManager mock/spy for isolated unit tests
- [ ] Create event assertion helpers for testing

#### Integration Tests Needed
- [ ] Full battle flow with all managers using events
- [ ] Multi-manager coordination test scenarios
- [ ] Event ordering and priority tests
- [ ] Performance tests for event processing

### Code Cleanup

#### Remove Legacy Code
- [ ] Remove all `Optional[Callable]` event callbacks
- [ ] Remove all `log_manager` parameters
- [ ] Remove direct manager-to-manager imports
- [ ] Remove any remaining cross-dependencies
- [ ] Clean up unused callback wiring in Game class

#### Documentation Updates
- [ ] Update CLAUDE.md with event-driven architecture
- [ ] Document all event types and payloads
- [ ] Create event flow diagrams
- [ ] Update manager responsibility matrix
- [ ] Add EventManager usage examples

### Validation Checklist

#### Per-Manager Validation
For each manager, verify:
- [ ] Constructor requires EventManager (not optional)
- [ ] No imports of other managers
- [ ] All inter-manager communication via events
- [ ] Proper event subscriptions set up
- [ ] Events published with correct source attribution
- [ ] No direct log_manager calls
- [ ] Unit tests pass with EventManager

#### System-Wide Validation
- [ ] All managers can be instantiated independently
- [ ] Game orchestrator properly wires EventManager
- [ ] No circular dependencies exist
- [ ] Event flow is traceable and debuggable
- [ ] Performance acceptable with event overhead
- [ ] All tests pass

## Migration Priority Order

### Phase 1: Critical Path (High Priority)
1. **MoraleManager** - Core combat system component
2. **HazardManager** - Affects movement and combat
3. **EscalationManager** - Controls difficulty progression

### Phase 2: Game Flow (Medium Priority)
4. **AIController** - Enemy behavior system
5. **InterruptSystem** - Reaction system
6. **ObjectiveManager** - Victory conditions

### Phase 3: Cleanup (Low Priority)
7. Remove all legacy code
8. Update documentation
9. Performance optimization
10. Enhanced event debugging tools

## Success Criteria

The migration is complete when:
1. **Zero cross-dependencies** between managers
2. **All managers** use EventManager for communication
3. **No optional parameters** - EventManager is required everywhere
4. **All tests pass** with the new architecture
5. **No performance regression** from event overhead
6. **Documentation** fully updated

## Notes

- **Breaking Changes**: This migration intentionally breaks backward compatibility
- **No Hybrid Mode**: Managers should be fully converted, not partially
- **Event First**: When in doubt, use events over direct calls
- **Required Dependencies**: EventManager and GameState should never be optional