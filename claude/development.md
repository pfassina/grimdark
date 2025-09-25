# Development Workflow

## Development Commands

```bash
# ===== SIMPLE UNIT TESTING =====
# Run all unit tests (primary testing method)
python run_tests.py                  # Run all unit tests with verbose output
python run_tests.py --quiet          # Run tests with minimal output
python run_tests.py --test timeline  # Run specific test file (test_timeline.py)
python run_tests.py --lint           # Run code linting only
python run_tests.py --types          # Run type checking only  
python run_tests.py --all            # Run tests + linting + type checking
python run_tests.py --help           # Show all available options

# Or use pytest directly
nix develop --command pytest tests/                    # All unit tests
nix develop --command pytest tests/test_timeline.py    # Specific test file
nix develop --command pytest tests/ -v                 # Verbose output

# ===== INTERACTIVE PLAY =====
# Play interactive terminal version (uses default scenario) - NOTE: Requires interactive terminal
python main.py

# ===== DEVELOPMENT TOOLS =====
# Update Nix flake dependencies
nix flake update --update-input nixpkgs

# Code quality and linting
nix develop --command pyright .                    # Type checking and error detection
nix develop --command ruff check .                 # Code linting and style checking
nix develop --command ruff check . --fix           # Auto-fix linting issues where possible
nix develop --command ruff check . --select ARG    # Check for unused function/method parameters
```

## Development Environment

- This repository uses a Nix flake for development. You need to explicitly call it when running python scripts.
- Run commands with `nix develop` prefix for the development shell
- The development environment includes:
  - Python 3.11 with required packages (numpy, pandas, pyyaml)
  - **Pyright** for static type checking
  - **Ruff** for fast linting and code formatting
  - All development tools are pre-configured and ready to use

## Mandatory Development Workflow

### **Code Quality Enforcement (CRITICAL)**

**ZERO TOLERANCE POLICY**: Always complete any coding task by running both linting tools and fixing ALL diagnostic errors:

1. **Run pyright for type checking**:
   ```bash
   nix develop --command pyright .
   ```
   - Fix ALL type errors, undefined variables, and import issues
   - Use proper type annotations and Optional types
   - Resolve circular imports with TYPE_CHECKING pattern
   - Use ComponentType enum for type-safe component access
   - **No exceptions**: Every type error must be resolved

2. **Run ruff for linting and style**:
   ```bash
   nix develop --command ruff check . --fix  # Auto-fix what's possible
   nix develop --command ruff check .        # Check remaining issues
   nix develop --command ruff check . --select ARG  # Check for unused parameters
   ```
   - Fix unused imports, undefined variables, and style violations
   - Remove or properly use unused function/method parameters
   - Ensure proper import ordering and formatting
   - Address any remaining manual fixes needed

3. **Update unit tests**:
   ```bash
   python run_tests.py                       # Verify all tests pass
   python run_tests.py --all                 # Full validation
   ```
   - **Required**: Update unit tests for every code change
   - Add new tests for new functionality
   - Ensure existing tests still pass
   - Test event-driven interactions properly

4. **Update documentation**:
   - **Required**: Update CLAUDE.md and README.md when affecting system behavior or architecture
   - Document new event types and manager responsibilities
   - Update development patterns and workflows

**Never consider a task complete until pyright and ruff report zero errors AND tests pass AND documentation is updated.**

### **Best Practices Enforcement**

**Write Simple, Readable, Maintainable Code**:
- **Prefer early returns and guard clauses** over deep nesting
- **Avoid defensive programming** that obscures actual errors - let errors surface clearly
- **Keep functions focused** on single responsibilities
- **Use descriptive variable and function names**
- **Limit indentation levels** - prefer flat code structure

**Anti-Patterns to Avoid**:
- ❌ **Multiple levels of indentation**: Use early returns instead
- ❌ **Defensive try/catch blocks**: Let errors propagate with clear messages
- ❌ **Direct manager-to-manager dependencies**: Use EventManager only
- ❌ **Complex nested structures**: Break into smaller, focused functions
- ❌ **Optional EventManager parameters**: EventManager is always required

**Event-Driven Patterns to Follow**:
- ✅ **Emit events after state changes**: `self.event_manager.publish(UnitMoved(...))`
- ✅ **Subscribe to relevant events**: `self.event_manager.subscribe(EventType.UNIT_MOVED, self._handle_unit_moved)`
- ✅ **Include rich event payloads**: Provide full context in event data
- ✅ **Use event priorities**: Critical events (combat) before UI updates