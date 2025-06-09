"""
Configuration Module for Anonymous Questions Bot

"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


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
            f"Please set it in your .env file or environment. "
            f"See .env.example for reference."
        )
    
    return value


def get_env_int(key: str, default: Optional[int] = None, required: bool = True) -> int:
    """Get environment variable as integer."""
    value = get_env_var(key, str(default) if default is not None else None, required)
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable '{key}' must be an integer")


# Bot Configuration - REQUIRED
TOKEN: str = get_env_var("BOT_TOKEN")
"""Telegram Bot API token from @BotFather"""

ADMIN_ID: int = get_env_int("ADMIN_ID")
"""Telegram user ID of the bot administrator"""

BOT_USERNAME: str = get_env_var("BOT_USERNAME")
"""Bot username for generating links (without @)"""

# Database Configuration - REQUIRED
DB_USER: str = get_env_var("DB_USER")
"""PostgreSQL username"""

DB_PASSWORD: str = get_env_var("DB_PASSWORD")
"""PostgreSQL password - NEVER commit real passwords!"""

DB_HOST: str = get_env_var("DB_HOST")
"""PostgreSQL host address"""

DB_PORT: str = get_env_var("DB_PORT")
"""PostgreSQL port"""

DB_NAME: str = get_env_var("DB_NAME")
"""PostgreSQL database name"""

# Bot Settings - OPTIONAL with safe defaults
MAX_QUESTION_LENGTH: int = get_env_int("MAX_QUESTION_LENGTH", default=1000, required=False)
"""Maximum length of a question in characters"""

MAX_ANSWER_LENGTH: int = get_env_int("MAX_ANSWER_LENGTH", default=2000, required=False)
"""Maximum length of an answer in characters"""

# Logging Configuration
LOG_LEVEL: str = get_env_var("LOG_LEVEL", default="INFO", required=False)
"""Logging level: DEBUG, INFO, WARNING, ERROR"""

# Security Settings
RATE_LIMIT_QUESTIONS_PER_HOUR: int = get_env_int("RATE_LIMIT_QUESTIONS_PER_HOUR", default=5, required=False)
"""Maximum questions per hour from one user"""

RATE_LIMIT_COOLDOWN_SECONDS: int = get_env_int("RATE_LIMIT_COOLDOWN_SECONDS", default=30, required=False)
"""Minimum seconds between questions from same user"""

# Optional: External Services
SENTRY_DSN: Optional[str] = get_env_var("SENTRY_DSN", default=None, required=False)
"""Sentry DSN for error tracking (optional)"""

# Dynamic settings defaults (stored in database)
DEFAULT_AUTHOR_NAME: str = "Автор канала"
"""Default author name (can be changed by admin)"""

DEFAULT_AUTHOR_INFO: str = "Здесь можно задать анонимный вопрос"
"""Default author info (can be changed by admin)"""

# Message Templates
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
# Error Messages with rate limit placeholder
ERROR_RATE_LIMIT: str = "❌ Слишком часто отправляете вопросы. Попробуйте через {seconds} секунд."

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
    errors = []
    
    # Check if TOKEN is valid (basic format check)
    if not TOKEN or len(TOKEN.split(':')) != 2:
        errors.append("Invalid BOT_TOKEN format")
    
    # Check if ADMIN_ID is valid
    if ADMIN_ID <= 0:
        errors.append("ADMIN_ID must be a positive integer")
    
    # Check database configuration
    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
        errors.append("Database configuration incomplete")
    
    # Validate numeric values
    if MAX_QUESTION_LENGTH <= 0 or MAX_ANSWER_LENGTH <= 0:
        errors.append("Message length limits must be positive")
    
    # Validate rate limits
    if RATE_LIMIT_QUESTIONS_PER_HOUR <= 0:
        errors.append("Rate limit must be positive")
    
    if RATE_LIMIT_COOLDOWN_SECONDS <= 0:
        errors.append("Cooldown must be positive")
    
    if errors:
        error_message = "Configuration validation failed:\n" + "\n".join(f"- {e}" for e in errors)
        raise ValueError(error_message)
    
    return True


# Initialize validation on import
if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(f"❌ Configuration Error:\n{e}")
        print("\n📋 Please check your .env file and ensure all required variables are set.")
        print("See .env.example for reference.")
        raise