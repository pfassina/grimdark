# Grimdark SRPG - Comprehensive Turn Flow

## Overview
The Grimdark SRPG uses a **timeline-based combat system** where units act based on action weights and speed rather than traditional turn-based rounds.
The system features:

- **Timeline Queue**: Priority queue ordering units by execution time
- **Action Weights**: Actions have time costs affecting next turn timing
- **Event-Driven Phases**: Phase transitions triggered by game events
- **Interrupt System**: Prepared actions that trigger on conditions

## Core Systems

### Timeline System
- **Timeline Queue**: Min-heap priority queue ordered by execution time
- **Action Scheduling**: `next_time = current_time + unit_speed + action_weight`
- **Entity Types**: Units, hazards, and events all share the timeline

### Phase Management
- **GamePhase**: Overall game states (MAIN_MENU → BATTLE → GAME_OVER)
- **BattlePhase**: Combat sub-phases managed by event-driven state machine
- **Phase Transitions**: Event-based rules trigger automatic transitions

## Turn Flow Diagrams

### Main Game Loop

```mermaid
flowchart TD
  Start([Game start]) --> MainMenu[Main menu]
  MainMenu --> LoadScenario[Load scenario]
  LoadScenario --> InitBattle[Init battle data]
  InitBattle --> InitTimeline[Init timeline heap]
  InitTimeline --> Loop{Timeline has entries?}

  %% Empty timeline handling
  Loop -->|No| BattleOver{Battle over?}
  BattleOver -->|Yes| GameOver([Game over])
  BattleOver -->|No| ErrEmpty[Raise EmptyTimelineError]

  %% Non-empty: dispatch by type
  Loop -->|Yes| Peek[Peek next entry]
  Peek --> Type{Entry type?}
  Type -->|Hazard| DoHaz[Process hazard] --> Loop
  Type -->|Event| DoEvt[Process event] --> Loop

  %% Unit path with strict checks
  Type -->|Unit| Alive{Unit alive?}
  Alive -->|No| ErrDead[Raise DeadUnitOnTimelineError]
  Alive -->|Yes| HasSched{Has scheduled action?}
  HasSched -->|Yes| ExecSched[Execute scheduled action] --> Resched[Reschedule with weight] --> Loop

  %% BeginTurn hands control to Battle Phases
  HasSched -->|No| BeginTurn[Begin turn<br/>emit TurnStarted] --> Phases([Battle phases state machine])
  Phases --> Loop
```

### Timeline Processing

```mermaid
flowchart TD
    TL([Timeline processing]) --> HasEntries{Timeline has entries?}

    %% Empty timeline branch
    HasEntries -->|No| BattleOver{Battle over?}
    BattleOver -->|Yes| Done([Game Over])
    BattleOver -->|No| ErrEmpty[Raise EmptyTimelineError]

    %% Non-empty timeline branch
    HasEntries -->|Yes| Peek["Peek next entry"]
    Peek --> Type{Entity type?}

    %% Hazard/Event
    Type -->|Hazard| DoHaz["Process hazard"] --> Next([Next timeline step])
    Type -->|Event| DoEvt["Process event"] --> Next

    %% Unit path with strict checks
    Type -->|Unit| Alive{Unit alive?}
    Alive -->|No| ErrDead[Raise DeadUnitOnTimelineError]
    Alive -->|Yes| HasSched{Has scheduled action?}
    HasSched -->|Yes| ExecSched["Execute scheduled action"] --> Resched["Reschedule with weight"] --> Next
    HasSched -->|No| BeginTurn["Begin unit turn"] --> Next

    %% Loop
    Next --> TL
```

### Player Turn Flow

```mermaid
flowchart TD
    PlayerTurn([Player Turn Start]) --> EmitStart["Emit 'TurnStarted'"]
    EmitStart --> SetUnit["Set acting unit & reset flags"]
    SetUnit --> MovePhase["Enter 'UNIT_MOVING' phase<br/>show reachable tiles"]

    %% Movement input (free movement)
    MovePhase --> MoveIn{Player input}
    MoveIn -->|Arrow keys| PreviewTile["Preview move to tile"]
    PreviewTile --> MoveIn

    %% Quick shortcuts from movement phase
    MovePhase --> WQuick["Press W → Quick Wait"]
    WQuick --> EndTurn["End unit turn"]

    MovePhase --> AQuick["Press A → Quick Attack"]
    AQuick --> TargetPhase["Enter 'ACTION_TARGETING' phase<br/>'Attack' preselected"]

    %% Confirm or cancel movement
    MoveIn -->|Enter| ConfirmMove{"Valid tile?"}
    ConfirmMove -->|Yes| DoMove["Move unit"]
    ConfirmMove -->|No| MoveIn

    %% Cancel from movement phase (has moved but not confirmed)
    MoveIn -->|X| CancelMove1["Cancel → return to original tile"]
    CancelMove1 --> MovePhase

    %% After confirmed movement
    DoMove --> EmitMoved["Emit 'UnitMoved'"]
    EmitMoved --> ActSel["Enter 'ACTION_SELECTION' phase"]
    ActSel --> MenuInput{Action menu}
    MenuInput -->|Wait| EndTurn
    MenuInput -->|Attack| TargetPhase
    MenuInput -->|X| CancelMove2["Cancel → revert to original tile<br/>return to 'UNIT_MOVING'"]
    CancelMove2 --> MovePhase

    %% Targeting phase
    TargetPhase --> TargetInput{Target input}
    TargetInput -->|Arrow keys| TargetPreview["Update target preview<br/>show forecast"]
    TargetPreview --> TargetInput
    TargetInput -->|X| CancelTarget["Cancel → back to 'ACTION_SELECTION'"]
    CancelTarget --> ActSel

    TargetInput -->|Enter| ValidateTarget{"Valid target?"}
    ValidateTarget -->|No| TargetInput

    %% Friendly fire confirmation
    ValidateTarget -->|Yes| FFCheck{"Friendly in target/AOE?"}
    FFCheck -->|No| ResolveAttack["Resolve attack"]
    FFCheck -->|Yes| FFPrompt["Confirm friendly fire?"]
    FFPrompt -->|Confirm| ResolveAttack
    FFPrompt -->|Cancel| ActSel

    %% End turn & timeline
    ResolveAttack --> EndTurn
    EndTurn --> PopEntry["Pop timeline entry"]
    PopEntry --> Resched["Reschedule with action weight"]
    Resched --> EmitEnd["Emit 'TurnEnded'"]
    EmitEnd --> ReturnTL(["Return to timeline"])
```

## System Architecture & Event Flow

### Core Architecture Principles

1. **Event-Driven Communication**: Systems communicate through events, not direct dependencies
2. **Timeline-Based Flow**: Units act on a priority queue based on speed and action weights
3. **Pull-Based Rendering**: Renderer pulls data each frame, doesn't listen to events
4. **Single Source of Truth**: GameState holds authoritative data, managers orchestrate behavior

### System Responsibilities

**TimelineManager**
- **Owns**: Timeline queue, unit scheduling, activation flow
- **Drives**: Main game progression, unit activation sequence
- **Emits**: Timeline and unit activation events
- **Listens**: Unit defeated events (for cleanup)

**EventManager**
- **Owns**: Event queue, subscriber registry, event routing
- **Drives**: Inter-system communication
- **Pattern**: Central message bus with priority queuing

**PhaseManager**
- **Owns**: Battle phase state machine
- **Drives**: Phase transitions based on events
- **Listens**: All game events that trigger phase changes

**UIManager**  
- **Owns**: Overlays, banners, dialogs, modal UI state
- **Drives**: UI element lifecycle
- **Listens**: Phase changes for automatic UI updates
- **Pattern**: Reactive to game state, doesn't drive game flow

**RenderBuilder**
- **Owns**: Render context construction
- **Drives**: Nothing (pure data transformation)
- **Pattern**: Pulls from GameState and managers each frame
- **No event subscriptions**: Stateless transformation layer

**InputHandler**
- **Owns**: User input processing, input-to-action mapping
- **Drives**: Player actions through event emission
- **Emits**: Action events based on user input

**CombatManager**
- **Owns**: Combat orchestration, targeting validation
- **Drives**: Combat resolution flow
- **Listens**: Combat-related events

### Data Flow Patterns

```
USER INPUT → InputHandler → Events → PhaseManager → State Changes
                              ↓
                         EventManager
                              ↓
                    All System Subscribers
                              
RENDERING:  GameState → RenderBuilder → RenderContext → Renderer
            (pulled each frame, not event-driven)

TIMELINE:   TimelineManager → Unit Activation → Events → Systems React
```

### Key Invariants

1. **Timeline Consistency**: Dead units never exist in timeline
2. **Phase Coherence**: Only one battle phase active at a time
3. **Event Ordering**: Events processed by priority, then timestamp
4. **Render Independence**: Rendering never modifies game state
5. **Manager Isolation**: Managers communicate only through events

### Decision Points & Ownership

| Decision | Owner | Triggers |
|----------|-------|----------|
| Unit activation order | TimelineManager | Timeline queue state |
| Phase transitions | PhaseManager | Game events |
| UI element visibility | UIManager | Phase changes |
| Combat resolution | CombatManager | Attack actions |
| Victory/defeat | ObjectiveManager | Game state conditions |
| Render frame content | RenderBuilder | Frame tick (pull) |

### Common Patterns

**Adding a New Feature**:
1. Identify owning manager (or create new one)
2. Define events for state changes
3. Subscribe relevant systems to events
4. Ensure render builder can visualize state

**Debugging Flow Issues**:
1. Check event history in EventManager
2. Verify phase transitions in PhaseManager
3. Confirm timeline consistency in TimelineManager
4. Validate UI state in UIManager

**System Communication**:
- **Loosely Coupled**: Use events for non-critical updates
- **Direct Calls**: Only for initialization and tightly coupled operations
- **State Queries**: Pull from GameState, never push
