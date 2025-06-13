# Файл: D:\Python\anon_question_bot\conftest.py

import sys
import os
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Mark test as unit test")
    config.addinivalue_line("markers", "handlers: Mark test as handler test")
    config.addinivalue_line(
        "markers", "integration: Mark test as integration test")
    config.addinivalue_line("markers", "database: Mark test as database test")
    config.addinivalue_line("markers", "models: Mark test as model test")
    config.addinivalue_line("markers", "utils: Mark test as utility test")
    config.addinivalue_line("markers", "security: Mark test as security test")
    config.addinivalue_line(
        "markers", "middleware: Mark test as middleware test")


@pytest_asyncio.fixture
async def event_loop():
    """Create an instance of the default event loop for each test case."""
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def test_message():
    """Create a mock message for testing."""
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.from_user.is_bot = False
    message.from_user.first_name = "Test"
    message.from_user.username = "testuser"
    return message


@pytest.fixture
def admin_message():
    """Create a mock admin message for testing."""
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = int(os.getenv('ADMIN_ID', '123456789'))
    message.from_user.is_bot = False
    message.from_user.first_name = "Admin"
    message.from_user.username = "admin"
    return message


@pytest.fixture
def test_callback():
    """Create a mock callback query for testing."""
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    callback.from_user.is_bot = False
    callback.from_user.first_name = "Test"
    callback.from_user.username = "testuser"
    return callback


@pytest.fixture
def mock_user_state_manager():
    """Create a mock UserStateManager."""
    manager = MagicMock()
    manager.can_send_question = AsyncMock(return_value=True)
    manager.set_user_state = AsyncMock(return_value=True)
    manager.allow_new_question = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_async_session():
    """Create a mock async session."""
    session = MagicMock()
    session.__aenter__ = AsyncMock()
    session.__aexit__ = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__.return_value = MagicMock()
    session.__aenter__.return_value.add = MagicMock()
    session.__aenter__.return_value.commit = AsyncMock()
    session.__aenter__.return_value.refresh = AsyncMock()
    session.__aenter__.return_value.get = AsyncMock()
    session.__aenter__.return_value.scalar = AsyncMock()
    return session


@pytest.fixture
def mock_input_validator():
    """Create a mock InputValidator."""
    validator = MagicMock()
    validator.sanitize_text = MagicMock(return_value="Test text")
    validator.validate_question = MagicMock(return_value=(True, None))
    validator.extract_personal_data = MagicMock(
        return_value={'emails': [], 'phones': [], 'urls': []})
    return validator


@pytest.fixture
def mock_content_moderator():
    """Create a mock ContentModerator."""
    moderator = MagicMock()
    moderator.is_likely_spam = MagicMock(return_value=False)
    moderator.calculate_spam_score = MagicMock(return_value=0.0)
    return moderator


@pytest.fixture
def mock_settings_manager():
    """Create a mock SettingsManager."""
    manager = MagicMock()
    manager.get_author_name = AsyncMock(return_value="Test Author")
    manager.get_author_info = AsyncMock(return_value="Test Info")
    return manager
