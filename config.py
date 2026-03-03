"""Bot configuration from environment variables."""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv(override=True)


def get_env_var(key: str, default: Optional[str] = None, required: bool = True) -> str:
    """Get environment variable with validation."""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Required environment variable '{key}' not found.")
    return value or ""


def get_env_int(key: str, default: Optional[int] = None, required: bool = True) -> int:
    """Get integer environment variable."""
    value = get_env_var(key, str(default) if default is not None else None, required)

    try:
        return int(value)
    except ValueError:
        raise ValueError(
            f"Environment variable '{key}' must be an integer, got: '{value}'"
        )


# Bot Configuration - REQUIRED
TOKEN: str = get_env_var("BOT_TOKEN")
ADMIN_ID: int = get_env_int("ADMIN_ID")
BOT_USERNAME: str = get_env_var("BOT_USERNAME")

# Pagination
QUESTIONS_PER_PAGE: int = get_env_int("QUESTIONS_PER_PAGE", default=5, required=False)

# Admin Interface
ADMIN_AUTO_REFRESH: bool = (
    get_env_var("ADMIN_AUTO_REFRESH", default="false", required=False).lower() == "true"
)
SHOW_QUESTION_PREVIEW_LENGTH: int = get_env_int(
    "SHOW_QUESTION_PREVIEW_LENGTH", default=200, required=False
)

# Message limits
MIN_QUESTION_LENGTH: int = get_env_int("MIN_QUESTION_LENGTH", default=5, required=False)
MAX_QUESTION_LENGTH: int = get_env_int(
    "MAX_QUESTION_LENGTH", default=2500, required=False
)
MAX_ANSWER_LENGTH: int = get_env_int("MAX_ANSWER_LENGTH", default=6000, required=False)

# Logging
LOG_LEVEL: str = get_env_var("LOG_LEVEL", default="INFO", required=False).upper()
LOG_FORMAT: str = get_env_var(
    "LOG_FORMAT",
    default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    required=False,
)
LOG_TO_FILE: bool = (
    get_env_var("LOG_TO_FILE", default="true", required=False).lower() == "true"
)
LOG_FILE_PATH: str = get_env_var(
    "LOG_FILE_PATH", default="/data/bot.log", required=False
)
LOG_MAX_SIZE_MB: int = get_env_int("LOG_MAX_SIZE_MB", default=10, required=False)
LOG_BACKUP_COUNT: int = get_env_int("LOG_BACKUP_COUNT", default=5, required=False)

# Rate limiting
RATE_LIMIT_QUESTIONS_PER_HOUR: int = get_env_int(
    "RATE_LIMIT_QUESTIONS_PER_HOUR", default=500, required=False
)
RATE_LIMIT_COOLDOWN_SECONDS: int = get_env_int(
    "RATE_LIMIT_COOLDOWN_SECONDS", default=5, required=False
)

# Sentry Configuration
SENTRY_DSN: Optional[str] = get_env_var("SENTRY_DSN", default=None, required=False)
SENTRY_ENVIRONMENT: str = get_env_var(
    "SENTRY_ENVIRONMENT", default="production", required=False
)
SENTRY_RELEASE: Optional[str] = get_env_var(
    "SENTRY_RELEASE", default=None, required=False
)
SENTRY_SAMPLE_RATE: float = float(
    get_env_var("SENTRY_SAMPLE_RATE", default="1.0", required=False)
)
SENTRY_TRACES_SAMPLE_RATE: float = float(
    get_env_var("SENTRY_TRACES_SAMPLE_RATE", default="0.1", required=False)
)
ENABLE_PERFORMANCE_MONITORING: bool = (
    get_env_var(
        "ENABLE_PERFORMANCE_MONITORING", default="false", required=False
    ).lower()
    == "true"
)

# Debug
DEBUG_MODE: bool = (
    get_env_var("DEBUG_MODE", default="false", required=False).lower() == "true"
)
VERBOSE_DATABASE_LOGS: bool = (
    get_env_var("VERBOSE_DATABASE_LOGS", default="false", required=False).lower()
    == "true"
)

# Validation
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
if LOG_LEVEL not in VALID_LOG_LEVELS:
    raise ValueError(
        f"Invalid LOG_LEVEL '{LOG_LEVEL}'. Must be one of: {VALID_LOG_LEVELS}"
    )
if not 0.0 <= SENTRY_SAMPLE_RATE <= 1.0:
    raise ValueError("SENTRY_SAMPLE_RATE must be between 0.0 and 1.0")
if not 0.0 <= SENTRY_TRACES_SAMPLE_RATE <= 1.0:
    raise ValueError("SENTRY_TRACES_SAMPLE_RATE must be between 0.0 and 1.0")

# Dynamic settings defaults
DEFAULT_AUTHOR_NAME: str = "Автор канала"
DEFAULT_AUTHOR_INFO: str = "Здесь можно задать анонимный вопрос"

# Message Templates
WELCOME_MESSAGE_TEMPLATE: str = """
👋 <b>Привет! Вы можете анонимно задать свой вопрос автору.</b>

ℹ️ <b>Автор:</b> {author_name}
📝 <b>О канале:</b> {author_info}

✍️ Просто напишите свой вопрос в ответном сообщении.

<i>Минимальная длина вопроса: {min_length} символов</i>
<i>Максимальная длина вопроса: {max_length} символов</i>
"""

# Success Messages
SUCCESS_QUESTION_SENT: str = "✅ Ваш вопрос отправлен автору анонимно!"
SUCCESS_ANSWER_SENT: str = "✅ Ответ отправлен пользователю!"
SUCCESS_ADDED_TO_FAVORITES: str = "⭐ Вопрос добавлен в избранное!"
SUCCESS_REMOVED_FROM_FAVORITES: str = "⭐ Вопрос убран из избранного!"
SUCCESS_QUESTION_DELETED: str = "🗑️ Вопрос удален!"
SUCCESS_SETTING_UPDATED: str = "✅ Настройка «{setting}» обновлена: {value}"


# Error Messages
ERROR_MESSAGE_TOO_LONG: str = (
    "❌ Вопрос слишком длинный. Максимум {max_length} символов."
)
ERROR_MESSAGE_EMPTY: str = "❌ Пустое сообщение не может быть отправлено как вопрос."
ERROR_ADMIN_ONLY: str = "❌ Эта команда доступна только администратору."
ERROR_DATABASE: str = "❌ Произошла ошибка при работе с базой данных. Попробуйте позже."
ERROR_QUESTION_NOT_FOUND: str = "❌ Вопрос не найден или уже удален."
ERROR_ALREADY_ANSWERED: str = "❌ На этот вопрос уже был дан ответ."
ERROR_SETTING_UPDATE: str = "❌ Ошибка при обновлении настройки."
ERROR_INVALID_VALUE: str = "❌ Некорректное значение."
ERROR_RATE_LIMIT: str = (
    "❌ Слишком часто отправляете вопросы. Попробуйте через {seconds} секунд."
)

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


def validate_config() -> bool:
    """Validate all configuration parameters."""
    errors = []

    if not TOKEN or len(TOKEN.split(":")) != 2:
        errors.append("Invalid BOT_TOKEN format")
    if ADMIN_ID <= 0:
        errors.append("ADMIN_ID must be a positive integer")
    if MAX_QUESTION_LENGTH <= 0 or MAX_ANSWER_LENGTH <= 0:
        errors.append("Message length limits must be positive")
    if RATE_LIMIT_QUESTIONS_PER_HOUR <= 0:
        errors.append("Rate limit must be positive")
    if RATE_LIMIT_COOLDOWN_SECONDS <= 0:
        errors.append("Cooldown must be positive")

    if errors:
        raise ValueError(
            "Configuration validation failed:\n" + "\n".join(f"- {e}" for e in errors)
        )
    return True


if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(f"❌ Configuration Error:\n{e}")
        raise

# Network Configuration
POLLING_TIMEOUT = 300
REQUEST_TIMEOUT = 120
CONNECT_TIMEOUT = 60
READ_TIMEOUT = 120
MAX_POLLING_RETRIES = 8
RETRY_DELAY_BASE = 60
MAX_RETRY_DELAY = 600
ALLOWED_UPDATES = ["message", "callback_query"]

# Backup Configuration
BACKUP_ENABLED: bool = (
    get_env_var("BACKUP_ENABLED", default="true", required=False).lower() == "true"
)
BACKUP_RECIPIENT_ID: int = get_env_int("BACKUP_RECIPIENT_ID", required=True)
BACKUP_KEEP_LOCAL_COUNT: int = get_env_int(
    "BACKUP_KEEP_LOCAL_COUNT", default=3, required=False
)
BACKUP_STORAGE_DIR: str = get_env_var(
    "BACKUP_STORAGE_DIR", default="./data/backups", required=False
)
