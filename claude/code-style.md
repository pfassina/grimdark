# Code Style

This project follows modern Python conventions. When writing or modifying code:

## Type Hints
- **Use built-in type conventions** (Python 3.9+):
  - `dict[str, Any]` instead of `Dict[str, Any]`
  - `list[str]` instead of `List[str]`
  - `tuple[int, int]` instead of `Tuple[int, int]`
  - `set[str]` instead of `Set[str]`
- Only import from `typing` module for advanced types like `Optional`, `Union`, `TYPE_CHECKING`, etc.
- Always include type hints for function parameters and return values
- Use `Optional[Type]` for nullable values instead of `Union[Type, None]`

## General Style
- Follow PEP 8 conventions for naming and formatting
- Use descriptive variable and function names
- Add docstrings for public methods and classes
- Keep functions focused on single responsibilities
- Prefer composition over inheritance where appropriate
- **Avoid deep nesting**: Use early returns and guard clauses
- **Keep code flat**: Prefer simple, linear flow over complex nested structures

## Code Quality Tools
- **Pyright**: Static type checker for comprehensive type analysis
- **Ruff**: Fast Python linter for code style and quality issues
- Both tools are included in the Nix development environment
- Use `TYPE_CHECKING` imports to resolve circular dependency issues

## Documentation Guidelines

**Maintain Documentation**: Always update CLAUDE.md and README.md when making code changes that affect system behavior or architecture.

- **Update after changes**: When refactoring, adding features, or changing APIs, update relevant documentation
- **Keep it practical**: Focus on how the system works, not marketing language or aspirations
- **Be objective**: Document actual implementation and behavior, avoid verbose descriptions
- **Explain usage**: Include practical examples and workflow guidance for developers

Documentation should help developers understand and work with the system effectively.