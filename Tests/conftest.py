"""
Simplified test configuration for production-critical tests.

Provides essential fixtures for database, bot mocking, and basic test data.
"""

import pytest
import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Database testing
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Bot testing
from aiogram import Bot
from aiogram.types import User, Chat, Message, CallbackQuery

# Project imports
from models.database import Base
from models.questions import Question
from models.user_states import UserState
from models.settings import BotSettings
from config import ADMIN_ID


# ==================== PYTEST CONFIGURATION ====================

def pytest_configure(config):
    """Pytest configuration hook."""
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)


# ==================== CORE FIXTURES ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine with in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
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
        # Clear all tables
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
        yield session


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


# ==================== USER FIXTURES ====================

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
    return User(
        id=ADMIN_ID,
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
    return Chat(id=ADMIN_ID, type="private")


# ==================== MESSAGE FIXTURES ====================

@pytest.fixture
def test_message(test_user, test_chat, mock_bot):
    """Create test message object."""
    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=test_chat,
        from_user=test_user,
        text="Test message",
        bot=mock_bot
    )
    message.answer = AsyncMock()
    return message


@pytest.fixture
def admin_message(admin_user, admin_chat, mock_bot):
    """Create admin message object."""
    message = Message(
        message_id=2,
        date=datetime.now(),
        chat=admin_chat,
        from_user=admin_user,
        text="Admin message",
        bot=mock_bot
    )
    message.answer = AsyncMock()
    return message


@pytest.fixture
def test_callback(test_user, test_message, mock_bot):
    """Create test callback query."""
    callback = CallbackQuery(
        id="test_callback",
        from_user=test_user,
        chat_instance="test_instance",
        message=test_message,
        data="test_action:123",
        bot=mock_bot
    )
    callback.answer = AsyncMock()
    return callback


# ==================== DATABASE DATA FIXTURES ====================

@pytest.fixture
async def sample_question(clean_db) -> Question:
    """Create sample question in database."""
    question = Question.create_new(
        text="Test question text",
        user_id=123456789
    )
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


# ==================== ENVIRONMENT SETUP ====================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("BOT_TOKEN", "test_token:test")
    monkeypatch.setenv("ADMIN_ID", str(ADMIN_ID))
    monkeypatch.setenv("DB_NAME", "test_db")


# ==================== HELPER FUNCTIONS ====================

def assert_message_sent(mock_bot, chat_id: int, text_contains: str = None):
    """Helper to assert that message was sent."""
    mock_bot.send_message.assert_called()
    call_args = mock_bot.send_message.call_args
    
    assert call_args[1]['chat_id'] == chat_id
    
    if text_contains:
        sent_text = call_args[1]['text']
        assert text_contains in sent_text


async def create_test_question(session: AsyncSession, text: str = "Test question", user_id: int = 123456789) -> Question:
    """Helper to create test question."""
    question = Question.create_new(text=text, user_id=user_id)
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question