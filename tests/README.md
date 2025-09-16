# Grimdark SRPG Test Suite

This directory contains a comprehensive test suite for the Grimdark SRPG game engine, built with pytest and following modern Python testing best practices.

## Overview

The test suite is organized into several categories:

- **Unit Tests** (`unit/`): Test individual components in isolation
- **Integration Tests** (`integration/`): Test system interactions and workflows  
- **Performance Tests** (`performance/`): Benchmark critical game systems
- **Edge Cases** (`edge_cases/`): Test boundary conditions and error handling
- **Legacy Tests** (root level): Original validation scripts maintained for compatibility

## Quick Start

```bash
# Run quick tests (recommended for development)
python run_tests.py --quick

# Run all tests with coverage
python run_tests.py --all

# Run specific test categories
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --performance

# Run code quality checks
python run_tests.py --quality

# Full CI pipeline
python run_tests.py --ci
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation using mocks and fixtures:

- **Core Systems**: Data structures, game state, events, enums
- **Manager Systems**: Combat, input handling, UI management  
- **Game Logic**: Maps, units, pathfinding, combat resolution

Key files:
- `test_data_structures.py` - Vector2, VectorArray operations
- `test_game_state.py` - Game state management and transitions
- `test_combat_manager.py` - Combat targeting and coordination
- `test_game_map.py` - Map operations and pathfinding
- `test_unit.py` - Unit stats and behavior

### Integration Tests (`tests/integration/`)

Test system interactions and complete workflows:

- **Combat Integration**: Full combat flows from targeting to resolution
- **Game System Integration**: Manager coordination and game loops
- **Input Handling**: Input processing through complete game systems

Key files:
- `test_combat_integration.py` - End-to-end combat scenarios
- `test_game_system_integration.py` - Full system coordination

### Performance Tests (`tests/performance/`)

Benchmark critical systems and detect performance regressions:

- **Pathfinding Performance**: Movement and attack range calculations
- **Combat Performance**: Single and mass combat resolution
- **Rendering Performance**: Context generation and scaling
- **Data Structure Performance**: Core operations benchmarking

Key files:
- `test_benchmarks.py` - Comprehensive performance test suite

### Edge Cases (`tests/edge_cases/`)

Test boundary conditions, error handling, and graceful degradation:

- **Boundary Conditions**: Map edges, extreme coordinates, size limits
- **Error Handling**: Invalid inputs, null values, state corruption
- **Resource Limits**: Memory usage, maximum units, large datasets

Key files:
- `test_error_handling.py` - Comprehensive edge case testing

## Test Infrastructure

### Fixtures and Utilities (`conftest.py`, `test_utils.py`)

Shared testing infrastructure provides:

- **Pre-configured test objects**: Maps, units, scenarios
- **Mock factories**: Renderers, event emitters, managers
- **Test builders**: Flexible object creation with sensible defaults
- **Assertion helpers**: Common validation patterns
- **Test constants**: Shared values and thresholds

### Test Configuration (`pytest.ini`)

Pytest configuration includes:

- Coverage reporting with HTML output
- Test markers for categorization
- Strict configuration and error handling
- Performance benchmarking integration

## Running Tests

### Using the Test Runner (Recommended)

The `run_tests.py` script provides convenient access to all test categories:

```bash
# Quick development testing
python run_tests.py --quick

# Comprehensive testing
python run_tests.py --all

# Specific categories
python run_tests.py --unit
python run_tests.py --integration  
python run_tests.py --performance

# Code quality
python run_tests.py --quality

# Legacy compatibility
python run_tests.py --legacy

# Full CI pipeline
python run_tests.py --ci
```

### Using Pytest Directly

For more control, use pytest directly:

```bash
# All tests
nix develop --command pytest tests/

# Specific directories
nix develop --command pytest tests/unit/
nix develop --command pytest tests/integration/

# With coverage
nix develop --command pytest tests/ --cov=src --cov-report=html

# Specific markers
nix develop --command pytest -m unit
nix develop --command pytest -m integration
nix develop --command pytest -m performance

# Benchmarks only
nix develop --command pytest tests/performance/ --benchmark-only

# Verbose output
nix develop --command pytest tests/ -v --tb=short
```

### Using Make (Alternative)

Convenient make targets are available:

```bash
make test          # Quick tests
make test-all      # All tests with coverage
make test-unit     # Unit tests only
make quality       # Code quality checks
make ci           # Full CI pipeline
```

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.architecture` - Architecture validation

Use markers to run specific test subsets:

```bash
pytest -m "unit and not slow"      # Fast unit tests
pytest -m "integration or performance"  # System tests
pytest -m "not performance"       # Skip benchmarks
```

## Coverage Reporting

The test suite includes comprehensive coverage reporting:

```bash
# Generate coverage report
python run_tests.py --all

# View HTML report
open htmlcov/index.html
```

Coverage targets:
- **Minimum**: 80% overall coverage
- **Goal**: 90%+ for core game logic
- **Critical paths**: 100% for safety-critical systems

## Performance Benchmarking

Performance tests use pytest-benchmark for:

- **Regression detection**: Alert on performance degradation
- **Optimization validation**: Verify improvements
- **Baseline establishment**: Track performance over time
- **Scaling analysis**: Test with various load conditions

Key metrics tracked:
- Pathfinding calculation time
- Combat resolution throughput  
- Rendering context generation speed
- Memory usage patterns

## Adding New Tests

### Unit Tests

1. Create test file in appropriate `tests/unit/` subdirectory
2. Use existing fixtures from `conftest.py`
3. Follow naming convention: `test_<component>.py`
4. Include docstrings and mark with `@pytest.mark.unit`

### Integration Tests

1. Create test file in `tests/integration/`
2. Mark with `@pytest.mark.integration`
3. Focus on system interactions, not individual components
4. Use realistic scenarios and data

### Performance Tests

1. Add benchmarks to `tests/performance/test_benchmarks.py`
2. Mark with `@pytest.mark.performance`
3. Use pytest-benchmark fixtures
4. Include regression thresholds

### Edge Cases

1. Add to `tests/edge_cases/test_error_handling.py`
2. Test boundary conditions and error paths
3. Verify graceful degradation
4. Include recovery validation

## Best Practices

### Test Structure

- **Arrange-Act-Assert**: Clear test structure
- **Single responsibility**: One concept per test
- **Descriptive names**: Clear test purpose
- **Isolated tests**: No dependencies between tests

### Fixtures and Mocking

- **Reuse fixtures**: Leverage shared test infrastructure
- **Mock external dependencies**: Isolate units under test
- **Realistic data**: Use representative test scenarios
- **Clean boundaries**: Clear separation between test and production code

### Performance Testing

- **Representative workloads**: Test realistic scenarios
- **Multiple iterations**: Account for variance
- **Baseline establishment**: Track changes over time
- **Resource monitoring**: Memory and CPU usage

### Maintenance

- **Update with code changes**: Keep tests synchronized
- **Regular review**: Remove outdated or redundant tests
- **Documentation**: Maintain test purpose and expectations
- **Continuous improvement**: Refactor and optimize test suite

## Troubleshooting

### Common Issues

**Tests fail with import errors**:
- Ensure you're running in Nix development environment: `nix develop`
- Check Python path includes project root

**Performance tests inconsistent**:
- Run on dedicated hardware when possible
- Account for system load and background processes
- Use multiple iterations and statistical analysis

**Coverage gaps**:
- Review uncovered code paths
- Add tests for error conditions and edge cases
- Consider integration testing for complex workflows

**Slow test runs**:
- Use `--quick` for development
- Mark slow tests with `@pytest.mark.slow`
- Optimize fixtures and test data

### Getting Help

1. Check test output and error messages
2. Review existing similar tests for patterns
3. Use pytest's `-v` flag for detailed output
4. Run individual test files to isolate issues
5. Check `conftest.py` for available fixtures

## Continuous Integration

The test suite integrates with GitHub Actions for:

- **Automated testing**: All PRs and pushes
- **Code quality**: Linting and type checking
- **Performance monitoring**: Benchmark tracking
- **Coverage reporting**: Codecov integration
- **Security scanning**: Dependency and code analysis

See `.github/workflows/ci.yml` for CI configuration.