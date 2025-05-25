"""
Configuration Module for Anonymous Questions Bot

Этот модуль содержит все конфигурационные параметры бота.
Загружает настройки из переменных окружения для безопасности
и содержит константы, используемые по всему приложению.

Security Note:
- Токены и чувствительные данные должны храниться в .env файле
- Никогда не коммитьте токены в репозиторий
- Используйте переменные окружения в продакшене
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

# Database Configuration
DB_PATH: str = get_env_var("DB_PATH", default="database/questions.db", required=False)
"""Path to SQLite database file"""

# Bot Settings
MAX_QUESTION_LENGTH: int = 1000
"""Maximum length of a question in characters"""

MAX_ANSWER_LENGTH: int = 2000
"""Maximum length of an answer in characters"""

# Message Templates
WELCOME_MESSAGE: str = """
🤖 <b>Добро пожаловать в бот анонимных вопросов!</b>

Здесь вы можете задать любой вопрос анонимно.
Просто напишите свой вопрос, и администратор получит его без информации о вас.

<i>Отправьте любое сообщение, чтобы задать вопрос.</i>
"""

HELP_MESSAGE: str = """
🆘 <b>Помощь по использованию бота</b>

<b>Для пользователей:</b>
• Просто напишите ваш вопрос
• Вопрос будет отправлен анонимно
• Ответ придет в этот же чат

<b>Команды:</b>
/start - Начать работу с ботом
/help - Показать это сообщение

<i>Максимальная длина вопроса: {max_length} символов</i>
""".format(max_length=MAX_QUESTION_LENGTH)

ADMIN_HELP_MESSAGE: str = """
🛠 <b>Админ-панель</b>

<b>Доступные команды:</b>
/admin - Показать админ-панель
/stats - Статистика вопросов
/export - Экспорт всех вопросов

<b>Работа с вопросами:</b>
• Отвечайте на вопросы через Reply
• Используйте кнопки для управления вопросами
"""

# Error Messages
ERROR_MESSAGE_TOO_LONG: str = f"❌ Вопрос слишком длинный. Максимум {MAX_QUESTION_LENGTH} символов."
ERROR_MESSAGE_EMPTY: str = "❌ Пустое сообщение не может быть отправлено как вопрос."
ERROR_ADMIN_ONLY: str = "❌ Эта команда доступна только администратору."
ERROR_DATABASE: str = "❌ Произошла ошибка при работе с базой данных."

# Success Messages
SUCCESS_QUESTION_SENT: str = "✅ Ваш вопрос отправлен администратору анонимно!"
SUCCESS_ANSWER_SENT: str = "✅ Ответ отправлен пользователю!"


# Validation Functions
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
        
        # Check database path
        if not DB_PATH:
            raise ValueError("DB_PATH cannot be empty")
        
        return True
        
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


# Initialize validation on import
if __name__ != "__main__":
    validate_config()