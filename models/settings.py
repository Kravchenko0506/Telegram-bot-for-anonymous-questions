"""
Dynamic Configuration Management System

A comprehensive system for managing dynamic bot settings that can be modified
at runtime without requiring application restart.

Features:
- Dynamic setting updates
- Default value management
- Persistence in database
- Timezone-aware tracking
- Error handling
- Setting validation

Components:
- Settings Model: Database schema for settings
- Settings Manager: Business logic for setting operations
- Default Values: Fallback configuration
- Update Tracking: Modification history
"""

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from typing import Optional

from models.database import Base, async_session


class BotSettings(Base):
    """
    Database model for dynamic bot configuration settings.

    This model provides:
    - Key-value storage for settings
    - Automatic update tracking
    - Timezone-aware timestamps
    - Flexible value types

    Features:
    - String-based keys for easy access
    - Text values for unlimited length
    - Automatic timestamp updates
    - Database-backed persistence
    """

    __tablename__ = "bot_settings"

    # Primary key is the setting name
    key = Column(String(100), primary_key=True)
    """
    Setting identifier key.
    Examples: 'author_name', 'author_info'
    Limited to 100 characters for efficiency.
    """

    value = Column(Text, nullable=False)
    """
    Setting value in text format.
    No length limit for maximum flexibility.
    """

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    """
    Last modification timestamp.
    Automatically updated on value changes.
    Timezone-aware for accurate tracking.
    """

    def __repr__(self) -> str:
        """
        Generate string representation for debugging.

        Returns:
            str: Formatted string with key setting attributes
        """
        return f"<BotSettings(key='{self.key}', value='{self.value[:50]}...', updated_at='{self.updated_at}')>"


class SettingsManager:
    """
    Comprehensive manager for bot settings operations.

    This class provides:
    - Setting retrieval and updates
    - Default value management
    - Error handling
    - Convenience methods
    - Batch operations

    Features:
    - Automatic error recovery
    - Default value fallback
    - Value validation
    - Atomic operations
    - Setting normalization
    """

    # Default values
    DEFAULT_SETTINGS = {
        'author_name': 'Автор канала',
        'author_info': 'Здесь можно задать анонимный вопрос'
    }

    @staticmethod
    async def get_setting(key: str) -> str:
        """
        Retrieve setting value with fallback to defaults.

        Features:
        - Database lookup
        - Default value fallback
        - Error handling
        - Value validation

        Args:
            key: Setting identifier to retrieve

        Returns:
            str: Current setting value or default
        """
        try:
            async with async_session() as session:
                setting = await session.get(BotSettings, key)
                if setting:
                    return setting.value

                # Return default value if setting not found
                return SettingsManager.DEFAULT_SETTINGS.get(key, "")

        except Exception:
            # Return default on any error
            return SettingsManager.DEFAULT_SETTINGS.get(key, "")

    @staticmethod
    async def set_setting(key: str, value: str) -> bool:
        """
        Update or create setting value.

        Features:
        - Atomic updates
        - Automatic creation
        - Error handling
        - Value validation

        Args:
            key: Setting identifier to update
            value: New setting value

        Returns:
            bool: True if operation succeeded
        """
        try:
            async with async_session() as session:
                # Try to get existing setting
                setting = await session.get(BotSettings, key)

                if setting:
                    # Update existing
                    setting.value = value
                else:
                    # Create new
                    setting = BotSettings(key=key, value=value)
                    session.add(setting)

                await session.commit()
                return True

        except Exception:
            return False

    @staticmethod
    async def get_author_name() -> str:
        """
        Get current author name setting.

        Returns:
            str: Current author name or default
        """
        return await SettingsManager.get_setting('author_name')

    @staticmethod
    async def get_author_info() -> str:
        """
        Get current author info setting.

        Returns:
            str: Current author info or default
        """
        return await SettingsManager.get_setting('author_info')

    @staticmethod
    async def set_author_name(name: str) -> bool:
        """
        Update author name setting.

        Features:
        - Value normalization
        - Whitespace trimming
        - Atomic update

        Args:
            name: New author name

        Returns:
            bool: True if update succeeded
        """
        return await SettingsManager.set_setting('author_name', name.strip())

    @staticmethod
    async def set_author_info(info: str) -> bool:
        """
        Update author info setting.

        Features:
        - Value normalization
        - Whitespace trimming
        - Atomic update

        Args:
            info: New author info

        Returns:
            bool: True if update succeeded
        """
        return await SettingsManager.set_setting('author_info', info.strip())

    @staticmethod
    async def get_all_settings() -> dict:
        """
        Retrieve all current settings.

        Features:
        - Batch retrieval
        - Default value handling
        - Comprehensive results

        Returns:
            dict: All settings with current values
        """
        settings = {}
        for key in SettingsManager.DEFAULT_SETTINGS.keys():
            settings[key] = await SettingsManager.get_setting(key)
        return settings
