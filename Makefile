# Grimdark SRPG Makefile
# Provides convenient shortcuts for common development tasks

.PHONY: help test test-quick test-all test-unit test-integration test-performance
.PHONY: quality lint typecheck fix-lint demo clean install-dev
.PHONY: ci coverage docs

# Default target
help:
	@echo "Grimdark SRPG Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run quick tests (default)"
	@echo "  test-quick    - Run unit tests only (fast)"
	@echo "  test-all      - Run all tests with coverage"
	@echo "  test-unit     - Run unit tests"
	@echo "  test-integration - Run integration tests"
	@echo "  test-performance - Run performance benchmarks"
	@echo ""
	@echo "Code Quality:"
	@echo "  quality       - Run all quality checks"
	@echo "  lint          - Run ruff linting"
	@echo "  typecheck     - Run pyright type checking"
	@echo "  fix-lint      - Auto-fix linting issues"
	@echo ""
	@echo "Development:"
	@echo "  demo          - Run game demo"
	@echo "  ci            - Run full CI pipeline"
	@echo "  coverage      - Generate coverage report"
	@echo "  clean         - Clean build artifacts"
	@echo ""
	@echo "All commands use the Nix development environment automatically."

# Testing targets
test: test-quick

test-quick:
	@echo "Running quick tests..."
	python run_tests.py --quick

test-all:
	@echo "Running all tests with coverage..."
	python run_tests.py --all

test-unit:
	@echo "Running unit tests..."
	python run_tests.py --unit

test-integration:
	@echo "Running integration tests..."
	python run_tests.py --integration

test-performance:
	@echo "Running performance benchmarks..."
	python run_tests.py --performance

# Code quality targets
quality:
	@echo "Running code quality checks..."
	python run_tests.py --quality

lint:
	@echo "Running ruff linting..."
	nix develop --command ruff check .

typecheck:
	@echo "Running pyright type checking..."
	nix develop --command pyright .

fix-lint:
	@echo "Auto-fixing linting issues..."
	nix develop --command ruff check . --fix

# Development targets
demo:
	@echo "Running game demo..."
	python run_tests.py --demo

ci:
	@echo "Running full CI pipeline..."
	python run_tests.py --ci

coverage:
	@echo "Generating coverage report..."
	nix develop --command pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/"

# Cleanup
clean:
	@echo "Cleaning build artifacts..."
	rm -rf __pycache__ .pytest_cache .coverage htmlcov/ .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true

# Development environment setup
install-dev:
	@echo "Setting up development environment..."
	@echo "This project uses Nix flakes for dependency management."
	@echo "Run 'nix develop' to enter the development shell."
	@echo "Or use any of the make targets which will automatically use the Nix environment."

# Documentation (placeholder for future)
docs:
	@echo "Documentation generation not yet implemented."
	@echo "See README.md and CLAUDE.md for current documentation."