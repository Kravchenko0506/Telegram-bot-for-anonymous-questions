#!/usr/bin/env python3
"""
Test Runner for Anonymous Questions Bot

Provides different test execution scenarios with proper reporting.
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """Manages test execution with different scenarios."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.tests_dir = self.project_root / "tests"
        self.coverage_dir = self.project_root / "tests" / "coverage_html"
        
    def run_command(self, cmd: List[str], description: str = None) -> int:
        """Run command and return exit code."""
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
        """Run quick unit tests only."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "unit",
            "--tb=short",
            "--durations=10",
            "tests/"
        ]
        return self.run_command(cmd, "Running Quick Unit Tests")
    
    def full_tests(self) -> int:
        """Run all tests with coverage."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "--cov=.",
            "--cov-report=html:tests/coverage_html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-fail-under=75",
            "--tb=short",
            "--durations=10",
            "tests/"
        ]
        return self.run_command(cmd, "Running Full Test Suite with Coverage")
    
    def integration_tests(self) -> int:
        """Run integration and database tests."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "integration or database",
            "--tb=short",
            "tests/"
        ]
        return self.run_command(cmd, "Running Integration and Database Tests")
    
    def e2e_tests(self) -> int:
        """Run end-to-end tests."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "e2e",
            "--tb=long",
            "tests/"
        ]
        return self.run_command(cmd, "Running End-to-End Tests")
    
    def security_tests(self) -> int:
        """Run security-focused tests."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "security",
            "--tb=short",
            "tests/"
        ]
        return self.run_command(cmd, "Running Security Tests")
    
    def performance_tests(self) -> int:
        """Run performance tests."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "slow",
            "--tb=short",
            "tests/"
        ]
        return self.run_command(cmd, "Running Performance Tests")
    
    def models_tests(self) -> int:
        """Run model tests only."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "models",
            "--tb=short",
            "tests/test_models.py"
        ]
        return self.run_command(cmd, "Running Model Tests")
    
    def handlers_tests(self) -> int:
        """Run handler tests only."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "handlers",
            "--tb=short",
            "tests/test_handlers.py"
        ]
        return self.run_command(cmd, "Running Handler Tests")
    
    def utils_tests(self) -> int:
        """Run utility tests only."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-m", "utils",
            "--tb=short",
            "tests/test_utils.py"
        ]
        return self.run_command(cmd, "Running Utility Tests")
    
    def ci_tests(self) -> int:
        """Run tests suitable for CI/CD pipeline."""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "--tb=short",
            "--cov=.",
            "--cov-report=xml",
            "--cov-fail-under=70",
            "--maxfail=5",
            "-x",  # Stop on first failure
            "tests/"
        ]
        return self.run_command(cmd, "Running CI/CD Tests")
    
    def lint_check(self) -> int:
        """Run code quality checks."""
        print("\n🔍 Running Code Quality Checks")
        print("=" * 60)
        
        # Check if flake8 is available
        try:
            result = subprocess.run(["flake8", "--version"], capture_output=True)
            if result.returncode == 0:
                cmd = [
                    "flake8",
                    "--max-line-length=120",
                    "--ignore=E501,W503",
                    "--exclude=venv,env,__pycache__,.git",
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
        """Run tests suitable for pre-commit hooks."""
        print("\n🚀 Pre-Commit Test Suite")
        print("=" * 60)
        
        # 1. Lint check
        lint_result = self.lint_check()
        if lint_result != 0:
            return lint_result
        
        # 2. Quick unit tests
        unit_result = self.quick_tests()
        if unit_result != 0:
            return unit_result
        
        # 3. Security tests
        security_result = self.security_tests()
        
        print("\n✅ Pre-commit checks completed")
        return security_result
    
    def deploy_tests(self) -> int:
        """Run comprehensive tests for deployment."""
        print("\n🚀 Deployment Test Suite")
        print("=" * 60)
        
        # 1. Full test suite
        full_result = self.full_tests()
        if full_result != 0:
            print("❌ Full tests failed, deployment not recommended")
            return full_result
        
        # 2. Integration tests
        integration_result = self.integration_tests()
        if integration_result != 0:
            print("❌ Integration tests failed, deployment not recommended")
            return integration_result
        
        # 3. Security tests
        security_result = self.security_tests()
        if security_result != 0:
            print("⚠️  Security tests failed, review before deployment")
        
        print("\n✅ Deployment test suite completed")
        return security_result
    
    def show_coverage_report(self):
        """Show coverage report location."""
        if self.coverage_dir.exists():
            print(f"\n📊 Coverage Report Available:")
            print(f"   HTML: {self.coverage_dir / 'index.html'}")
            print(f"   Open with: open {self.coverage_dir / 'index.html'}")
        else:
            print("\n📊 No coverage report found. Run full tests to generate.")
    
    def clean_cache(self):
        """Clean pytest and coverage cache."""
        print("\n🧹 Cleaning test cache...")
        
        cache_dirs = [
            self.project_root / ".pytest_cache",
            self.project_root / ".coverage",
            self.project_root / "tests" / "coverage_html",
            self.project_root / "coverage.xml",
        ]
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                if cache_dir.is_file():
                    cache_dir.unlink()
                    print(f"   Removed file: {cache_dir}")
                else:
                    import shutil
                    shutil.rmtree(cache_dir)
                    print(f"   Removed directory: {cache_dir}")
        
        # Clean __pycache__ directories
        for pycache_dir in self.project_root.rglob("__pycache__"):
            if pycache_dir.is_dir():
                import shutil
                shutil.rmtree(pycache_dir)
                print(f"   Removed: {pycache_dir}")
        
        print("✅ Cache cleaned")


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Test Runner for Anonymous Questions Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  quick      - Fast unit tests only (~30 seconds)
  full       - All tests with coverage (~2-5 minutes)
  integration- Integration and database tests
  e2e        - End-to-end workflow tests
  security   - Security-focused tests
  performance- Performance and load tests
  models     - Model and database tests only
  handlers   - Handler and bot logic tests only
  utils      - Utility and validation tests only
  ci         - Tests optimized for CI/CD
  pre-commit - Quick checks for pre-commit hooks
  deploy     - Comprehensive tests for deployment

Examples:
  python run_tests.py quick           # Fast unit tests
  python run_tests.py full            # Full test suite with coverage
  python run_tests.py deploy          # Deployment readiness tests
  python run_tests.py --clean         # Clean cache and exit
  python run_tests.py --coverage      # Show coverage report location
        """
    )
    
    parser.add_argument(
        "test_type",
        nargs="?",
        default="quick",
        choices=[
            "quick", "full", "integration", "e2e", "security", "performance",
            "models", "handlers", "utils", "ci", "pre-commit", "deploy"
        ],
        help="Type of tests to run (default: quick)"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean test cache and coverage files"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Show coverage report location"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Handle special flags
    if args.clean:
        runner.clean_cache()
        return 0
    
    if args.coverage:
        runner.show_coverage_report()
        return 0
    
    # Print header
    print("🧪 Anonymous Questions Bot - Test Runner")
    print("=" * 60)
    print(f"Test Type: {args.test_type}")
    print(f"Working Directory: {runner.project_root}")
    print(f"Tests Directory: {runner.tests_dir}")
    
    # Check if tests directory exists
    if not runner.tests_dir.exists():
        print(f"❌ Tests directory not found: {runner.tests_dir}")
        return 1
    
    # Check if pytest is available
    try:
        subprocess.run(["python", "-m", "pytest", "--version"], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pytest not available. Install with: pip install pytest pytest-asyncio pytest-cov")
        return 1
    
    # Run appropriate test suite
    test_methods = {
        "quick": runner.quick_tests,
        "full": runner.full_tests,
        "integration": runner.integration_tests,
        "e2e": runner.e2e_tests,
        "security": runner.security_tests,
        "performance": runner.performance_tests,
        "models": runner.models_tests,
        "handlers": runner.handlers_tests,
        "utils": runner.utils_tests,
        "ci": runner.ci_tests,
        "pre-commit": runner.pre_commit_tests,
        "deploy": runner.deploy_tests,
    }
    
    test_method = test_methods[args.test_type]
    exit_code = test_method()
    
    # Print summary
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ Tests completed successfully!")
        if args.test_type in ["full", "deploy"]:
            runner.show_coverage_report()
    else:
        print("❌ Tests failed!")
        print(f"Exit code: {exit_code}")
    
    # Show next steps
    if args.test_type == "quick" and exit_code == 0:
        print("\n💡 Next steps:")
        print("   - Run 'python run_tests.py full' for complete test suite")
        print("   - Run 'python run_tests.py deploy' before deployment")
    elif args.test_type == "full" and exit_code == 0:
        print("\n💡 Ready for deployment!")
        print("   - Run 'python run_tests.py deploy' for final checks")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())