"""
Test configuration and fixtures for the bot test suite.

This module provides:
- Database fixtures with in-memory SQLite
- Mock objects for bot testing
- Test data factories
- Helper functions for assertions
- Environment setup and teardown

Key components:
- Database session management
- Bot and user mocking
- Message and callback simulation
- Test data generation
"""

import pytest
import pytest_asyncio
import asyncio
import sys
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch, create_autospec
from datetime import datetime

# Database testing
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from models.questions import Question

# Bot testing
from aiogram import Bot
from aiogram.types import User, Chat, Message, CallbackQuery

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# ==================== PYTEST CONFIGURATION ====================


def pytest_configure(config):
    """Configure pytest environment and register custom markers.

    Sets up:
    - Warning filters for deprecation notices
    - Custom test markers for different test types
    - Pydantic V2 compatibility settings
    """
    import warnings
    from pydantic._internal._model_construction import PydanticDeprecatedSince20

    # Filter standard warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    # Filter Pydantic V2 warnings
    warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
    warnings.filterwarnings("ignore", message=".*__fields__.*")
    warnings.filterwarnings("ignore", message=".*model_fields.*")

    # Register markers
    config.addinivalue_line(
        "markers", "integration: Mark test as integration test")
    config.addinivalue_line("markers", "unit: Mark test as unit test")
    config.addinivalue_line("markers", "handlers: Mark test as handler test")
    config.addinivalue_line("markers", "database: Mark test as database test")
    config.addinivalue_line("markers", "models: Mark test as model test")
    config.addinivalue_line("markers", "utils: Mark test as utility test")
    config.addinivalue_line("markers", "security: Mark test as security test")
    config.addinivalue_line(
        "markers", "middleware: Mark test as middleware test")


@pytest_asyncio.fixture(scope="function")
async def event_loop():
    """Create an instance of the default event loop for each test case.

    Handles platform-specific event loop creation:
    - Uses ProactorEventLoop for Windows
    - Uses default event loop for other platforms
    """
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

# ==================== DATABASE FIXTURES ====================


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create and configure test database engine.

    Sets up:
    - In-memory SQLite database
    - Table creation for all models
    - Connection pool configuration
    - Automatic cleanup on test completion
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )

    # Import models to ensure they're registered
    from models.database import Base
    from models.questions import Question
    from models.user_states import UserState
    from models.settings import BotSettings
    from models.admin_state import AdminState

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def clean_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide clean database session for each test.

    Features:
    - Fresh database state for each test
    - Automatic table cleanup
    - Session management
    - Error handling and cleanup
    """
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    session = async_session_factory()

    # Clear all tables before test
    from models.database import Base
    async with session.begin():
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())

    try:
        yield session
    finally:
        # Clean up after test
        await session.close()

# ==================== BOT FIXTURES ====================


@pytest.fixture
def mock_bot():
    """Create a mock bot instance with common methods.

    Mocked methods:
    - send_message
    - edit_message_text
    - answer_callback_query
    """
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    return bot


@pytest.fixture
def test_user():
    """Create a mock user for testing.

    Properties:
    - Standard user ID
    - Non-bot status
    - Test username and first name
    """
    user = MagicMock(spec=User)
    user.id = 123456789
    user.is_bot = False
    user.first_name = "Test"
    user.username = "testuser"
    return user


@pytest.fixture
def admin_user():
    """Create an admin user object for testing.

    Properties:
    - Admin ID from environment
    - Non-bot status
    - Admin username and first name
    """
    admin_id = int(os.getenv('ADMIN_ID', '123456789'))
    return User(
        id=admin_id,
        is_bot=False,
        first_name="Admin",
        username="admin"
    )


@pytest.fixture
def test_chat():
    """Create a mock chat for testing."""
    chat = MagicMock(spec=Chat)
    chat.id = 123456789
    chat.type = "private"
    return chat


@pytest.fixture
def admin_chat():
    """Create admin chat object."""
    admin_id = int(os.getenv('ADMIN_ID', '123456789'))
    return Chat(id=admin_id, type="private")


@pytest.fixture
def test_message(test_user, test_chat, mock_bot):
    """Create a test message object with Pydantic V2 compatibility.

    Features:
    - Message ID and timestamp
    - User and chat information
    - Mock reply methods
    - Bot instance reference
    """
    # Create a mock that behaves like Message but allows attribute assignment
    message = MagicMock(spec=Message)

    # Set the required attributes
    message.message_id = 1
    message.date = datetime.now()
    message.chat = test_chat
    message.from_user = test_user
    message.text = "Test message"
    message.bot = mock_bot
    message.reply_to_message = None

    # Add mock methods
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    message.edit_text = AsyncMock()

    return message


@pytest.fixture
def admin_message(mock_bot):
    """Create a mock admin message for testing - FIXED for Pydantic V2."""
    message = MagicMock(spec=Message)
    message.message_id = 2
    message.date = datetime.now()
    message.chat = MagicMock(spec=Chat)
    message.chat.id = int(os.getenv('ADMIN_ID', '123456789'))
    message.chat.type = "private"
    message.from_user = MagicMock(spec=User)
    message.from_user.id = int(os.getenv('ADMIN_ID', '123456789'))
    message.from_user.is_bot = False
    message.from_user.first_name = "Admin"
    message.from_user.username = "admin"
    message.text = "Admin message"
    message.bot = mock_bot
    message.reply_to_message = None
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    message.edit_text = AsyncMock()
    return message


@pytest.fixture
def test_callback(test_user, mock_bot):
    """Create a mock callback query for testing - FIXED for Pydantic V2."""
    callback = MagicMock(spec=CallbackQuery)
    callback.id = "test_callback_id"
    callback.from_user = test_user
    callback.message = MagicMock(spec=Message)
    callback.message.message_id = 3
    callback.message.chat = MagicMock(spec=Chat)
    callback.message.chat.id = 123456789
    callback.message.chat.type = "private"
    callback.message.edit_text = AsyncMock()
    callback.message.edit_reply_markup = AsyncMock()
    callback.message.bot = mock_bot
    callback.data = "test_data"
    callback.answer = AsyncMock()
    return callback

# ==================== DATABASE DATA FIXTURES ====================


@pytest_asyncio.fixture
async def sample_question(clean_db):
    """Create a sample question in the database."""
    question = Question.create_new(
        text="Test question",
        user_id=123456789
    )
    clean_db.add(question)
    await clean_db.commit()
    await clean_db.refresh(question)
    return question


@pytest.fixture
async def sample_user_state(clean_db):
    """Create sample user state."""
    from models.user_states import UserState

    user_state = UserState(
        user_id=123456789,
        state="idle",
        questions_count=0
    )
    clean_db.add(user_state)
    await clean_db.commit()
    await clean_db.refresh(user_state)
    return user_state


@pytest.fixture
async def sample_settings(clean_db):
    """Create sample bot settings."""
    from models.settings import BotSettings

    settings = [
        BotSettings(key="author_name", value="Test Author"),
        BotSettings(key="author_info", value="Test Info")
    ]

    for setting in settings:
        clean_db.add(setting)

    await clean_db.commit()
    return settings

# ==================== ENVIRONMENT SETUP ====================


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("BOT_TOKEN", "test_token:test")
    monkeypatch.setenv("ADMIN_ID", "123456789")
    monkeypatch.setenv("DB_NAME", "test_db")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")  # Reduce log noise in tests

# ==================== MOCK PATCHES ====================


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
def mock_user_state_manager():
    """Create a mock UserStateManager."""
    manager = MagicMock()
    manager.can_send_question = AsyncMock(return_value=True)
    manager.set_user_state = AsyncMock(return_value=True)
    manager.allow_new_question = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_settings_manager():
    """Create a mock SettingsManager."""
    manager = MagicMock()
    manager.get_author_name = AsyncMock(return_value="Test Author")
    manager.get_author_info = AsyncMock(return_value="Test Info")
    return manager


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

# ==================== HELPER FUNCTIONS ====================


def assert_message_sent(mock_bot, chat_id: int, text_contains: str = None):
    """Helper to assert that message was sent."""
    mock_bot.send_message.assert_called()
    call_args = mock_bot.send_message.call_args

    # Handle both positional and keyword arguments
    if call_args[0]:  # positional args
        assert call_args[0][0] == chat_id
        if text_contains and len(call_args[0]) > 1:
            assert text_contains in call_args[0][1]
    else:  # keyword args
        assert call_args[1]['chat_id'] == chat_id
        if text_contains:
            sent_text = call_args[1]['text']
            assert text_contains in sent_text


async def create_test_question(session: AsyncSession, text: str = "Test question", user_id: int = 123456789):
    """Helper to create test question."""
    from models.questions import Question

    question = Question.create_new(text=text, user_id=user_id)
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question

# ==================== TEST DATA FACTORIES ====================


class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_question_data(
        text: str = "Test question",
        user_id: int = 123456789,
        is_answered: bool = False
    ) -> dict:
        """Create question data."""
        data = {
            'text': text,
            'user_id': user_id,
            'is_favorite': False,
            'is_deleted': False
        }

        if is_answered:
            data['answer'] = "Test answer"
            data['answered_at'] = datetime.now()

        return data

    @staticmethod
    def create_user_state_data(
        user_id: int = 123456789,
        state: str = "idle"
    ) -> dict:
        """Create user state data."""
        return {
            'user_id': user_id,
            'state': state,
            'questions_count': 0
        }


@pytest.fixture
def test_data_factory():
    """Provide test data factory."""
    return TestDataFactory
