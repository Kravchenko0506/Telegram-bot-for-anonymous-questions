"""
Configuration Module for Anonymous Questions Bot

Updated configuration with dynamic settings support.
Author name and info are now editable by admin through bot commands.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_env_var(key: str, default: Optional[str] = None, required: bool = True) -> str:
    """
    Get environment variable with validation.
    
    Args:
        key (str): Environment variable name
        default (Optional[str]): Default value if variable not found
        required (bool): Whether the variable is required
        
    Returns:
        str: Environment variable value
        
    Raises:
        ValueError: If required variable is not found
    """
    value = os.getenv(key, default)
    
    if required and not value:
        raise ValueError(
            f"Required environment variable '{key}' not found. "
            f"Please set it in your .env file or environment."
        )
    
    return value


# Bot Configuration
TOKEN: str = get_env_var("BOT_TOKEN")
"""Telegram Bot API token from @BotFather"""

ADMIN_ID: int = int(get_env_var("ADMIN_ID"))
"""Telegram user ID of the bot administrator"""

# Database Configuration (PostgreSQL)
DB_USER: str = get_env_var("DB_USER", default="botanon", required=False)
"""PostgreSQL username"""

DB_PASSWORD: str = get_env_var("DB_PASSWORD", default="BotDB25052025", required=False)
"""PostgreSQL password"""

DB_HOST: str = get_env_var("DB_HOST", default="127.0.0.1", required=False)
"""PostgreSQL host address"""

DB_PORT: str = get_env_var("DB_PORT", default="5432", required=False)
"""PostgreSQL port"""

DB_NAME: str = get_env_var("DB_NAME", default="dbfrombot", required=False)
"""PostgreSQL database name"""

# Bot Settings
MAX_QUESTION_LENGTH: int = 1000
"""Maximum length of a question in characters"""

MAX_ANSWER_LENGTH: int = 2000
"""Maximum length of an answer in characters"""

BOT_USERNAME: str = get_env_var("BOT_USERNAME", default="YourBot", required=False)
"""Bot username for generating links"""

# Dynamic settings (now managed through database)
# These are default values, actual values are fetched from BotSettings table

DEFAULT_AUTHOR_NAME: str = "Автор канала"
"""Default author name (can be changed by admin)"""

DEFAULT_AUTHOR_INFO: str = "Здесь можно задать анонимный вопрос"
"""Default author info (can be changed by admin)"""

# Message Templates (now use dynamic settings)
WELCOME_MESSAGE_TEMPLATE: str = """
👋 <b>Привет! Ты можешь анонимно задать свой вопрос автору.</b>

ℹ️ <b>Автор:</b> {author_name}
📝 <b>О канале:</b> {author_info}

✍️ Просто напиши свой вопрос в ответном сообщении.

<i>Максимальная длина вопроса: {max_length} символов</i>
"""

# Success Messages
SUCCESS_QUESTION_SENT: str = "✅ Ваш вопрос отправлен автору анонимно!"
SUCCESS_ANSWER_SENT: str = "✅ Ответ отправлен пользователю!"
SUCCESS_ADDED_TO_FAVORITES: str = "⭐ Вопрос добавлен в избранное!"
SUCCESS_REMOVED_FROM_FAVORITES: str = "⭐ Вопрос убран из избранного!"
SUCCESS_QUESTION_DELETED: str = "🗑️ Вопрос удален!"
SUCCESS_SETTING_UPDATED: str = "✅ Настройка обновлена!"

# Error Messages
ERROR_MESSAGE_TOO_LONG: str = f"❌ Вопрос слишком длинный. Максимум {MAX_QUESTION_LENGTH} символов."
ERROR_MESSAGE_EMPTY: str = "❌ Пустое сообщение не может быть отправлено как вопрос."
ERROR_ADMIN_ONLY: str = "❌ Эта команда доступна только администратору."
ERROR_DATABASE: str = "❌ Произошла ошибка при работе с базой данных. Попробуйте позже."
ERROR_QUESTION_NOT_FOUND: str = "❌ Вопрос не найден или уже удален."
ERROR_ALREADY_ANSWERED: str = "❌ На этот вопрос уже был дан ответ."
ERROR_SETTING_UPDATE: str = "❌ Ошибка при обновлении настройки."
ERROR_INVALID_VALUE: str = "❌ Некорректное значение."

# Admin Messages
ADMIN_NEW_QUESTION: str = """
❓ <b>Новый анонимный вопрос #{question_id}:</b>

{question_text}

<i>Отправлено: {created_at}</i>
"""

ADMIN_NO_PENDING_QUESTIONS: str = "📭 Нет неотвеченных вопросов."
ADMIN_NO_FAVORITES: str = "⭐ Нет избранных вопросов."

# User Messages  
USER_ANSWER_RECEIVED: str = """
💬 <b>Получен ответ на ваш вопрос:</b>

<b>Ваш вопрос:</b>
<i>{question}</i>

<b>Ответ:</b>
{answer}
"""

USER_QUESTION_PROCESSING: str = "⏳ Ваш вопрос отправлен и ожидает ответа..."


def get_bot_link(unique_id: str) -> str:
    """
    Generate bot link with unique start parameter.
    
    Args:
        unique_id: Unique identifier for tracking
        
    Returns:
        str: Complete bot link
    """
    return f"https://t.me/{BOT_USERNAME}?start={unique_id}"


def validate_config() -> bool:
    """
    Validate all required configuration parameters.
    
    Returns:
        bool: True if all required parameters are valid
        
    Raises:
        ValueError: If any required parameter is invalid
    """
    try:
        # Check if TOKEN is valid (basic format check)
        if not TOKEN or len(TOKEN.split(':')) != 2:
            raise ValueError("Invalid BOT_TOKEN format")
        
        # Check if ADMIN_ID is valid
        if ADMIN_ID <= 0:
            raise ValueError("ADMIN_ID must be a positive integer")
        
        # Check database configuration
        if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
            raise ValueError("Database configuration incomplete")
        
        # Validate numeric values
        if MAX_QUESTION_LENGTH <= 0 or MAX_ANSWER_LENGTH <= 0:
            raise ValueError("Message length limits must be positive")
            
        return True
        
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


# Initialize validation on import
if __name__ != "__main__":
    validate_config()