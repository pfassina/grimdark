# Architecture

The system uses an **event-driven architecture** with timeline-based combat flow where game logic and rendering are completely separated:

- **Game logic** updates state and builds a `RenderContext` containing all renderable data
- **Renderers** receive the context and draw it using their own implementation
- **Communication** happens through EventManager for inter-system coordination
- **Timeline system** replaces traditional turn-based phases with fluid action-weight scheduling

## Core Architecture Principles

- **Event-Driven Communication**: All managers communicate through EventManager, never direct dependencies
- **Timeline-Based Combat**: Action weights determine when units act next, creating tactical depth through time management
- **Hybrid Component System**: ECS with type-safe Unit wrapper providing clean property access and component management
- **Push-Based Rendering**: Game builds render contexts, renderers display them independently
- **Single Source of Truth**: GameState holds all persistent data, EventManager coordinates behavior

## Timeline System

- **Priority Queue**: Units scheduled by execution time (current_time + speed + action_weight)
- **Action Categories**: Quick (50-80), Normal (100), Heavy (150-200+), Prepared (120-140) weight
- **Discrete Ticks**: Integer time values for deterministic, reproducible behavior
- **Mixed Turns**: Player and AI units intermixed based on timeline, not phases
- **Event Integration**: Timeline events trigger manager reactions through EventManager

## Event-Driven Communication

- **EventManager**: Central message bus replacing all direct manager dependencies
- **Publisher-Subscriber**: Managers emit events, subscribe to relevant events only
- **Loose Coupling**: Each manager only knows EventManager and GameState
- **Event Types**: Timeline, Combat, Input, UI, System events with rich payloads
- **Required Dependency**: EventManager is mandatory constructor parameter for all managers

## Core Components

1. **Core Layer** (`src/core/`) - **Organized into focused subpackages**
   - **Engine** (`src/core/engine/`)
     - `timeline.py` - Timeline queue and entry management for fluid turn order
     - `actions.py` - Action class hierarchy with weight categories and validation
     - `game_state.py` - Centralized state management
   - **Events** (`src/core/events/`)
     - `events.py` - Event definitions for inter-system communication
     - `event_manager.py` - Publisher-subscriber event routing and coordination
   - **Entities** (`src/core/entities/`)
     - `components.py` - Base Component and Entity classes for ECS system
     - `renderable.py` - Data classes for renderable entities (NO game logic)
   - **Data** (`src/core/data/`)
     - `data_structures.py` - Vector2 and VectorArray for efficient spatial operations
     - `game_enums.py` - Centralized enums for teams, unit classes, terrain types, and ComponentType for type-safe ECS
     - `game_info.py` - Static game data and lookup tables
   - **Other** (remaining in core root)
     - `renderer.py` - Abstract base class all renderers must implement
     - `input.py` - Generic input events (renderer-agnostic)
     - `wounds.py` - Wound types, severity, and healing mechanics **(WIP)**
     - `hazards.py` - Environmental hazard base classes and spreading effects **(WIP)**
     - `hidden_intent.py` - Information warfare and intent revelation system **(WIP)**

2. **Game Logic** (`src/game/`) - **Organized into focused subpackages**
   - **Core Game Files** (in `src/game/` root)
     - `game.py` - **Main orchestrator** that coordinates all manager systems through EventManager
     - `map.py` - Grid-based battlefield with vectorized operations, pathfinding, CSV map loading
     - `tile.py` - Tile data structures and terrain handling
     - `input_handler.py` - User input processing and action routing
     - `render_builder.py` - Render context construction from game state
   - **Managers** (`src/game/managers/`)
     - `timeline_manager.py` - Timeline processing, unit activation, and turn flow coordination
     - `combat_manager.py` - Combat targeting, validation, and UI integration
     - `morale_manager.py` - Morale calculations, panic state management **(WIP)**
     - `hazard_manager.py` - Environmental hazard processing and timeline integration **(WIP)**
     - `escalation_manager.py` - Time pressure through reinforcements **(WIP)**
     - `ui_manager.py` - Overlays, dialogs, banners, and modal UI state
     - `scenario_manager.py` - Scenario loading, map creation, and game state initialization
     - `selection_manager.py` - Cursor positioning and unit selection state management
     - `objective_manager.py` - Event-driven objective tracking
     - `phase_manager.py` - Game phase transitions and state management
     - `log_manager.py` - Logging and debug message handling
   - **Combat** (`src/game/combat/`)
     - `combat_resolver.py` - Damage application, wound generation, and combat execution
     - `battle_calculator.py` - Damage prediction and forecasting (read-only)
   - **AI** (`src/game/ai/`)
     - `ai_controller.py` - Timeline-aware AI with personality types and tactical assessment
     - `ai_behaviors.py` - AI behavior patterns and decision-making logic
   - **Entities** (`src/game/entities/`)
     - `unit.py` - Hybrid Unit wrapper with type-safe component access and clean property interface
     - `components.py` - Type-safe ECS components using ComponentType enum (Actor, Health, Movement, Combat, Morale, Wound, Interrupt)
     - `unit_templates.py` - Unit class definitions and base stats
     - `map_objects.py` - Interactive map objects and environmental elements
   - **Scenarios** (`src/game/scenarios/`)
     - `scenario_loader.py` - YAML scenario parsing and game state initialization
     - `scenario.py` - Scenario data structures and validation
     - `scenario_structures.py` - Data classes for scenario definitions
     - `scenario_menu.py` - Scenario selection interface
     - `objectives.py` - Victory/defeat condition implementations
   - **Systems** (`src/game/systems/`)
     - `interrupt_system.py` - Prepared actions and reaction system **(WIP)**

3. **Renderers** (`src/renderers/`)
   - Each renderer independently decides HOW to display the render context
   - Terminal renderer uses ASCII characters
   - New renderers (pygame, web, etc.) can be added without touching game code

## Manager System Design

The `Game` class acts as a **lean coordinator** that:
1. **Initializes** all manager systems with EventManager and GameState dependencies
2. **Coordinates** communication between managers through EventManager
3. **Orchestrates** the main game loop and high-level state management
4. **Delegates** all specific concerns to specialized managers

### Core Manager Responsibilities

- **ScenarioManager**: Scenario loading, map creation, unit placement, and objective system initialization
- **SelectionManager**: Cursor positioning, unit selection state, and selection validation
- **TimelineManager**: Timeline processing, unit activation, turn flow, and AI coordination
- **CombatManager**: Combat targeting, validation, UI integration, and action execution
- **UIManager**: Modal overlays, dialogs, banners, and UI state management
- **InputHandler**: User input processing, action routing, and input context management

### Manager Communication Flow
```
All Managers → EventManager ← All Managers
     ↓               ↓             ↑
GameState       Event Routing   Event Subscriptions
(shared data)   (coordination)  (reactive behavior)
```

### Key Architectural Benefits
1. **Single Responsibility**: Each manager handles exactly one major concern
2. **Testability**: Managers can be unit tested in isolation with EventManager mocks
3. **Maintainability**: Easy to locate and modify specific functionality
4. **Extensibility**: New managers can be added without touching existing code
5. **Event Traceability**: All communication is traceable through event emissions

## Timeline-Based Development Patterns

### **Adding New Actions**

1. **Create Action Class** in `src/core/actions.py`:
   ```python
   class NewAction(Action):
       category = ActionCategory.NORMAL
       base_weight = 100
       
       def validate(self, unit, target, game_map) -> ActionValidation:
           # Validation logic
           
       def execute(self, unit, target, game_map) -> ActionResult:
           # Execution logic
           # Emit events for side effects
   ```

2. **Consider Action Weight**: 
   - Quick (50-80): Fast, weak actions
   - Normal (100): Standard balanced actions
   - Heavy (150-200+): Slow, powerful actions
   - Prepared (120-140): Set up interrupts/reactions

3. **Emit Appropriate Events**: Actions should emit events for state changes

### **Working with Timeline System**

- **Timeline Scheduling**: Units added at `current_time + action_weight`
- **Event Integration**: Timeline events trigger through EventManager
- **Mixed Turn Order**: Player and AI units intermixed based on execution time
- **Discrete Ticks**: Use integer time values for deterministic behavior

### **Component-Based Development**

The game uses a hybrid Entity-Component System with a clean Unit wrapper for type-safe access:

#### **Component Architecture**
- **ComponentType Enum**: Type-safe component identification replacing string-based access
- **Entity + Components**: Core ECS with Actor, Health, Movement, Combat, Status components
- **Unit Wrapper**: High-level interface providing both direct properties and component access
- **Optional Components**: Morale, Wound, Interrupt, AI components for extended functionality

#### **Unit Access Patterns**
```python
# Direct property access (most frequent operations)
unit.x = 5                    # Position access
unit.hp_current = 20          # Health access
if unit.is_alive and unit.can_move:  # Status checks
    # Perform action

# Component access (less frequent operations)
unit.combat.strength = 10     # Combat stats
unit.health.hp_max = 25       # Health configuration
unit.actor.unit_class         # Unit classification
unit.morale.modify_morale(-5, "fear")  # Optional components
```

#### **Component Management**
```python
# Adding optional components dynamically
morale_comp = MoraleComponent(unit.entity)
unit.add_component(morale_comp)

# Type-safe component checking
if unit.has_component(ComponentType.MORALE):
    unit.morale.modify_morale(5, "victory")

# Component removal
unit.remove_component(ComponentType.WOUND)
```

#### **Key Components**
- **Actor Component**: Identity, team affiliation, unit class information
- **Health Component**: HP management, life/death state, damage tracking
- **Movement Component**: Position, facing, movement points, mobility
- **Combat Component**: Attack/defense stats, damage calculation, range validation
- **Status Component**: Turn state, action availability, temporary effects
- **Morale Component**: Psychological state affecting combat effectiveness (optional)
- **Wound Component**: Persistent injuries affecting unit performance (optional)
- **Interrupt Component**: Prepared actions and reaction capabilities (optional)
- **AI Component**: Behavior patterns and decision-making logic (optional)

### **Action Validation System**

The game uses a unified validation system through Action classes for consistent behavior:

#### **Validation Architecture**
- **Single Validation Path**: All attack/action validation goes through Action classes, not component methods
- **Action.validate()**: Returns ActionValidation with detailed validation results
- **Consistent Logic**: Same validation used by both player input and AI decision-making
- **Type Safety**: Actions use Unit objects directly, not Entity references

#### **Validation Examples**
```python
# AI decision making (unified with player actions)
attack_action = StandardAttack()
validation = attack_action.validate(unit, game_map, target_position)
if validation.is_valid:
    # Execute attack
    result = attack_action.execute(unit, target_position, game_map)

# Component separation of concerns
# ❌ Old approach: unit.combat.can_attack(target) - mixed health/status checks
# ✅ New approach: Action handles all validation logic consistently
```

#### **Component Responsibilities**
- **Components**: Manage their own state and properties only
- **Actions**: Handle complex validation logic and cross-component coordination
- **Unit Class**: Provides convenient property access and basic status queries
- **Managers**: Use Action validation for consistent behavior across systems

### **Manager Integration**

When creating new managers:
1. **Require EventManager**: Always mandatory constructor parameter
2. **Subscribe to Events**: Set up event subscriptions in `_setup_event_subscriptions()`
3. **Emit State Changes**: Publish events after modifying GameState
4. **Single Responsibility**: Each manager handles one major concern
5. **Unit Testing**: Design for isolation with EventManager mocks