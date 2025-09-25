# Testing

## Testing Workflow for Claude Code

**IMPORTANT**: `main.py` uses `TerminalRenderer` which requires an interactive terminal that Claude Code cannot access. For testing during development, use the unit test suite:

### Simple Unit Testing (Recommended)

The project uses a streamlined unit testing approach focused on the timeline-based architecture:

1. **Default Testing**: `python run_tests.py`
   - Runs all unit tests with verbose output
   - Tests core systems: Timeline, EventManager, Data Structures, Components, Managers
   - Perfect for development validation

2. **Specific Tests**: `python run_tests.py --test <name>`
   - Run individual test files (e.g., `--test timeline` for test_timeline.py)
   - Useful for focused development on specific systems

3. **Code Quality**: `python run_tests.py --all`
   - Unit tests + linting (ruff) + type checking (pyright)
   - Ensures both functionality and code quality

### Test Structure - **Mirrors the package hierarchy**

- **Core Tests** (`tests/core/`) - **Foundation systems with comprehensive coverage**
  - `tests/core/engine/test_timeline.py`: Core Timeline system tests
  - `tests/core/engine/test_actions.py`: Complete action hierarchy, validation, execution (56 tests)
  - `tests/core/events/test_event_manager.py`: Event Manager and communication tests
  - `tests/core/data/test_data_structures.py`: Vector2, GameState, and core data tests
- **Game Tests** (`tests/game/`) - **Game logic systems with extensive coverage**
  - `tests/game/test_game.py`: Game orchestrator, manager coordination, lifecycle (20 tests)
  - `tests/game/entities/test_components.py`: Unit components and ECS system tests
  - `tests/game/managers/test_managers.py`: Manager systems and integration tests
  - `tests/game/combat/test_combat_resolver.py`: Combat execution, damage, wounds (23 tests)
  - `tests/game/combat/test_battle_calculator.py`: Damage prediction, forecasting (30 tests)
- **Test Utilities**
  - `tests/conftest.py`: Basic fixtures and test utilities

**Note**: Test structure mirrors the source code package organization for easier navigation and maintenance. **Recent expansion added 129 new tests** covering critical systems previously untested.

### Testing New Features

When implementing new features:

1. **Write unit tests** in the appropriate test file or create a new one
2. **Update fixtures** in `tests/conftest.py` if needed for reusable test components  
3. **Run tests** with `python run_tests.py` to validate functionality
4. **Check code quality** with `python run_tests.py --all`

### Test Design Principles

- **Focus on unit testing**: Test individual components and systems in isolation
- **Mock external dependencies**: Use mocks for complex dependencies to keep tests fast and focused
- **Test the timeline architecture**: Emphasize testing the new timeline and event-driven systems
- **Simple and maintainable**: Keep tests straightforward and easy to understand
- **Type safety compliance**: All tests must pass pyright type checking with 0 errors
- **Mock unit compatibility**: Use `# type: ignore[arg-type]` for MockUnit parameters when needed
- **Comprehensive coverage**: New major systems require 85%+ test coverage before merge

## Test Coverage

The comprehensive test suite validates different aspects with **extensive coverage** of critical systems:

### Current Test Coverage (238+ tests)
- **Core Engine Tests** (84+ tests) - Foundation systems
  - **Actions System** (56 tests) - Complete action hierarchy, validation, execution, timeline integration
  - **Timeline System** (14 tests) - Priority queue, scheduling, time management
  - **Event System** (14+ tests) - Publisher-subscriber communication patterns
- **Game Logic Tests** (154+ tests) - Core gameplay systems  
  - **Game Orchestrator** (20 tests) - Manager coordination, initialization, lifecycle
  - **Combat Systems** (53 tests) - Battle execution, damage calculation, forecasting
  - **Component System** (30+ tests) - ECS architecture, unit management
  - **Manager Systems** (51+ tests) - Individual manager functionality in isolation

### Critical Systems Coverage
- ✅ **Actions System**: ~95% coverage - All action types, validation, execution
- ✅ **Game Orchestrator**: ~90% coverage - Manager wiring, event coordination
- ✅ **Combat Systems**: ~85% coverage - Damage resolution, battle forecasting
- ✅ **Timeline System**: ~90% coverage - Priority scheduling, turn management
- ✅ **Event System**: ~85% coverage - Publisher-subscriber patterns

### Testing Requirements
When adding features:
- **Update unit tests** for every code change (mandatory)
- Write comprehensive unit tests for new functionality
- Add integration tests for multi-system features
- Test event-driven interactions properly
- Verify game logic works without any renderer (testability principle)
- Include performance benchmarks for computationally intensive features

### Event-Driven Testing Patterns
- Mock EventManager for isolated unit tests
- Test event emission and subscription patterns
- Verify event payloads contain required data
- Test event ordering and priority handling
- Use type ignore comments for MockUnit compatibility: `# type: ignore[arg-type]`