#!/usr/bin/env python3
"""
Test Environment Setup System

A comprehensive system for setting up and verifying the test environment
for the Anonymous Questions Bot. This system ensures proper test configuration
and dependency management.

Features:
- Dependency management
- Environment verification
- Directory structure
- Sample test creation
- Configuration templates
- Next steps guidance

Technical Features:
- Version checking
- Package installation
- Module verification
- Test validation
- Error handling
- Logging support
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: list, description: str = None) -> bool:
    """
    Execute system command with error handling and logging.

    This function provides:
    - Command execution
    - Output capture
    - Error handling
    - Status reporting

    Features:
    - Command validation
    - Error capture
    - Status logging
    - Result reporting

    Args:
        cmd: Command and arguments as list
        description: Optional command description

    Returns:
        bool: True if command succeeded
    """
    if description:
        print(f"🔄 {description}")

    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description or 'Command'} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description or 'Command'} failed:")
        print(f"   Error: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        return False


def check_python_version():
    """
    Validate Python version requirements.

    This function:
    - Checks Python version
    - Validates requirements
    - Reports status

    Features:
    - Version detection
    - Requirement check
    - Status reporting
    - Error handling

    Returns:
        bool: True if version is compatible
    """
    version = sys.version_info
    if version < (3, 10):
        print(
            f"❌ Python 3.10+ required, found {version.major}.{version.minor}")
        return False

    print(f"✅ Python {version.major}.{version.minor} OK")
    return True


def install_dependencies():
    """
    Install project and test dependencies.

    This function provides:
    - Core dependency installation
    - Test dependency management
    - Conflict resolution
    - Status tracking

    Features:
    - Package installation
    - Dependency resolution
    - Error handling
    - Progress tracking

    Returns:
        bool: True if installation succeeded
    """
    print("\n📦 Installing dependencies...")

    # Core dependencies
    success = run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        "Installing core dependencies"
    )

    if not success:
        return False

    # Try minimal test dependencies first
    print("🔄 Trying minimal test dependencies...")
    minimal_deps = [
        "pytest==7.4.3",
        "pytest-asyncio==0.21.1",
        "pytest-cov==4.1.0",
        "pytest-mock==3.12.0",
        "psutil==5.9.6",
        "faker==19.13.0",
        "flake8==6.1.0"
    ]

    for dep in minimal_deps:
        success = run_command(
            [sys.executable, "-m", "pip", "install", dep],
            f"Installing {dep}"
        )
        if not success:
            print(f"⚠️  Skipping {dep} due to conflict")

    # Try full requirements-test.txt if minimal worked
    print("🔄 Attempting full test dependencies...")
    run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"],
        "Installing full test dependencies (optional)"
    )

    return True


def create_directories():
    """
    Create and verify required directory structure.

    This function:
    - Creates test directories
    - Verifies structure
    - Manages permissions
    - Reports status

    Features:
    - Directory creation
    - Permission handling
    - Structure validation
    - Status reporting

    Returns:
        bool: True if directories created/verified
    """
    print("\n📁 Creating directories...")

    directories = [
        "tests",
        "tests/coverage_html",
        "logs"
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created/verified: {directory}/")

    return True


def verify_installation():
    """
    Verify test environment installation.

    This function provides:
    - Package verification
    - Module testing
    - Import validation
    - Status reporting

    Features:
    - Package checks
    - Import testing
    - Error detection
    - Status logging

    Returns:
        bool: True if verification passed
    """
    print("\n🔍 Verifying installation...")

    # Check pytest
    success = run_command(
        [sys.executable, "-m", "pytest", "--version"],
        "Checking pytest"
    )

    if not success:
        return False

    # Check if we can import project modules
    try:
        import models.database
        import handlers.start
        import utils.validators
        print("✅ Project modules import successfully")
    except ImportError as e:
        print(f"❌ Cannot import project modules: {e}")
        return False

    return True


def run_sample_test():
    """
    Create and run sample test for verification.

    This function provides:
    - Test file creation
    - Sample test execution
    - Result validation
    - Status reporting

    Features:
    - File generation
    - Test execution
    - Result validation
    - Error handling

    Returns:
        bool: True if test passed
    """
    print("\n🧪 Running sample test...")

    # Create a simple test if tests directory is empty
    test_file = Path("tests/test_setup.py")
    if not test_file.exists():
        test_content = '''"""
Sample test to verify setup.
"""

import pytest

def test_setup_verification():
    """Test that basic setup works."""
    assert True

@pytest.mark.asyncio
async def test_async_setup():
    """Test async functionality."""
    assert True
'''
        test_file.write_text(test_content)
        print("✅ Created sample test file")

    # Run the test
    success = run_command(
        [sys.executable, "-m", "pytest", "tests/test_setup.py", "-v"],
        "Running sample tests"
    )

    return success


def create_env_example():
    """
    Create example environment configuration.

    This function provides:
    - Template creation
    - Configuration examples
    - Security handling
    - Status reporting

    Features:
    - File generation
    - Template management
    - Security checks
    - Status logging

    Returns:
        bool: True if file created/exists
    """
    env_example = Path(".env.example")
    if not env_example.exists():
        env_content = '''# Bot Configuration
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_user_id
BOT_USERNAME=your_bot_username

# Database Configuration
DB_USER=botanon
DB_PASSWORD=your_password_here
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=dbfrombot

# Optional Settings
LOG_LEVEL=INFO
RATE_LIMIT_QUESTIONS_PER_HOUR=5
MAX_QUESTION_LENGTH=2500
'''
        env_example.write_text(env_content)
        print("✅ Created .env.example")

    return True


def show_next_steps():
    """
    Display setup completion guidance.

    This function provides:
    - Next steps guidance
    - Command examples
    - Usage instructions
    - Helpful tips

    Features:
    - Step listing
    - Command help
    - Usage guidance
    - Tips display
    """
    print("\n🎉 Test setup completed!")
    print("\n📋 Next steps:")
    print("1. Copy .env.example to .env and fill in your values")
    print("2. Run tests: python run_tests.py quick")
    print("3. For full coverage: python run_tests.py full")
    print("4. Use Makefile: make test-quick")
    print("\n💡 Useful commands:")
    print("   make test-quick     # Fast development tests")
    print("   make test-full      # Complete test suite")
    print("   make clean         # Clean test cache")
    print("   make help          # Show all commands")


def main():
    """Main setup function."""
    print("🚀 Anonymous Questions Bot - Test Setup")
    print("=" * 50)

    # Check prerequisites
    if not check_python_version():
        return 1

    # Setup steps
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Creating directories", create_directories),
        ("Creating .env.example", create_env_example),
        ("Verifying installation", verify_installation),
        ("Running sample test", run_sample_test)
    ]

    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        if not step_func():
            print(f"\n❌ Setup failed at: {step_name}")
            print("Please fix the issues above and try again.")
            return 1

    show_next_steps()
    return 0


if __name__ == "__main__":
    sys.exit(main())
