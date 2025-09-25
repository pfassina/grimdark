# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grimdark SRPG is a timeline-based Strategy RPG built in Python with event-driven architecture and renderer-agnostic design. The codebase demonstrates complete separation between game logic and rendering through a timeline-based combat system where tactical depth comes from time management.

**⚠️ ACTIVE DEVELOPMENT**: This project is under active development. Breaking changes are expected and backward compatibility is NOT maintained. Feel free to refactor, redesign, or enhance any part of the codebase as needed, as long as it doesn't violate the core architectural principles and design premises outlined below.

## Documentation Modules

### When to Reference Each Module

**@claude/development.md** - Reference when:
- Running development commands (testing, linting, type checking)
- Setting up the Nix development environment
- Following code quality enforcement workflows
- Fixing pyright or ruff errors
- Understanding best practices and anti-patterns

**@claude/architecture.md** - Reference when:
- Understanding the event-driven system design
- Working with the Timeline system or adding Actions
- Creating or modifying Managers
- Working with Components and the ECS system
- Understanding communication flow between systems
- Implementing event publishers/subscribers

**@claude/testing.md** - Reference when:
- Writing unit tests for new functionality
- Running test suites (run_tests.py)
- Understanding test structure and organization
- Following event-driven testing patterns
- Checking test coverage requirements

**@claude/code-style.md** - Reference when:
- Writing or reviewing code
- Understanding type hint conventions (Python 3.9+)
- Following code formatting guidelines
- Updating documentation

**@claude/assets.md** - Reference when:
- Creating or modifying scenarios
- Working with map files (CSV layers)
- Understanding the scenario-first design
- Configuring terrain in tileset.yaml
- Working with markers, regions, and placements

**@claude/features.md** - Reference when:
- Adding new game features
- Creating new Manager systems
- Implementing new Renderers
- Extending the combat system
- Creating scenarios or maps

@claude/development.md
@claude/architecture.md  
@claude/testing.md
@claude/code-style.md
@claude/assets.md
@claude/features.md

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
