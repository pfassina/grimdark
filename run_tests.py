#!/usr/bin/env python3
"""
Test runner script for the grimdark test suite.

Provides convenient ways to run different types of tests with appropriate
configurations and reporting.
"""
import sys
import argparse
import subprocess
from pathlib import Path


def run_command(cmd: list, description: str):
    """Run a command and handle errors."""
    print(f"=== {description} ===")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print(f"✅ {description} completed successfully\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        print()
        return False


def run_unit_tests():
    """Run unit tests."""
    cmd = ["nix", "develop", "--command", "pytest", "tests/unit/", "-v", "--tb=short"]
    return run_command(cmd, "Unit Tests")


def run_integration_tests():
    """Run integration tests."""
    cmd = ["nix", "develop", "--command", "pytest", "tests/integration/", "-v", "--tb=short", "-m", "integration"]
    return run_command(cmd, "Integration Tests")


def run_performance_tests():
    """Run performance benchmarks."""
    cmd = ["nix", "develop", "--command", "pytest", "tests/performance/", "-v", "--tb=short", "-m", "performance", "--benchmark-only"]
    return run_command(cmd, "Performance Benchmarks")


def run_all_tests():
    """Run all tests with coverage."""
    cmd = ["nix", "develop", "--command", "pytest", "tests/", "-v", "--tb=short", "--cov=src", "--cov-report=term-missing", "--cov-report=html"]
    return run_command(cmd, "All Tests with Coverage")


def run_quick_tests():
    """Run quick tests (unit tests only, no slow tests)."""
    cmd = ["nix", "develop", "--command", "pytest", "tests/unit/", "-v", "--tb=short", "-m", "not slow"]
    return run_command(cmd, "Quick Tests")


def run_code_quality():
    """Run code quality checks."""
    success = True
    
    # Type checking with pyright
    cmd = ["nix", "develop", "--command", "pyright", "."]
    success &= run_command(cmd, "Type Checking (pyright)")
    
    # Linting with ruff
    cmd = ["nix", "develop", "--command", "ruff", "check", "."]
    success &= run_command(cmd, "Code Linting (ruff)")
    
    # Check for unused parameters
    cmd = ["nix", "develop", "--command", "ruff", "check", ".", "--select", "ARG"]
    success &= run_command(cmd, "Unused Parameters Check")
    
    return success




def main():
    parser = argparse.ArgumentParser(description="Run grimdark test suite")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--performance", action="store_true", help="Run performance benchmarks")
    parser.add_argument("--all", action="store_true", help="Run all tests with coverage")
    parser.add_argument("--quick", action="store_true", help="Run quick tests (unit tests, no slow tests)")
    parser.add_argument("--quality", action="store_true", help="Run code quality checks")
    parser.add_argument("--ci", action="store_true", help="Run full CI pipeline")
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        print("No test type specified. Running quick tests by default.")
        print("Use --help to see available options.")
        args.quick = True
    
    success = True
    
    if args.unit:
        success &= run_unit_tests()
    
    if args.integration:
        success &= run_integration_tests()
    
    if args.performance:
        success &= run_performance_tests()
    
    if args.all:
        success &= run_all_tests()
    
    if args.quick:
        success &= run_quick_tests()
    
    if args.quality:
        success &= run_code_quality()
    
    if args.ci:
        print("=== Running Full CI Pipeline ===")
        success = True
        
        # 1. Code quality
        success &= run_code_quality()
        
        # 2. Unit tests
        success &= run_unit_tests()
        
        # 3. Integration tests
        success &= run_integration_tests()
        
        # 4. Performance benchmarks (optional, don't fail CI)
        print("=== Performance Benchmarks (informational) ===")
        run_performance_tests()  # Don't affect CI success
    
    if success:
        print("🎉 All requested tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()