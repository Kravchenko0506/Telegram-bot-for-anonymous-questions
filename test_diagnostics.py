#!/usr/bin/env python3
"""
Test Infrastructure Diagnostic System

A comprehensive diagnostic system for analyzing and validating
test infrastructure, identifying issues, and suggesting improvements.

Features:
- Configuration validation
- Test file analysis
- Marker management
- Naming conventions
- Import validation
- Fixture analysis

Technical Features:
- AST parsing
- Pattern matching
- Issue tracking
- Report generation
- Auto-fixing
- Recommendations

Components:
- pytest configuration
- Test file structure
- Marker registration
- Naming conventions
- Import management
- Fixture organization
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import subprocess
import argparse


class TestDiagnostics:
    """
    Test Infrastructure Diagnostic System

    A comprehensive system for analyzing and validating test infrastructure,
    identifying potential issues, and providing improvement recommendations.

    Features:
    - Configuration validation
    - Test file analysis
    - Marker management
    - Naming conventions
    - Import validation
    - Fixture analysis

    Technical Features:
    - AST parsing
    - Pattern matching
    - Issue tracking
    - Report generation
    - Auto-fixing
    - Recommendations

    Components:
    - pytest configuration
    - Test file structure
    - Marker registration
    - Naming conventions
    - Import management
    - Fixture organization

    Attributes:
        project_root: Project root directory path
        tests_dir: Test directory path
        pytest_ini: pytest configuration file path
        issues: List of identified issues
        warnings: List of potential problems
        suggestions: List of improvement suggestions
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.tests_dir = self.project_root / "Tests"
        self.pytest_ini = self.project_root / "pytest.ini"

        # Найденные проблемы
        self.issues = []
        self.warnings = []
        self.suggestions = []

    def scan_all(self) -> Dict[str, any]:
        """
        Execute complete diagnostic scan of test infrastructure.

        This method provides:
        - Configuration validation
        - Test file analysis
        - Marker management
        - Naming convention checks
        - Import validation
        - Fixture analysis

        Features:
        - Complete scanning
        - Issue detection
        - Report generation
        - Status tracking

        Returns:
            Dict containing scan results for each component
        """
        print("🔍 Running test infrastructure diagnostics...")
        print("=" * 60)

        results = {
            'pytest_config': self.check_pytest_config(),
            'test_files': self.scan_test_files(),
            'markers': self.check_markers(),
            'naming': self.check_naming_issues(),
            'imports': self.check_imports(),
            'fixtures': self.check_fixtures()
        }

        self.generate_report(results)
        return results

    def check_pytest_config(self) -> Dict[str, any]:
        """
        Validate pytest configuration settings.

        This method provides:
        - File existence check
        - Section validation
        - Setting verification
        - Mode configuration

        Features:
        - Config validation
        - Section checking
        - Setting analysis
        - Status tracking

        Returns:
            Dict containing configuration validation results
        """
        print("\n📋 Checking pytest.ini...")

        issues = []
        if not self.pytest_ini.exists():
            issues.append("pytest.ini not found")
            return {'status': 'error', 'issues': issues}

        content = self.pytest_ini.read_text(encoding='utf-8')

        # Check sections
        required_sections = ['[tool:pytest]', 'markers']
        for section in required_sections:
            if section not in content:
                issues.append(f"Missing section: {section}")

        # Check asyncio_mode
        if 'asyncio_mode = auto' not in content:
            issues.append("asyncio_mode not configured")

        # Check testpaths
        if 'testpaths = Tests' not in content:
            issues.append("testpaths not configured")

        status = 'error' if issues else 'ok'
        print(f"   {'❌' if issues else '✅'} pytest.ini: {status}")

        return {'status': status, 'issues': issues}

    def scan_test_files(self) -> Dict[str, any]:
        """
        Analyze all test files in the test directory.

        This method provides:
        - File discovery
        - Content analysis
        - Issue detection
        - Status tracking

        Features:
        - File scanning
        - Pattern matching
        - Issue tracking
        - Status reporting

        Returns:
            Dict containing test file analysis results
        """
        print("\n📁 Scanning test files...")

        if not self.tests_dir.exists():
            print("   ❌ Tests directory not found")
            return {'status': 'error', 'files': []}

        test_files = list(self.tests_dir.glob("test_*.py"))
        test_files.extend(self.tests_dir.glob("*_test.py"))

        file_results = []
        for test_file in test_files:
            result = self.analyze_test_file(test_file)
            file_results.append(result)

        total_issues = sum(len(r['issues']) for r in file_results)
        status = 'error' if total_issues > 0 else 'ok'

        print(
            f"   {'❌' if total_issues else '✅'} Found files: {len(test_files)}, issues: {total_issues}")

        return {
            'status': status,
            'files': file_results,
            'total_files': len(test_files),
            'total_issues': total_issues
        }

    def analyze_test_file(self, file_path: Path) -> Dict[str, any]:
        """
        Perform detailed analysis of a single test file.

        This method provides:
        - Content parsing
        - AST analysis
        - Pattern detection
        - Issue identification

        Features:
        - AST parsing
        - Pattern matching
        - Issue tracking
        - Status reporting

        Args:
            file_path: Path to test file

        Returns:
            Dict containing file analysis results
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)

            issues = []
            methods = []
            classes = []
            markers = set()

            # Find test classes and methods
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                    classes.append(node.name)

                    # Check methods in class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                            methods.append(f"{node.name}::{item.name}")

                            # Check for "_FIXED" in name
                            if "_FIXED" in item.name:
                                issues.append(
                                    f"Method contains '_FIXED' in name: {item.name}")

                            # Find markers
                            for decorator in item.decorator_list:
                                if isinstance(decorator, ast.Attribute):
                                    if (isinstance(decorator.value, ast.Attribute) and
                                            decorator.value.attr == 'mark'):
                                        markers.add(decorator.attr)

                # Find module-level functions
                elif isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    methods.append(node.name)

                    if "_FIXED" in node.name:
                        issues.append(
                            f"Function contains '_FIXED' in name: {node.name}")

            # Check imports
            import_issues = self.check_file_imports(content)
            issues.extend(import_issues)

            return {
                'file': file_path.name,
                'path': str(file_path),
                'classes': classes,
                'methods': methods,
                'markers': list(markers),
                'issues': issues,
                'status': 'error' if issues else 'ok'
            }

        except Exception as e:
            return {
                'file': file_path.name,
                'path': str(file_path),
                'error': str(e),
                'status': 'error',
                'issues': [f"Parse error: {e}"]
            }

    def check_file_imports(self, content: str) -> List[str]:
        """
        Validate imports in a test file.

        This method provides:
        - Import detection
        - Pattern matching
        - Requirement checking
        - Issue tracking

        Features:
        - Import validation
        - Pattern matching
        - Issue detection
        - Status tracking

        Args:
            content: File content to check

        Returns:
            List of import-related issues
        """
        issues = []

        # Check core test imports
        required_imports = ['pytest']
        for imp in required_imports:
            if f"import {imp}" not in content and f"from {imp}" not in content:
                issues.append(f"Missing import: {imp}")

        return issues

    def check_markers(self) -> Dict[str, any]:
        """
        Validate pytest marker configuration and usage.

        This method provides:
        - Marker registration check
        - Usage validation
        - Pattern detection
        - Issue tracking

        Features:
        - Marker validation
        - Usage analysis
        - Pattern matching
        - Status reporting

        Returns:
            Dict containing marker validation results
        """
        print("\n🏷️  Checking pytest markers...")

        # Get registered markers
        registered_markers = self.get_registered_markers()

        # Get used markers
        used_markers = self.get_used_markers()

        # Find unregistered markers
        unregistered = used_markers - registered_markers
        unused = registered_markers - used_markers

        issues = []
        if unregistered:
            issues.append(f"Unregistered markers: {', '.join(unregistered)}")

        warnings = []
        if unused:
            warnings.append(f"Unused markers: {', '.join(unused)}")

        status = 'error' if issues else ('warning' if warnings else 'ok')
        print(f"   {'❌' if issues else '⚠️' if warnings else '✅'} Markers: {len(registered_markers)} registered, {len(used_markers)} used")

        return {
            'status': status,
            'registered': list(registered_markers),
            'used': list(used_markers),
            'unregistered': list(unregistered),
            'unused': list(unused),
            'issues': issues,
            'warnings': warnings
        }

    def get_registered_markers(self) -> Set[str]:
        """
        Get registered markers from pytest.ini.

        This method provides:
        - Configuration parsing
        - Marker extraction
        - Pattern matching
        - Set management

        Features:
        - Config parsing
        - Pattern detection
        - Set operations
        - Error handling

        Returns:
            Set of registered marker names
        """
        if not self.pytest_ini.exists():
            return set()

        content = self.pytest_ini.read_text(encoding='utf-8')
        markers = set()

        # Find markers section
        in_markers_section = False
        for line in content.split('\n'):
            line = line.strip()

            if line.startswith('[markers]'):
                in_markers_section = True
                continue
            elif line.startswith('[') and in_markers_section:
                break

            if in_markers_section and line and not line.startswith('#'):
                marker = line.split(':', 1)[0].strip()
                markers.add(marker)

        return markers

    def get_used_markers(self) -> Set[str]:
        """
        Get markers used in test files.

        This method provides:
        - File scanning
        - Marker detection
        - Pattern matching
        - Set management

        Features:
        - File parsing
        - Pattern detection
        - Set operations
        - Error handling

        Returns:
            Set of used marker names
        """
        markers = set()

        # Scan all test files
        test_files = list(self.tests_dir.glob("test_*.py"))
        test_files.extend(self.tests_dir.glob("*_test.py"))

        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                tree = ast.parse(content)

                # Find pytest.mark decorators
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Attribute):
                                if (isinstance(decorator.value, ast.Attribute) and
                                        decorator.value.attr == 'mark'):
                                    markers.add(decorator.attr)
            except Exception:
                continue

        return markers

    def check_naming_issues(self) -> Dict[str, any]:
        """
        Check test naming conventions.

        This method provides:
        - Pattern validation
        - Convention checking
        - Issue detection
        - Status tracking

        Features:
        - Pattern matching
        - Convention validation
        - Issue tracking
        - Status reporting

        Returns:
            Dict containing naming validation results
        """
        print("\n📝 Checking naming conventions...")

        issues = []
        test_files = list(self.tests_dir.glob("test_*.py"))
        test_files.extend(self.tests_dir.glob("*_test.py"))

        for test_file in test_files:
            # Check file naming
            if not (test_file.name.startswith('test_') or test_file.name.endswith('_test.py')):
                issues.append(f"Invalid test file name: {test_file.name}")

            try:
                content = test_file.read_text(encoding='utf-8')
                tree = ast.parse(content)

                # Check class and method naming
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if not node.name.startswith('Test'):
                            issues.append(
                                f"Invalid test class name: {node.name} in {test_file.name}")

                    elif isinstance(node, ast.FunctionDef):
                        if not node.name.startswith('test_'):
                            issues.append(
                                f"Invalid test function name: {node.name} in {test_file.name}")
            except Exception as e:
                issues.append(f"Error checking {test_file.name}: {e}")

        status = 'error' if issues else 'ok'
        print(f"   {'❌' if issues else '✅'} Naming conventions")

        return {
            'status': status,
            'issues': issues
        }

    def check_imports(self) -> Dict[str, any]:
        """
        Check test file imports.

        This method provides:
        - Import validation
        - Pattern checking
        - Issue detection
        - Status tracking

        Features:
        - Import checking
        - Pattern matching
        - Issue tracking
        - Status reporting

        Returns:
            Dict containing import validation results
        """
        print("\n📦 Checking imports...")

        issues = []
        test_files = list(self.tests_dir.glob("test_*.py"))
        test_files.extend(self.tests_dir.glob("*_test.py"))

        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                file_issues = self.check_file_imports(content)
                if file_issues:
                    issues.extend(
                        [f"{test_file.name}: {issue}" for issue in file_issues])
            except Exception as e:
                issues.append(f"Error checking {test_file.name}: {e}")

        status = 'error' if issues else 'ok'
        print(f"   {'❌' if issues else '✅'} Import validation")

        return {
            'status': status,
            'issues': issues
        }

    def check_fixtures(self) -> Dict[str, any]:
        """
        Check test fixture configuration and usage.

        This method provides:
        - Fixture validation
        - Usage checking
        - Pattern detection
        - Status tracking

        Features:
        - Fixture checking
        - Usage validation
        - Pattern matching
        - Status reporting

        Returns:
            Dict containing fixture validation results
        """
        print("\n🔧 Checking fixtures...")

        issues = []
        fixtures = set()
        usages = set()

        # Scan conftest.py for fixtures
        conftest = self.project_root / "conftest.py"
        if conftest.exists():
            try:
                content = conftest.read_text(encoding='utf-8')
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Call):
                                if (isinstance(decorator.func, ast.Attribute) and
                                        decorator.func.attr == 'fixture'):
                                    fixtures.add(node.name)
            except Exception as e:
                issues.append(f"Error parsing conftest.py: {e}")

        # Check fixture usage
        test_files = list(self.tests_dir.glob("test_*.py"))
        test_files.extend(self.tests_dir.glob("*_test.py"))

        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for arg in node.args.args:
                            if arg.arg in fixtures:
                                usages.add(arg.arg)
            except Exception as e:
                issues.append(f"Error checking {test_file.name}: {e}")

        # Find unused fixtures
        unused = fixtures - usages
        if unused:
            issues.append(f"Unused fixtures: {', '.join(unused)}")

        status = 'error' if issues else 'ok'
        print(f"   {'❌' if issues else '✅'} Fixture validation")

        return {
            'status': status,
            'fixtures': list(fixtures),
            'used': list(usages),
            'unused': list(unused),
            'issues': issues
        }

    def generate_report(self, results: Dict[str, any]):
        """
        Generate diagnostic report.

        This method provides:
        - Result aggregation
        - Issue summarization
        - Status reporting
        - Recommendation generation

        Features:
        - Result collection
        - Issue tracking
        - Status reporting
        - Report formatting
        """
        print("\n📊 Diagnostic Report")
        print("=" * 60)

        # Overall status
        has_errors = any(r.get('status') == 'error' for r in results.values())
        has_warnings = any(r.get('status') ==
                           'warning' for r in results.values())

        if has_errors:
            print("❌ Issues found that require attention")
        elif has_warnings:
            print("⚠️  Minor issues found")
        else:
            print("✅ All checks passed")

        # Component status
        print("\nComponent Status:")
        for component, result in results.items():
            status = result.get('status', 'unknown')
            icon = '❌' if status == 'error' else '⚠️' if status == 'warning' else '✅'
            print(f"{icon} {component}: {status}")

        # Issue summary
        total_issues = sum(
            len(r.get('issues', [])) for r in results.values()
        )
        if total_issues:
            print(f"\nTotal issues found: {total_issues}")

            print("\nIssues by component:")
            for component, result in results.items():
                issues = result.get('issues', [])
                if issues:
                    print(f"\n{component}:")
                    for issue in issues:
                        print(f"  - {issue}")

        # Generate recommendations
        self.generate_recommendations(results)

    def generate_recommendations(self, results: Dict[str, any]):
        """
        Generate improvement recommendations.

        This method provides:
        - Issue analysis
        - Solution suggestion
        - Priority setting
        - Action planning

        Features:
        - Issue analysis
        - Solution generation
        - Priority assignment
        - Action planning

        Args:
            results: Diagnostic results
        """
        print("\n💡 Recommendations:")

        if results['pytest_config']['status'] == 'error':
            print("\npytest Configuration:")
            print("1. Create or update pytest.ini")
            print("2. Add required sections: [tool:pytest], markers")
            print("3. Configure asyncio_mode and testpaths")

        if results['markers']['status'] in ['error', 'warning']:
            print("\nMarker Management:")
            print("1. Register all markers in pytest.ini")
            print("2. Remove unused markers")
            print("3. Standardize marker naming")

        if results['naming']['status'] == 'error':
            print("\nNaming Conventions:")
            print("1. Rename test files to start with 'test_'")
            print("2. Rename test classes to start with 'Test'")
            print("3. Rename test functions to start with 'test_'")

        if results['fixtures']['status'] == 'error':
            print("\nFixture Management:")
            print("1. Remove unused fixtures")
            print("2. Document fixture purposes")
            print("3. Consider fixture scoping")

    def auto_fix(self):
        """
        Attempt to automatically fix common issues.

        This method provides:
        - Issue resolution
        - Code modification
        - Status tracking
        - Result reporting

        Features:
        - Auto-fixing
        - Code updating
        - Status tracking
        - Result reporting
        """
        print("\n🔧 Attempting automatic fixes...")

        fixes_applied = []

        # Fix pytest.ini
        if not self.pytest_ini.exists():
            self.create_default_pytest_ini()
            fixes_applied.append("Created default pytest.ini")

        # Fix naming issues
        test_files = list(self.tests_dir.glob("*.py"))
        for test_file in test_files:
            if not (test_file.name.startswith('test_') or test_file.name.endswith('_test.py')):
                new_name = f"test_{test_file.name}"
                test_file.rename(test_file.parent / new_name)
                fixes_applied.append(f"Renamed {test_file.name} to {new_name}")

        if fixes_applied:
            print("\nApplied fixes:")
            for fix in fixes_applied:
                print(f"✅ {fix}")
        else:
            print("No automatic fixes required")

    def run_test_discovery(self):
        """
        Run test discovery process.

        This method provides:
        - Test discovery
        - Pattern matching
        - Status tracking
        - Result reporting

        Features:
        - Test finding
        - Pattern matching
        - Status tracking
        - Result reporting
        """
        print("\n🔍 Running test discovery...")

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ Test discovery successful")
                print(result.stdout)
            else:
                print("❌ Test discovery failed")
                print(result.stderr)

            return result.returncode == 0

        except Exception as e:
            print(f"❌ Error during test discovery: {e}")
            return False


def main():
    """
    Main entry point for test diagnostics.

    This function provides:
    - Argument parsing
    - Diagnostic execution
    - Result reporting
    - Auto-fixing

    Features:
    - Command parsing
    - Mode selection
    - Error handling
    - Status reporting

    Modes:
    - scan: Run diagnostics
    - fix: Auto-fix issues
    - discover: Run test discovery
    """
    parser = argparse.ArgumentParser(
        description="Test Infrastructure Diagnostic Tool",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "mode",
        choices=["scan", "fix", "discover"],
        help="""Operation mode:
scan     - Run diagnostic scan
fix      - Auto-fix issues
discover - Run test discovery
"""
    )

    parser.add_argument(
        "--project",
        default=".",
        help="Project root directory (default: current directory)"
    )

    args = parser.parse_args()

    try:
        diagnostics = TestDiagnostics(args.project)

        if args.mode == "scan":
            diagnostics.scan_all()
        elif args.mode == "fix":
            diagnostics.auto_fix()
        elif args.mode == "discover":
            diagnostics.run_test_discovery()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
