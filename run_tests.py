#!/usr/bin/env python3
"""
Simple test runner for the grimdark timeline-based game.

Provides a straightforward way to run unit tests for the new architecture.
Focuses on simplicity and ease of use rather than complex test categories.
"""

import sys
import subprocess
import argparse


def run_command(cmd: list[str], description: str) -> bool:
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


def run_unit_tests(verbose: bool = True) -> bool:
    """Run all unit tests."""
    cmd = ["nix", "develop", "--command", "pytest", "tests/"]
    if verbose:
        cmd.append("-v")
    return run_command(cmd, "Unit Tests")


def run_specific_test(test_file: str, verbose: bool = True) -> bool:
    """Run a specific test file."""
    cmd = ["nix", "develop", "--command", "pytest", f"tests/{test_file}"]
    if verbose:
        cmd.append("-v")
    return run_command(cmd, f"Test: {test_file}")


def run_lint_check() -> bool:
    """Run code linting with ruff."""
    cmd = ["nix", "develop", "--command", "ruff", "check", "."]
    return run_command(cmd, "Code Linting (Ruff)")


def run_type_check() -> bool:
    """Run type checking with pyright."""
    cmd = ["nix", "develop", "--command", "pyright", "."]
    return run_command(cmd, "Type Checking (Pyright)")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Simple test runner for grimdark SRPG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all unit tests
  python run_tests.py --quiet            # Run tests with minimal output
  python run_tests.py --test timeline    # Run specific test file
  python run_tests.py --lint             # Run linting only
  python run_tests.py --types            # Run type checking only
  python run_tests.py --all              # Run tests, linting, and type checking
        """
    )
    
    parser.add_argument(
        "--test", 
        help="Run specific test file (e.g., 'timeline' for test_timeline.py)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Run with minimal output"
    )
    parser.add_argument(
        "--lint",
        action="store_true", 
        help="Run code linting only"
    )
    parser.add_argument(
        "--types",
        action="store_true",
        help="Run type checking only"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run tests, linting, and type checking"
    )
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    success = True
    
    if args.test:
        # Run specific test
        test_file = args.test
        if not test_file.startswith("test_"):
            test_file = f"test_{test_file}"
        if not test_file.endswith(".py"):
            test_file = f"{test_file}.py"
        
        success = run_specific_test(test_file, verbose)
        
    elif args.lint:
        # Run linting only
        success = run_lint_check()
        
    elif args.types:
        # Run type checking only
        success = run_type_check()
        
    elif args.all:
        # Run everything
        success = run_unit_tests(verbose)
        if success:
            success = run_lint_check()
        if success:
            success = run_type_check()
            
    else:
        # Default: run unit tests
        success = run_unit_tests(verbose)
    
    if success:
        print("🎉 All operations completed successfully!")
        sys.exit(0)
    else:
        print("💥 Some operations failed. See output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()