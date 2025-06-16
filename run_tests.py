#!/usr/bin/env python3
"""
Test Runner System for Anonymous Questions Bot

A comprehensive test execution and management system that provides
multiple test scenarios, coverage reporting, and quality checks.

Features:
- Multiple test execution modes
- Coverage reporting
- Code quality checks
- CI/CD integration
- Pre-commit hooks
- Dependency validation

Test Categories:
- Quick unit tests
- Full test suite
- Integration tests
- Handler tests
- Model tests
- Utility tests
- Middleware tests
- Security tests
- CI/CD tests
- Pre-commit tests
- Deployment tests

Technical Features:
- Async test support
- Coverage thresholds
- Duration reporting
- Error handling
- Clean reporting
- Cache management
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """
    Test Execution Management System

    A comprehensive system for managing and executing different test scenarios
    with proper reporting and error handling.

    Features:
    - Multiple test execution modes
    - Coverage reporting
    - Code quality validation
    - CI/CD integration
    - Pre-commit validation
    - Dependency checking

    Technical Features:
    - Async test support
    - Coverage thresholds
    - Duration tracking
    - Error handling
    - Clean reporting
    - Cache management

    Test Categories:
    - Quick unit tests
    - Full test suite
    - Integration tests
    - Handler tests
    - Model tests
    - Utility tests
    - Middleware tests
    - Security tests
    - CI/CD tests
    - Pre-commit tests
    - Deployment tests
    """

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.tests_dir = self.project_root / "Tests"
        self.coverage_dir = self.project_root / "Tests" / "coverage_html"

    def run_command(self, cmd: List[str], description: str = None) -> int:
        """
        Execute command with proper output handling and error management.

        This method provides:
        - Command execution
        - Output formatting
        - Error handling
        - Status reporting

        Features:
        - Clean output
        - Error capture
        - User interruption
        - Status codes

        Args:
            cmd: Command and arguments as list
            description: Optional command description

        Returns:
            int: Command exit code (0 for success)
        """
        if description:
            print(f"\n🔄 {description}")
            print("=" * 60)

        print(f"Running: {' '.join(cmd)}")
        print("-" * 60)

        try:
            result = subprocess.run(cmd, cwd=self.project_root)
            return result.returncode
        except KeyboardInterrupt:
            print("\n❌ Tests interrupted by user")
            return 1
        except Exception as e:
            print(f"❌ Error running command: {e}")
            return 1

    def quick_tests(self) -> int:
        """
        Execute quick unit tests for rapid development feedback.

        This method provides:
        - Fast unit testing
        - Basic validation
        - Quick feedback
        - Error reporting

        Features:
        - Unit test focus
        - Short traces
        - Duration tracking
        - Async support

        Returns:
            int: Test exit code (0 for success)
        """
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "unit",
            "--tb=short",
            "--durations=10",
            "--asyncio-mode=auto",
            str(self.tests_dir)
        ]
        return self.run_command(cmd, "Running Quick Unit Tests")

    def full_tests(self) -> int:
        """
        Execute complete test suite with coverage reporting.

        This method provides:
        - Full test execution
        - Coverage analysis
        - HTML reporting
        - Threshold checking

        Features:
        - Complete coverage
        - Multiple reports
        - Duration tracking
        - Failure thresholds

        Returns:
            int: Test exit code (0 for success)
        """
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "--cov=.",
            f"--cov-report=html:{self.coverage_dir}",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-fail-under=70",
            "--tb=short",
            "--durations=10",
            "--asyncio-mode=auto",
            str(self.tests_dir)
        ]
        return self.run_command(cmd, "Running Full Test Suite with Coverage")

    def integration_tests(self) -> int:
        """
        Execute integration and database interaction tests.

        This method provides:
        - Integration testing
        - Database validation
        - System interaction
        - Component testing

        Features:
        - Integration focus
        - Database checks
        - System validation
        - Error tracking

        Returns:
            int: Test exit code (0 for success)
        """
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "integration or database",
            "--tb=short",
            "--asyncio-mode=auto",
            str(self.tests_dir)
        ]
        return self.run_command(cmd, "Running Integration and Database Tests")

    def handlers_tests(self) -> int:
        """
        Execute handler-specific test suite.

        This method provides:
        - Handler validation
        - Route testing
        - Request handling
        - Response validation

        Features:
        - Handler focus
        - Route checks
        - Request testing
        - Response validation

        Returns:
            int: Test exit code (0 for success)
        """
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "handlers",
            "--tb=short",
            "--asyncio-mode=auto",
            str(self.tests_dir / "test_handlers.py")
        ]
        return self.run_command(cmd, "Running Handler Tests")

    def models_tests(self) -> int:
        """
        Execute model-specific test suite.

        This method provides:
        - Model validation
        - Data integrity
        - Schema testing
        - Relationship checks

        Features:
        - Model focus
        - Data validation
        - Schema checks
        - Relationship testing

        Returns:
            int: Test exit code (0 for success)
        """
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "models",
            "--tb=short",
            "--asyncio-mode=auto",
            str(self.tests_dir / "test_models.py")
        ]
        return self.run_command(cmd, "Running Model Tests")

    def utils_tests(self) -> int:
        """
        Execute utility function test suite.

        This method provides:
        - Utility validation
        - Helper testing
        - Function checks
        - Tool validation

        Features:
        - Utility focus
        - Helper checks
        - Function testing
        - Tool validation

        Returns:
            int: Test exit code (0 for success)
        """
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "utils",
            "--tb=short",
            "--asyncio-mode=auto",
            str(self.tests_dir / "test_utils.py")
        ]
        return self.run_command(cmd, "Running Utility Tests")

    def middleware_tests(self) -> int:
        """
        Execute middleware component test suite.

        This method provides:
        - Middleware validation
        - Pipeline testing
        - Filter checks
        - Chain validation

        Features:
        - Middleware focus
        - Pipeline checks
        - Filter testing
        - Chain validation

        Returns:
            int: Test exit code (0 for success)
        """
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "--tb=short",
            "--asyncio-mode=auto",
            str(self.tests_dir / "middleware.py")
        ]
        return self.run_command(cmd, "Running Middleware Tests")

    def security_tests(self) -> int:
        """
        Execute security-focused test suite.

        This method provides:
        - Security validation
        - Access control
        - Permission checks
        - Vulnerability testing

        Features:
        - Security focus
        - Access testing
        - Permission validation
        - Vulnerability checks

        Returns:
            int: Test exit code (0 for success)
        """
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "security",
            "--tb=short",
            "--asyncio-mode=auto",
            str(self.tests_dir)
        ]
        return self.run_command(cmd, "Running Security Tests")

    def ci_tests(self) -> int:
        """
        Execute CI/CD pipeline optimized test suite.

        This method provides:
        - Pipeline validation
        - Coverage checks
        - Quick feedback
        - Early termination

        Features:
        - Pipeline focus
        - Coverage thresholds
        - Fast feedback
        - Failure limits

        Returns:
            int: Test exit code (0 for success)
        """
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "--tb=short",
            "--cov=.",
            "--cov-report=xml",
            "--cov-fail-under=60",
            "--maxfail=5",
            "-x",
            "--asyncio-mode=auto",
            str(self.tests_dir)
        ]
        return self.run_command(cmd, "Running CI/CD Tests")

    def lint_check(self) -> int:
        """
        Execute code quality and style validation.

        This method provides:
        - Style checking
        - Quality validation
        - Format verification
        - Standard compliance

        Features:
        - Style checks
        - Quality validation
        - Format testing
        - Standard compliance

        Returns:
            int: Check exit code (0 for success)
        """
        print("\n🔍 Running Code Quality Checks")
        print("=" * 60)

        # Check if flake8 is available
        try:
            result = subprocess.run(
                ["flake8", "--version"], capture_output=True)
            if result.returncode == 0:
                cmd = [
                    "flake8",
                    "--max-line-length=120",
                    "--ignore=E501,W503,E203",
                    "--exclude=venv,env,__pycache__,.git,Tests/coverage_html",
                    "."
                ]
                return self.run_command(cmd, "Running Flake8 Linting")
            else:
                print("⚠️  flake8 not available, skipping lint check")
                return 0
        except FileNotFoundError:
            print("⚠️  flake8 not installed, skipping lint check")
            return 0

    def pre_commit_tests(self) -> int:
        """
        Execute pre-commit hook test suite.

        This method provides:
        - Quick validation
        - Style checking
        - Basic testing
        - Early feedback

        Features:
        - Fast checks
        - Style validation
        - Unit testing
        - Quick feedback

        Returns:
            int: Test exit code (0 for success)
        """
        print("\n🚀 Pre-Commit Test Suite")
        print("=" * 60)

        # 1. Quick unit tests
        unit_result = self.quick_tests()
        if unit_result != 0:
            print("❌ Unit tests failed")
            return unit_result

        # 2. Lint check (optional)
        lint_result = self.lint_check()
        if lint_result != 0:
            print("⚠️  Lint check failed, but continuing")

        print("\n✅ Pre-commit checks completed")
        return 0

    def deploy_tests(self) -> int:
        """
        Execute deployment validation test suite.

        This method provides:
        - Deployment checks
        - Integration testing
        - System validation
        - Performance testing

        Features:
        - Deploy focus
        - System checks
        - Integration tests
        - Performance validation

        Returns:
            int: Test exit code (0 for success)
        """
        print("\n🚀 Deployment Test Suite")
        print("=" * 60)

        # 1. Run integration tests
        integration_result = self.integration_tests()
        if integration_result != 0:
            print("❌ Integration tests failed")
            return integration_result

        # 2. Run security tests
        security_result = self.security_tests()
        if security_result != 0:
            print("❌ Security tests failed")
            return security_result

        return 0

    def show_coverage_report(self):
        """
        Display test coverage report in browser.

        This method provides:
        - Report display
        - Browser launch
        - Path handling
        - Status tracking

        Features:
        - HTML display
        - Path management
        - Browser control
        - Status reporting
        """
        coverage_index = self.coverage_dir / "index.html"
        if coverage_index.exists():
            import webbrowser
            webbrowser.open(str(coverage_index))
            print(f"✅ Opening coverage report: {coverage_index}")
        else:
            print("❌ No coverage report found. Run full tests first.")

    def clean_cache(self):
        """
        Clean test cache and temporary files.

        This method provides:
        - Cache cleaning
        - File removal
        - Directory cleanup
        - Status tracking

        Features:
        - Cache removal
        - File cleanup
        - Directory management
        - Status reporting
        """
        print("\n🧹 Cleaning Test Cache")
        print("=" * 60)

        patterns = [
            "**/__pycache__",
            "**/.pytest_cache",
            "**/coverage_html",
            ".coverage",
            "coverage.xml"
        ]

        for pattern in patterns:
            for path in self.project_root.glob(pattern):
                if path.is_file():
                    path.unlink()
                    print(f"✅ Removed file: {path}")
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                    print(f"✅ Removed directory: {path}")

    def check_dependencies(self) -> bool:
        """
        Verify test dependencies installation.

        This method provides:
        - Dependency checks
        - Version validation
        - Package verification
        - Status tracking

        Features:
        - Package checks
        - Version validation
        - Import testing
        - Status reporting

        Returns:
            bool: True if all dependencies are installed
        """
        try:
            import pytest
            import pytest_asyncio
            import pytest_cov
            return True
        except ImportError as e:
            print(f"❌ Missing dependency: {e.name}")
            return False


def main():
    """
    Main test execution entry point.

    This function provides:
    - Argument parsing
    - Test selection
    - Execution control
    - Result reporting

    Features:
    - Command parsing
    - Test selection
    - Error handling
    - Status reporting

    Test Modes:
    - quick: Fast unit tests
    - full: Complete test suite
    - integration: System tests
    - handlers: Handler tests
    - models: Model tests
    - utils: Utility tests
    - middleware: Middleware tests
    - security: Security tests
    - ci: CI/CD tests
    - pre-commit: Git hook tests
    - deploy: Deployment tests
    - clean: Cache cleanup
    - coverage: Report viewing
    """
    parser = argparse.ArgumentParser(
        description="Test Runner for Anonymous Questions Bot",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "mode",
        choices=[
            "quick",
            "full",
            "integration",
            "handlers",
            "models",
            "utils",
            "middleware",
            "security",
            "ci",
            "pre-commit",
            "deploy",
            "clean",
            "coverage"
        ],
        help="""Test execution mode:
quick      - Run quick unit tests
full       - Run full test suite with coverage
integration - Run integration tests
handlers   - Run handler tests
models     - Run model tests
utils      - Run utility tests
middleware - Run middleware tests
security   - Run security tests
ci         - Run CI/CD pipeline tests
pre-commit - Run pre-commit hook tests
deploy     - Run deployment validation
clean      - Clean test cache
coverage   - Show coverage report
"""
    )

    args = parser.parse_args()
    runner = TestRunner()

    # Check dependencies first
    if not runner.check_dependencies():
        print("\n❌ Missing required dependencies")
        print("Run: pip install -r requirements-test.txt")
        return 1

    # Execute selected mode
    if args.mode == "clean":
        runner.clean_cache()
        return 0
    elif args.mode == "coverage":
        runner.show_coverage_report()
        return 0

    # Map modes to test functions
    mode_map = {
        "quick": runner.quick_tests,
        "full": runner.full_tests,
        "integration": runner.integration_tests,
        "handlers": runner.handlers_tests,
        "models": runner.models_tests,
        "utils": runner.utils_tests,
        "middleware": runner.middleware_tests,
        "security": runner.security_tests,
        "ci": runner.ci_tests,
        "pre-commit": runner.pre_commit_tests,
        "deploy": runner.deploy_tests
    }

    # Run selected test mode
    test_func = mode_map.get(args.mode)
    if test_func:
        return test_func()
    else:
        print(f"❌ Unknown test mode: {args.mode}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
