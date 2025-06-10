"""
Fixed test configuration - solves Pydantic frozen instance issue.

Key fix: Use unittest.mock.create_autospec instead of trying to modify frozen objects.
"""

import pytest
import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch, create_autospec
from datetime import datetime

# Database testing
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Bot testing  
from aiogram import Bot
from aiogram.types import User, Chat, Message, CallbackQuery


# ==================== PYTEST CONFIGURATION ====================

def pytest_configure(config):
    """Pytest configuration hook."""
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== DATABASE FIXTURES ====================

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine with in-memory SQLite."""
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
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def clean_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create clean test database session for each test."""
    async_session_factory = async_sessionmaker(
        test_engine, 
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_factory() as session:
        # Clear all tables before test
        from models.database import Base
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
        
        yield session
        
        # Clean up after test  
        try:
            await session.rollback()
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
            await session.commit()
        except Exception:
            pass


# ==================== BOT FIXTURES ====================

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
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def test_user():
    """Create test user object."""
    return User(
        id=123456789,
        is_bot=False,
        first_name="Test",
        username="testuser"
    )


@pytest.fixture  
def admin_user():
    """Create admin user object."""
    admin_id = int(os.getenv('ADMIN_ID', '123456789'))
    return User(
        id=admin_id,
        is_bot=False,
        first_name="Admin", 
        username="admin"
    )


@pytest.fixture
def test_chat():
    """Create test chat object."""
    return Chat(id=123456789, type="private")


@pytest.fixture
def admin_chat():
    """Create admin chat object."""
    admin_id = int(os.getenv('ADMIN_ID', '123456789'))
    return Chat(id=admin_id, type="private")


@pytest.fixture
def test_message(test_user, test_chat, mock_bot):
    """Create test message object - FIXED for Pydantic frozen instances."""
    # Create a mock that behaves like Message but allows attribute assignment
    message = create_autospec(Message, instance=True)
    
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
def admin_message(admin_user, admin_chat, mock_bot):
    """Create admin message object - FIXED for Pydantic frozen instances."""
    # Create a mock that behaves like Message but allows attribute assignment
    message = create_autospec(Message, instance=True)
    
    # Set the required attributes
    message.message_id = 2
    message.date = datetime.now()
    message.chat = admin_chat
    message.from_user = admin_user
    message.text = "Admin message"
    message.bot = mock_bot
    message.reply_to_message = None
    
    # Add mock methods
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    message.edit_text = AsyncMock()
    
    return message


@pytest.fixture
def test_callback(test_user, test_message, mock_bot):
    """Create test callback query - FIXED for Pydantic frozen instances."""
    # Create a mock that behaves like CallbackQuery but allows attribute assignment
    callback = create_autospec(CallbackQuery, instance=True)
    
    # Set the required attributes
    callback.id = "test_callback"
    callback.from_user = test_user
    callback.chat_instance = "test_instance"
    callback.message = test_message
    callback.data = "test_action:123"
    callback.bot = mock_bot
    
    # Add mock methods
    callback.answer = AsyncMock()
    
    # Fix message methods for callback
    callback.message.edit_text = AsyncMock()
    callback.message.edit_reply_markup = AsyncMock()
    callback.message.reply = AsyncMock()
    
    return callback


# ==================== DATABASE DATA FIXTURES ====================

@pytest.fixture
async def sample_question(clean_db):
    """Create sample question in database."""
    from models.questions import Question
    
    question = Question.create_new(
        text="Test question text",
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
    """Mock async session for database operations."""
    with patch('models.database.async_session') as mock_session:
        # Create proper structure for async context manager
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        mock_session.return_value.__aexit__.return_value = None
        yield mock_session


@pytest.fixture  
def mock_user_state_manager():
    """Mock UserStateManager for handler tests."""
    with patch('models.user_states.UserStateManager') as mock_manager:
        # Set up common return values as coroutines
        mock_manager.can_send_question = AsyncMock(return_value=True)
        mock_manager.set_user_state = AsyncMock(return_value=True)
        mock_manager.reset_to_idle = AsyncMock(return_value=True)
        mock_manager.allow_new_question = AsyncMock(return_value=True)
        
        # Add state constants
        mock_manager.STATE_IDLE = "idle"
        mock_manager.STATE_QUESTION_SENT = "question_sent"
        mock_manager.STATE_AWAITING_QUESTION = "awaiting_question"
        
        yield mock_manager


@pytest.fixture
def mock_settings_manager():
    """Mock SettingsManager for tests."""
    with patch('models.settings.SettingsManager') as mock_manager:
        mock_manager.get_author_name = AsyncMock(return_value="Test Author")
        mock_manager.get_author_info = AsyncMock(return_value="Test Info")
        mock_manager.set_author_name = AsyncMock(return_value=True)
        mock_manager.set_author_info = AsyncMock(return_value=True)
        yield mock_manager


@pytest.fixture
def mock_input_validator():
    """Mock InputValidator for tests."""
    with patch('utils.validators.InputValidator') as mock_validator:
        # Static methods mock properly
        mock_validator.sanitize_text.side_effect = lambda x, max_length=None: x.strip() if x else ""
        mock_validator.validate_question.return_value = (True, None)
        mock_validator.validate_answer.return_value = (True, None)
        mock_validator.extract_personal_data.return_value = {
            'emails': [], 'phones': [], 'urls': []
        }
        yield mock_validator


@pytest.fixture
def mock_content_moderator():
    """Mock ContentModerator for tests."""
    with patch('utils.validators.ContentModerator') as mock_moderator:
        mock_moderator.is_likely_spam.return_value = False
        mock_moderator.calculate_spam_score.return_value = 0.0
        yield mock_moderator


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