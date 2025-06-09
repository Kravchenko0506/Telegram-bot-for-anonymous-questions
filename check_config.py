#!/usr/bin/env python3
"""
Configuration Security Checker

This script checks for security issues in the configuration.
Run before committing to ensure no secrets are exposed.
"""

import os
import re
import sys
from pathlib import Path


def check_file_for_secrets(filepath: Path) -> list[str]:
    """Check a file for potential secrets."""
    issues = []
    
    # Patterns that might indicate secrets
    secret_patterns = [
        (r'password\s*=\s*["\'][\w\d]{6,}["\']', 'Hardcoded password found'),
        (r'token\s*=\s*["\'][\w\d\-:]{20,}["\']', 'Hardcoded token found'),
        (r'default\s*=\s*["\'][\w\d]{8,}["\']', 'Suspicious default value'),
        (r'BotDB25052025', 'Example password found in code'),
        (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'IP address found (might be okay for localhost)'),
    ]
    
    try:
        content = filepath.read_text(encoding='utf-8')
        
        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern, message in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if it's a comment
                    if line.strip().startswith('#'):
                        continue
                    # Skip if it's in .env.example (those should be empty)
                    if filepath.name == '.env.example':
                        continue
                    # Skip localhost IPs
                    if '127.0.0.1' in line or 'localhost' in line:
                        continue
                        
                    issues.append(f"{filepath}:{line_num} - {message}: {line.strip()}")
    
    except Exception as e:
        issues.append(f"{filepath} - Error reading file: {e}")
    
    return issues


def check_env_file() -> list[str]:
    """Check if .env file exists and is properly ignored."""
    issues = []
    
    env_file = Path('.env')
    gitignore_file = Path('.gitignore')
    
    # Check if .env exists
    if env_file.exists():
        # Check if it's in .gitignore
        if gitignore_file.exists():
            gitignore_content = gitignore_file.read_text()
            if '.env' not in gitignore_content and '*.env' not in gitignore_content:
                issues.append("❌ .env file exists but is NOT in .gitignore!")
        else:
            issues.append("❌ .gitignore file not found!")
    
    # Check if .env.example exists
    if not Path('.env.example').exists():
        issues.append("⚠️  .env.example file not found - create it for documentation")
    
    return issues


def check_config_security() -> bool:
    """Main security check function."""
    print("🔍 Checking configuration security...\n")
    
    all_issues = []
    
    # Files to check
    files_to_check = [
        'config.py',
        'debug_bot.py',
        'debug_simple.py',
        'main.py',
    ]
    
    # Check each file
    for filename in files_to_check:
        filepath = Path(filename)
        if filepath.exists():
            issues = check_file_for_secrets(filepath)
            all_issues.extend(issues)
    
    # Check .env security
    env_issues = check_env_file()
    all_issues.extend(env_issues)
    
    # Report results
    if all_issues:
        print("❌ Security issues found:\n")
        for issue in all_issues:
            print(f"  • {issue}")
        print(f"\n Total issues: {len(all_issues)}")
        return False
    else:
        print("✅ No security issues found!")
        print("✅ Configuration appears to be secure")
        return True


def check_env_variables() -> bool:
    """Check if all required environment variables are set."""
    print("\n🔍 Checking environment variables...\n")
    
    required_vars = [
        'BOT_TOKEN',
        'ADMIN_ID',
        'BOT_USERNAME',
        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'DB_PORT',
        'DB_NAME',
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"  ❌ {var}: NOT SET")
        else:
            # Mask sensitive values
            if 'PASSWORD' in var or 'TOKEN' in var:
                masked_value = value[:4] + '***' + value[-4:] if len(value) > 8 else '***'
                print(f"  ✅ {var}: {masked_value}")
            else:
                print(f"  ✅ {var}: {value}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        print("📋 Copy .env.example to .env and fill in the values")
        return False
    
    print("\n✅ All required environment variables are set")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("🔐 Configuration Security Checker")
    print("=" * 60)
    
    # Run security checks
    security_ok = check_config_security()
    env_ok = check_env_variables()
    
    print("\n" + "=" * 60)
    
    if security_ok and env_ok:
        print("✅ All checks passed! Configuration is secure.")
        sys.exit(0)
    else:
        print("❌ Issues found! Please fix them before deploying.")
        sys.exit(1)