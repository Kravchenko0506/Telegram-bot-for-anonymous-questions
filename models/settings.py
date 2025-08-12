"""
Settings Management System

Dynamic configuration system for the Anonymous Questions Bot that handles:
- Bot settings persistence
- Author information management
- Rate limiting configuration
- Question/answer length limits
- Pagination settings
- Database-backed settings storage

"""

from sqlalchemy import Column, String, select
from typing import Optional

from models.database import Base, async_session
from config import (
    DEFAULT_AUTHOR_NAME, 
    DEFAULT_AUTHOR_INFO,
    RATE_LIMIT_QUESTIONS_PER_HOUR,
    RATE_LIMIT_COOLDOWN_SECONDS,
    MAX_QUESTION_LENGTH,
    MAX_ANSWER_LENGTH,
    QUESTIONS_PER_PAGE,
    MAX_PAGES_TO_SHOW
)
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class BotSettings(Base):
    """Database model for bot settings storage."""
    __tablename__ = "bot_settings"

    key = Column(String(100), primary_key=True)
    value = Column(String(1000), nullable=False)

    def __repr__(self) -> str:
        return f"<BotSettings(key='{self.key}', value='{self.value}')>"


class SettingsManager:
    """Comprehensive settings management with database persistence."""

    # Default settings configuration
    DEFAULT_SETTINGS = {
        'author_name': DEFAULT_AUTHOR_NAME,
        'author_info': DEFAULT_AUTHOR_INFO,
        'rate_limit_per_hour': str(RATE_LIMIT_QUESTIONS_PER_HOUR),
        'rate_limit_cooldown': str(RATE_LIMIT_COOLDOWN_SECONDS),
        'max_question_length': str(MAX_QUESTION_LENGTH),
        'max_answer_length': str(MAX_ANSWER_LENGTH),
        'questions_per_page': str(QUESTIONS_PER_PAGE),
        'max_pages_to_show': str(MAX_PAGES_TO_SHOW)
    }

    @staticmethod
    async def get_setting(key: str) -> Optional[str]:
        """Get setting value from database."""
        try:
            async with async_session() as session:
                setting = await session.get(BotSettings, key)
                return setting.value if setting else None
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return None

    @staticmethod
    async def set_setting(key: str, value: str) -> bool:
        """Set setting value in database."""
        try:
            async with async_session() as session:
                setting = await session.get(BotSettings, key)
                if setting:
                    setting.value = value
                else:
                    setting = BotSettings(key=key, value=value)
                    session.add(setting)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False

    # Author settings
    @staticmethod
    async def get_author_name() -> str:
        """Get current author name."""
        value = await SettingsManager.get_setting('author_name')
        return value or DEFAULT_AUTHOR_NAME

    @staticmethod
    async def set_author_name(name: str) -> bool:
        """Set author name."""
        if not name or len(name.strip()) == 0:
            return False
        return await SettingsManager.set_setting('author_name', name.strip())

    @staticmethod
    async def get_author_info() -> str:
        """Get current author info."""
        value = await SettingsManager.get_setting('author_info')
        return value or DEFAULT_AUTHOR_INFO

    @staticmethod
    async def set_author_info(info: str) -> bool:
        """Set author info."""
        if not info or len(info.strip()) == 0:
            return False
        return await SettingsManager.set_setting('author_info', info.strip())

    # Rate limiting settings
    @staticmethod
    async def get_rate_limit_per_hour() -> int:
        """Get questions per hour limit."""
        value = await SettingsManager.get_setting('rate_limit_per_hour')
        try:
            return int(value) if value else RATE_LIMIT_QUESTIONS_PER_HOUR
        except ValueError:
            return RATE_LIMIT_QUESTIONS_PER_HOUR

    @staticmethod
    async def set_rate_limit_per_hour(limit: int) -> bool:
        """Set questions per hour limit."""
        if not (1 <= limit <= 100):
            return False
        return await SettingsManager.set_setting('rate_limit_per_hour', str(limit))

    @staticmethod
    async def get_rate_limit_cooldown() -> int:
        """Get cooldown between questions in seconds."""
        value = await SettingsManager.get_setting('rate_limit_cooldown')
        try:
            return int(value) if value else RATE_LIMIT_COOLDOWN_SECONDS
        except ValueError:
            return RATE_LIMIT_COOLDOWN_SECONDS

    @staticmethod
    async def set_rate_limit_cooldown(seconds: int) -> bool:
        """Set cooldown between questions."""
        if not (0 <= seconds <= 3600):
            return False
        return await SettingsManager.set_setting('rate_limit_cooldown', str(seconds))

    # Question/Answer length settings
    @staticmethod
    async def get_max_question_length() -> int:
        """Get maximum question length."""
        value = await SettingsManager.get_setting('max_question_length')
        try:
            return int(value) if value else MAX_QUESTION_LENGTH
        except ValueError:
            return MAX_QUESTION_LENGTH

    @staticmethod
    async def set_max_question_length(length: int) -> bool:
        """Set maximum question length."""
        if not (10 <= length <= 10000):
            return False
        return await SettingsManager.set_setting('max_question_length', str(length))

    @staticmethod
    async def get_max_answer_length() -> int:
        """Get maximum answer length."""
        value = await SettingsManager.get_setting('max_answer_length')
        try:
            return int(value) if value else MAX_ANSWER_LENGTH
        except ValueError:
            return MAX_ANSWER_LENGTH

    @staticmethod
    async def set_max_answer_length(length: int) -> bool:
        """Set maximum answer length."""
        if not (10 <= length <= 10000):
            return False
        return await SettingsManager.set_setting('max_answer_length', str(length))

    # Pagination settings
    @staticmethod
    async def get_questions_per_page() -> int:
        """Get questions per page for admin interface."""
        value = await SettingsManager.get_setting('questions_per_page')
        try:
            return int(value) if value else QUESTIONS_PER_PAGE
        except ValueError:
            return QUESTIONS_PER_PAGE

    @staticmethod
    async def set_questions_per_page(count: int) -> bool:
        """Set questions per page."""
        if not (1 <= count <= 50):
            return False
        return await SettingsManager.set_setting('questions_per_page', str(count))

    @staticmethod
    async def get_max_pages_to_show() -> int:
        """Get maximum pages to show."""
        value = await SettingsManager.get_setting('max_pages_to_show')
        try:
            return int(value) if value else MAX_PAGES_TO_SHOW
        except ValueError:
            return MAX_PAGES_TO_SHOW

    @staticmethod
    async def set_max_pages_to_show(pages: int) -> bool:
        """Set maximum pages to show."""
        if not (10 <= pages <= 1000):
            return False
        return await SettingsManager.set_setting('max_pages_to_show', str(pages))

    @staticmethod
    async def reset_all_to_defaults() -> bool:
        """Reset all settings to default values."""
        try:
            for key, default_value in SettingsManager.DEFAULT_SETTINGS.items():
                await SettingsManager.set_setting(key, default_value)
            logger.info("All settings reset to defaults")
            return True
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            return False

    @staticmethod
    async def get_all_settings() -> dict:
        """Get all current settings as dictionary."""
        settings = {}
        try:
            for key in SettingsManager.DEFAULT_SETTINGS.keys():
                settings[key] = await SettingsManager.get_setting(key)
            return settings
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
