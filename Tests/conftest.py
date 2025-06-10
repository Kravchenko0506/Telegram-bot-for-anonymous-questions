"""
Central test configuration and fixtures for Anonymous Questions Bot.

Provides shared fixtures, test database setup, and mock configurations.
"""

import pytest
import asyncio
import os
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Database testing
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Bot testing
from aiogram import Bot, Dispatcher
from aiogram.types import User, Chat, Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage

# Project imports
from models.database import Base, async_session
from models.questions import Question
from models.settings import BotSettings
from models.user_states import UserState
from models.admin_state import AdminState
from config import ADMIN_ID


# ==================== PYTEST CONFIGURATION ====================

def pytest_configure(config):
    """Pytest configuration hook."""
    import warnings
    # Suppress specific warnings during testing
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Auto-mark based on file path
        if "test_models" in str(item.fspath):
            item.add_marker(pytest.mark.models)
        elif "test_handlers" in str(item.fspath):
            item.add_marker(pytest.mark.handlers)
        elif "test_utils" in str(item.fspath):
            item.add_marker(pytest.mark.utils)
        elif "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark database tests
        if any(marker.name == 'database' for marker in item.iter_markers()):
            item.add_marker(pytest.mark.database)


# ==================== FIXTURES ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine with in-memory SQLite."""
    # Use in-memory SQLite for fast testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False  # Set True for SQL debugging
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create clean test database session for each test."""
    async_session_factory = async_sessionmaker(
        test_engine, 
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def clean_db(test_session):
    """Ensure clean database state for each test."""
    # Clear all tables
    for table in reversed(Base.metadata.sorted_tables):
        await test_session.execute(table.delete())
    await test_session.commit()
    yield test_session


@pytest.fixture
def mock_bot():
    """Mock Bot instance for testing handlers."""
    bot = AsyncMock(spec=Bot)
    bot.session = AsyncMock()
    bot.get_me.return_value = AsyncMock(
        id=12345,
        is_bot=True,
        first_name="Test Bot",
        username="test_bot"
    )
    return bot


@pytest.fixture
def mock_dispatcher():
    """Mock Dispatcher for testing."""
    dp = MagicMock(spec=Dispatcher)
    dp.storage = MemoryStorage()
    return dp


@pytest.fixture
def test_user():
    """Create test user object."""
    return User(
        id=123456789,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser"
    )


@pytest.fixture
def admin_user():
    """Create admin user object."""
    return User(
        id=ADMIN_ID,
        is_bot=False,
        first_name="Admin",
        username="admin"
    )


@pytest.fixture
def test_chat():
    """Create test chat object."""
    return Chat(
        id=123456789,
        type="private"
    )


@pytest.fixture
def test_message(test_user, test_chat, mock_bot):
    """Create test message object."""
    return Message(
        message_id=1,
        date=datetime.now(),
        chat=test_chat,
        from_user=test_user,
        text="Test message",
        bot=mock_bot
    )


@pytest.fixture
def admin_message(admin_user, test_chat, mock_bot):
    """Create admin message object."""
    return Message(
        message_id=2,
        date=datetime.now(),
        chat=Chat(id=ADMIN_ID, type="private"),
        from_user=admin_user,
        text="Admin message",
        bot=mock_bot
    )


@pytest.fixture
def test_callback(test_user, test_message, mock_bot):
    """Create test callback query."""
    return CallbackQuery(
        id="test_callback",
        from_user=test_user,
        chat_instance="test_instance",
        message=test_message,
        data="test_action:123",
        bot=mock_bot
    )


# ==================== DATABASE FIXTURES ====================

@pytest.fixture
async def sample_question(clean_db) -> Question:
    """Create sample question in database."""
    question = Question.create_new(
        text="Test question text",
        user_id=123456789,
        unique_id="test_channel"
    )
    clean_db.add(question)
    await clean_db.commit()
    await clean_db.refresh(question)
    return question


@pytest.fixture
async def answered_question(clean_db) -> Question:
    """Create answered question in database."""
    question = Question.create_new(
        text="Answered question",
        user_id=123456789
    )
    question.answer = "Test answer"
    question.answered_at = datetime.utcnow()
    
    clean_db.add(question)
    await clean_db.commit()
    await clean_db.refresh(question)
    return question


@pytest.fixture
async def favorite_question(clean_db) -> Question:
    """Create favorite question in database."""
    question = Question.create_new(
        text="Favorite question",
        user_id=123456789
    )
    question.is_favorite = True
    
    clean_db.add(question)
    await clean_db.commit()
    await clean_db.refresh(question)
    return question


@pytest.fixture
async def sample_user_state(clean_db) -> UserState:
    """Create sample user state."""
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
    settings = [
        BotSettings(key="author_name", value="Test Author"),
        BotSettings(key="author_info", value="Test Info")
    ]
    
    for setting in settings:
        clean_db.add(setting)
    
    await clean_db.commit()
    return settings


# ==================== MOCK FIXTURES ====================

@pytest.fixture
def mock_async_session(test_session):
    """Mock async_session to use test database."""
    with patch('models.database.async_session') as mock:
        mock.return_value.__aenter__.return_value = test_session
        mock.return_value.__aexit__.return_value = None
        yield mock


@pytest.fixture
def mock_logger():
    """Mock logger to prevent log spam during tests."""
    with patch('utils.logger.get_bot_logger') as mock_bot_logger, \
         patch('utils.logger.get_admin_logger') as mock_admin_logger, \
         patch('utils.logger.get_question_logger') as mock_question_logger:
        
        # Create mock loggers
        bot_logger = MagicMock()
        admin_logger = MagicMock()
        question_logger = MagicMock()
        
        mock_bot_logger.return_value = bot_logger
        mock_admin_logger.return_value = admin_logger
        mock_question_logger.return_value = question_logger
        
        yield {
            'bot': bot_logger,
            'admin': admin_logger,
            'question': question_logger
        }


@pytest.fixture
def freeze_time():
    """Freeze time for consistent testing."""
    test_time = datetime(2024, 1, 1, 12, 0, 0)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = test_time
        mock_datetime.now.return_value = test_time
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield test_time


# ==================== HELPER FIXTURES ====================

@pytest.fixture
def test_config():
    """Test configuration values."""
    return {
        'BOT_TOKEN': 'test_token:test',
        'ADMIN_ID': ADMIN_ID,
        'DB_NAME': 'test_db',
        'MAX_QUESTION_LENGTH': 1000,
        'RATE_LIMIT_QUESTIONS_PER_HOUR': 5
    }


@pytest.fixture
async def multiple_questions(clean_db):
    """Create multiple questions for pagination testing."""
    questions = []
    for i in range(15):  # More than default page size
        question = Question.create_new(
            text=f"Question {i+1}",
            user_id=123456789 + i
        )
        if i % 3 == 0:  # Every 3rd is favorite
            question.is_favorite = True
        if i % 4 == 0:  # Every 4th is answered
            question.answer = f"Answer {i+1}"
            question.answered_at = datetime.utcnow()
        
        clean_db.add(question)
        questions.append(question)
    
    await clean_db.commit()
    return questions


# ==================== MARKS ====================

# Define custom marks for easy test selection
pytestmark = [
    pytest.mark.asyncio,  # All tests are async by default
]


# ==================== ENVIRONMENT SETUP ====================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("BOT_TOKEN", "test_token:test")
    monkeypatch.setenv("ADMIN_ID", str(ADMIN_ID))
    monkeypatch.setenv("DB_NAME", "test_db")


# ==================== UTILITY FUNCTIONS ====================

def create_mock_update(user_id: int = 123456789, text: str = "test", **kwargs):
    """Helper to create mock update objects."""
    return {
        'update_id': 1,
        'message': {
            'message_id': 1,
            'date': datetime.now().timestamp(),
            'chat': {'id': user_id, 'type': 'private'},
            'from': {'id': user_id, 'is_bot': False, 'first_name': 'Test'},
            'text': text,
            **kwargs
        }
    }


def assert_message_sent(mock_bot, chat_id: int, text_contains: str = None):
    """Helper to assert that message was sent."""
    mock_bot.send_message.assert_called()
    call_args = mock_bot.send_message.call_args
    
    assert call_args[1]['chat_id'] == chat_id
    
    if text_contains:
        sent_text = call_args[1]['text']
        assert text_contains in sent_text, f"'{text_contains}' not found in '{sent_text}'"


# ==================== ASYNC HELPERS ====================

async def run_handler_test(handler, event, **kwargs):
    """Helper to run handler tests with proper mocking."""
    try:
        result = await handler(event, **kwargs)
        return result
    except Exception as e:
        pytest.fail(f"Handler raised exception: {e}")


# ==================== TEST DATA FACTORIES ====================

class QuestionFactory:
    """Factory for creating test questions."""
    
    @staticmethod
    def create(**kwargs):
        defaults = {
            'text': 'Test question',
            'user_id': 123456789,
            'unique_id': None
        }
        defaults.update(kwargs)
        return Question.create_new(**defaults)


class UserStateFactory:
    """Factory for creating test user states."""
    
    @staticmethod
    def create(**kwargs):
        defaults = {
            'user_id': 123456789,
            'state': 'idle',
            'questions_count': 0
        }
        defaults.update(kwargs)
        return UserState(**defaults)