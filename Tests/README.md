# Testing Infrastructure for Anonymous Questions Bot

Complete testing suite with unit, integration, and end-to-end tests for production-ready Telegram bot.

## 🎯 Overview

This testing infrastructure provides comprehensive coverage for:
- **Bot handlers** and user interactions
- **Database models** and CRUD operations  
- **Input validation** and security
- **Middleware** (rate limiting, error handling)
- **End-to-end workflows**
- **Integration** between components

## 🚀 Quick Start

### Install Dependencies
```bash
# Install test dependencies only
make install-test

# Or install full development environment
make install-dev
```

### Run Tests
```bash
# Fast unit tests (30 seconds)
make test-quick

# Full test suite with coverage (2-5 minutes)
make test-full

# Before deployment
make test-deploy
```

## 📁 Test Structure

```
Tests/
├── conftest.py          # Test fixtures and configuration
├── test_handlers.py     # Bot handlers and user interactions
├── test_models.py       # Database models and operations
├── test_utils.py        # Validation and utility functions
├── test_integration.py  # End-to-end workflows
├── middleware.py        # Middleware testing
├── coverage_html/       # HTML coverage reports
└── README.md           # This file
```

## 🧪 Test Categories

### Unit Tests (`make test-quick`)
Fast, isolated tests without external dependencies:
- ✅ Model creation and validation
- ✅ Input sanitization and validation
- ✅ User state logic
- ✅ Spam detection algorithms
- ✅ Error handling patterns

### Integration Tests (`make test-integration`)
Tests with real database and component interaction:
- ✅ Complete user workflows
- ✅ Database CRUD operations
- ✅ Admin panel functionality
- ✅ State persistence and recovery

### Handler Tests (`make test-handlers`)
Bot interaction and command processing:
- ✅ `/start` command for users and admin
- ✅ Question submission and validation
- ✅ Admin controls and permissions
- ✅ Callback button handling

### Security Tests (`make test-security`)
Security validation and protection:
- ✅ Input sanitization (XSS prevention)
- ✅ Rate limiting enforcement
- ✅ Admin access control
- ✅ Data validation boundaries

## 🛠 Available Commands

### Make Commands
```bash
# Quick development cycle
make test-quick          # Fast unit tests
make test-full           # All tests + coverage
make lint               # Code quality check
make clean              # Clean cache files

# Specific test categories
make test-handlers      # Bot handlers only
make test-models        # Database models only
make test-utils         # Validation utilities only
make test-middleware    # Middleware only

# Development workflow
make dev-test           # Quick tests + lint
make pre-push           # Full validation before git push
make test-deploy        # Deployment readiness check
```

### Python Script Commands
```bash
# Using run_tests.py directly
python run_tests.py quick           # Fast unit tests
python run_tests.py full            # Complete test suite
python run_tests.py integration     # Integration tests only
python run_tests.py deploy          # Deployment validation
python run_tests.py --clean         # Clean cache
python run_tests.py --coverage      # Show coverage location
```

## 📊 Coverage Reports

### HTML Report (Detailed)
```bash
make coverage-html
# Opens: Tests/coverage_html/index.html
```

### Terminal Report
```bash
make test-full
# Shows coverage summary in terminal
```

### CI/CD Integration
```bash
make test-ci
# Generates coverage.xml for CI systems
```

## 🏗 Test Configuration

### Pytest Markers
Tests are organized using pytest markers:

```python
@pytest.mark.unit           # Fast unit tests
@pytest.mark.integration    # Integration tests
@pytest.mark.database       # Requires database
@pytest.mark.handlers       # Bot handler tests
@pytest.mark.models         # Data model tests
@pytest.mark.utils          # Utility function tests
@pytest.mark.security       # Security validation
```

### Run Specific Markers
```bash
pytest -m "unit"                    # Unit tests only
pytest -m "integration or database" # Integration tests
pytest -m "security"                # Security tests only
```

## 🔧 Test Environment

### Environment Variables
Tests use these environment variables:
```bash
TESTING=true                    # Enables test mode
BOT_TOKEN=test_token:test       # Mock bot token
ADMIN_ID=123456789             # Test admin ID
DB_NAME=test_db                # Test database name
LOG_LEVEL=ERROR                # Reduce log noise
```

### Database Testing
- Uses **in-memory SQLite** for fast, isolated tests
- Each test gets a clean database session
- Automatic rollback after each test
- No external database required

## 📈 Performance & Benchmarks

### Test Execution Times
- **Quick tests**: ~30 seconds (unit tests only)
- **Full suite**: ~2-5 minutes (all tests + coverage)
- **Integration**: ~1-2 minutes (database tests)
- **Single category**: ~30-60 seconds

### Coverage Targets
- **Minimum**: 70% overall coverage
- **Target**: 80%+ for critical components
- **Handlers**: 85%+ (user-facing functionality)
- **Models**: 90%+ (data integrity critical)

## 🐛 Debugging Failed Tests

### Verbose Output
```bash
pytest -v --tb=long Tests/test_handlers.py::TestCriticalStartFlow::test_start_regular_user
```

### Debug Specific Test Category
```bash
make test-handlers     # Focus on handler issues
make test-models       # Debug database problems
```

### Clean Environment
```bash
make clean             # Clear cache and retry
make clean-all         # Deep clean including bytecode
```

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Tests
  run: |
    pip install -r requirements.txt
    pip install pytest pytest-asyncio pytest-cov
    make test-ci
    
- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

### Pre-commit Hooks
```bash
make test-pre-commit   # Fast validation for commits
```

### Deployment Validation
```bash
make test-deploy       # Comprehensive pre-deployment check
```

## 🧩 Writing New Tests

### Test Structure Template
```python
import pytest
from unittest.mock import AsyncMock, patch

class TestNewFeature:
    """Test description for new feature."""
    
    @pytest.mark.unit
    async def test_basic_functionality(self, test_message):
        """Test basic functionality works."""
        # Arrange
        test_message.text = "test input"
        
        # Act
        result = await your_function(test_message)
        
        # Assert
        assert result is not None
        test_message.answer.assert_called_once()
```

### Available Fixtures
```python
# Bot objects
test_user           # Regular user object
admin_user          # Admin user object
test_message        # Message from regular user
admin_message       # Message from admin
test_callback       # Callback query object

# Database
clean_db            # Clean database session
sample_question     # Pre-created question
sample_user_state   # Pre-created user state
sample_settings     # Pre-created bot settings

# Mocks
mock_bot            # Mocked Bot instance
mock_async_session  # Mocked database session
mock_user_state_manager     # Mocked UserStateManager
mock_settings_manager       # Mocked SettingsManager
mock_input_validator        # Mocked InputValidator
mock_content_moderator      # Mocked ContentModerator
```

### Testing Async Functions
```python
@pytest.mark.unit
async def test_async_handler(self, test_message, mock_user_state_manager):
    """Test async handler function."""
    # Setup mocks
    mock_user_state_manager.can_send_question = AsyncMock(return_value=True)
    
    # Test the function
    await your_async_handler(test_message)
    
    # Verify async mock was called
    mock_user_state_manager.can_send_question.assert_called_once()
```

## 🚨 Common Issues & Solutions

### Import Errors
```bash
# Issue: ModuleNotFoundError
# Solution: Run from project root
cd /path/to/project
python run_tests.py quick
```

### Database Errors
```bash
# Issue: Database connection failed
# Solution: Tests use in-memory SQLite, no external DB needed
# Check: pytest-asyncio is installed
pip install pytest-asyncio
```

### Async Test Failures
```bash
# Issue: RuntimeError: no running event loop
# Solution: Add @pytest.mark.asyncio to async test functions
@pytest.mark.asyncio
async def test_async_function():
    pass
```

### Mock Issues
```bash
# Issue: Mock not working with async functions
# Solution: Use AsyncMock instead of MagicMock
from unittest.mock import AsyncMock
mock_function = AsyncMock(return_value="test")
```

## 📚 Best Practices

### Test Naming
- Use descriptive names: `test_user_can_send_valid_question`
- Follow pattern: `test_<action>_<expected_result>`
- Group related tests in classes: `TestCriticalUserFlow`

### Test Organization
- **One test per behavior** - don't test multiple things in one test
- **Arrange-Act-Assert** pattern for clarity
- **Independent tests** - each test should work alone

### Mocking Strategy
- **Mock external dependencies** (database, HTTP requests)
- **Don't mock the system under test** - test real code
- **Use fixtures** for common setup to avoid repetition

### Performance
- **Keep unit tests fast** (< 1 second each)
- **Use integration tests** for slower, complex scenarios
- **Clean up properly** to prevent test interference

---

## 🤝 Contributing

When adding new features:
1. **Write tests first** (TDD approach)
2. **Ensure 80%+ coverage** for new code  
3. **Run full test suite** before committing
4. **Update this README** if adding new test categories

### Pre-commit Checklist
- [ ] `make test-quick` passes
- [ ] `make lint` passes  
- [ ] New tests added for new features
- [ ] Coverage threshold maintained
- [ ] Documentation updated

---
