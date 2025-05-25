"""
Settings Model for Dynamic Bot Configuration

Allows admin to change author name and channel info without restarting bot.
"""

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from typing import Optional

from models.database import Base, async_session


class BotSettings(Base):
    """
    Model for storing dynamic bot settings that admin can edit.
    
    Uses key-value pairs for flexible configuration.
    """
    
    __tablename__ = "bot_settings"

    # Primary key is the setting name
    key = Column(String(100), primary_key=True)
    """Setting name/key (e.g., 'author_name', 'author_info')"""
    
    value = Column(Text, nullable=False)
    """Setting value"""
    
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    """When this setting was last updated"""

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<BotSettings(key='{self.key}', value='{self.value[:50]}...', updated_at='{self.updated_at}')>"


class SettingsManager:
    """Helper class for managing bot settings."""
    
    # Default values
    DEFAULT_SETTINGS = {
        'author_name': 'Автор канала',
        'author_info': 'Здесь можно задать анонимный вопрос'
    }
    
    @staticmethod
    async def get_setting(key: str) -> str:
        """
        Get setting value by key.
        
        Args:
            key: Setting key
            
        Returns:
            str: Setting value or default if not found
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
        Set setting value.
        
        Args:
            key: Setting key
            value: New value
            
        Returns:
            bool: True if successful
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
        """Get current author name."""
        return await SettingsManager.get_setting('author_name')
    
    @staticmethod
    async def get_author_info() -> str:
        """Get current author info."""
        return await SettingsManager.get_setting('author_info')
    
    @staticmethod
    async def set_author_name(name: str) -> bool:
        """Set author name."""
        return await SettingsManager.set_setting('author_name', name.strip())
    
    @staticmethod
    async def set_author_info(info: str) -> bool:
        """Set author info."""
        return await SettingsManager.set_setting('author_info', info.strip())
    
    @staticmethod
    async def get_all_settings() -> dict:
        """
        Get all current settings.
        
        Returns:
            dict: All settings with their values
        """
        settings = {}
        for key in SettingsManager.DEFAULT_SETTINGS.keys():
            settings[key] = await SettingsManager.get_setting(key)
        return settings