"""
Settings Management.
Dynamic configuration system.

"""

from sqlalchemy import Column, String
from typing import Optional

from models.database import Base, async_session
from config import (
    DEFAULT_AUTHOR_NAME,
    DEFAULT_AUTHOR_INFO,
    RATE_LIMIT_QUESTIONS_PER_HOUR,
    RATE_LIMIT_COOLDOWN_SECONDS,
    MIN_QUESTION_LENGTH,
    MAX_QUESTION_LENGTH,
    MAX_ANSWER_LENGTH,
    QUESTIONS_PER_PAGE
)
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class BotSettings(Base):
    """Key-value storage for bot settings."""

    __tablename__ = "bot_settings"

    key = Column(String(100), primary_key=True)
    value = Column(String(1000), nullable=False)

    def __repr__(self) -> str:
        return f"<BotSettings(key='{self.key}', value='{self.value}')>"


class SettingsManager:
    """Settings management with database persistence and defaults."""

    DEFAULT_SETTINGS = {
        'author_name': DEFAULT_AUTHOR_NAME,
        'author_info': DEFAULT_AUTHOR_INFO,
        'rate_limit_per_hour': str(RATE_LIMIT_QUESTIONS_PER_HOUR),
        'rate_limit_cooldown': str(RATE_LIMIT_COOLDOWN_SECONDS),
        'min_question_length': str(MIN_QUESTION_LENGTH),
        'max_question_length': str(MAX_QUESTION_LENGTH),
        'max_answer_length': str(MAX_ANSWER_LENGTH),
        'questions_per_page': str(QUESTIONS_PER_PAGE)
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
                    session.add(BotSettings(key=key, value=value))
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False

    @staticmethod
    async def _get_int(key: str, default: int) -> int:
        value = await SettingsManager.get_setting(key)
        try:
            return int(value) if value else default
        except ValueError:
            return default

    @staticmethod
    async def _set_int(key: str, value: int, min_val: int, max_val: int) -> bool:
        if not (min_val <= value <= max_val):
            return False
        return await SettingsManager.set_setting(key, str(value))

    @staticmethod
    async def get_author_name() -> str:
        return await SettingsManager.get_setting('author_name') or DEFAULT_AUTHOR_NAME

    @staticmethod
    async def set_author_name(name: str) -> bool:
        if not name or not name.strip():
            return False
        return await SettingsManager.set_setting('author_name', name.strip())

    @staticmethod
    async def get_author_info() -> str:
        return await SettingsManager.get_setting('author_info') or DEFAULT_AUTHOR_INFO

    @staticmethod
    async def set_author_info(info: str) -> bool:
        if not info or not info.strip():
            return False
        return await SettingsManager.set_setting('author_info', info.strip())

    @staticmethod
    async def get_rate_limit_per_hour() -> int:
        return await SettingsManager._get_int('rate_limit_per_hour', RATE_LIMIT_QUESTIONS_PER_HOUR)

    @staticmethod
    async def set_rate_limit_per_hour(limit: int) -> bool:
        return await SettingsManager._set_int('rate_limit_per_hour', limit, 1, 100)

    @staticmethod
    async def get_rate_limit_cooldown() -> int:
        return await SettingsManager._get_int('rate_limit_cooldown', RATE_LIMIT_COOLDOWN_SECONDS)

    @staticmethod
    async def set_rate_limit_cooldown(seconds: int) -> bool:
        return await SettingsManager._set_int('rate_limit_cooldown', seconds, 0, 3600)

    @staticmethod
    async def get_min_question_length() -> int:
        return await SettingsManager._get_int('min_question_length', MIN_QUESTION_LENGTH)

    @staticmethod
    async def set_min_question_length(length: int) -> bool:
        return await SettingsManager._set_int('min_question_length', length, 1, 100)

    @staticmethod
    async def get_max_question_length() -> int:
        return await SettingsManager._get_int('max_question_length', MAX_QUESTION_LENGTH)

    @staticmethod
    async def set_max_question_length(length: int) -> bool:
        return await SettingsManager._set_int('max_question_length', length, 10, 10000)

    @staticmethod
    async def get_max_answer_length() -> int:
        return await SettingsManager._get_int('max_answer_length', MAX_ANSWER_LENGTH)

    @staticmethod
    async def set_max_answer_length(length: int) -> bool:
        return await SettingsManager._set_int('max_answer_length', length, 10, 10000)

    @staticmethod
    async def get_questions_per_page() -> int:
        return await SettingsManager._get_int('questions_per_page', QUESTIONS_PER_PAGE)

    @staticmethod
    async def set_questions_per_page(count: int) -> bool:
        return await SettingsManager._set_int('questions_per_page', count, 1, 50)

    @staticmethod
    async def reset_all_to_defaults() -> bool:
        """Reset all settings to default values."""
        try:
            for key, value in SettingsManager.DEFAULT_SETTINGS.items():
                await SettingsManager.set_setting(key, value)
            logger.info("All settings reset to defaults")
            return True
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            return False

    @staticmethod
    async def get_all_settings() -> dict:
        """Get all current settings."""
        try:
            return {key: await SettingsManager.get_setting(key)
                    for key in SettingsManager.DEFAULT_SETTINGS}
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
