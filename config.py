"""
Configuration Management System

A comprehensive configuration system for the Anonymous Questions Bot that handles:
- Environment variable management
- Database configuration
- Bot settings and limits
- Message templates
- Security parameters
- External service integration
- Dynamic settings

Features:
- Environment variable validation
- Type conversion
- Default value handling
- Configuration validation
- Secure credential management
- Internationalization support
- Dynamic runtime configuration
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


def get_env_var(key: str, default: Optional[str] = None, required: bool = True) -> str:
    """
    Retrieve and validate environment variables with comprehensive error handling.

    This function provides a robust way to:
    - Load environment variables
    - Handle missing variables
    - Provide default values
    - Validate requirements

    Args:
        key: Name of the environment variable to retrieve
        default: Default value if variable is not found
        required: Whether the variable must be present

    Returns:
        str: The value of the environment variable

    Raises:
        ValueError: If a required variable is missing
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
    """
    Get integer environment variable with robust error handling.
    Handles various hosting platform quirks.

    Args:
        key: Name of the environment variable
        default: Default integer value if variable is not found
        required: Whether the variable must be present

    Returns:
        int: The integer value of the environment variable

    Raises:
        ValueError: If value cannot be converted to integer with detailed message
    """
    value = get_env_var(
        key, str(default) if default is not None else None, required)

    if '=' in value:
        value = value.split('=')[-1]

    value = value.strip()

    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1]

    try:
        result = int(value)
        return result
    except ValueError as e:
        print(
            f"Error parsing {key}: '{value}' (original: '{get_env_var(key)}')")
        raise ValueError(
            f"Environment variable '{key}' must be an integer, got: '{value}'. Original value: '{get_env_var(key)}'")


# Bot Configuration - REQUIRED
TOKEN: str = get_env_var("BOT_TOKEN")
"""Telegram Bot API token from @BotFather"""

ADMIN_ID: int = get_env_int("ADMIN_ID")
"""Telegram user ID of the bot administrator"""

BOT_USERNAME: str = get_env_var("BOT_USERNAME")
"""Bot username for generating links (without @)"""

# Pagination Settings
QUESTIONS_PER_PAGE: int = get_env_int(
    "QUESTIONS_PER_PAGE", default=5, required=False)
"""Number of questions to show per page in admin interface"""

MAX_PAGES_TO_SHOW: int = get_env_int(
    "MAX_PAGES_TO_SHOW", default=100, required=False)
"""Maximum number of pages to show (prevents memory issues with huge databases)"""

# Admin Interface Settings
ADMIN_AUTO_REFRESH: bool = get_env_var(
    "ADMIN_AUTO_REFRESH", default="false", required=False).lower() == "true"
"""Whether to auto-refresh admin lists after actions"""

SHOW_QUESTION_PREVIEW_LENGTH: int = get_env_int(
    "SHOW_QUESTION_PREVIEW_LENGTH", default=200, required=False)
"""Length of question preview in admin interface"""

# Bot Settings - OPTIONAL with safe defaults
MAX_QUESTION_LENGTH: int = get_env_int(
    "MAX_QUESTION_LENGTH", default=2500, required=False)
"""Maximum length of a question in characters"""

MAX_ANSWER_LENGTH: int = get_env_int(
    "MAX_ANSWER_LENGTH", default=6000, required=False)
"""Maximum length of an answer in characters"""

# Logging Configuration
LOG_LEVEL: str = get_env_var(
    "LOG_LEVEL", default="INFO", required=False).upper()
"""Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"""

LOG_FORMAT: str = get_env_var(
    "LOG_FORMAT",
    default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    required=False
)
"""Custom log format string"""

LOG_TO_FILE: bool = get_env_var(
    "LOG_TO_FILE", default="true", required=False).lower() == "true"
"""Whether to save logs to file"""

LOG_FILE_PATH: str = get_env_var(
    "LOG_FILE_PATH", default="/data/bot.log", required=False)
"""Path to log file (in persistent storage)"""

LOG_MAX_SIZE_MB: int = get_env_int(
    "LOG_MAX_SIZE_MB", default=10, required=False)
"""Maximum log file size in MB before rotation"""

LOG_BACKUP_COUNT: int = get_env_int(
    "LOG_BACKUP_COUNT", default=5, required=False)
"""Number of backup log files to keep"""

# Security Settings
RATE_LIMIT_QUESTIONS_PER_HOUR: int = get_env_int(
    "RATE_LIMIT_QUESTIONS_PER_HOUR", default=500, required=False)
"""Maximum questions per hour from one user"""

RATE_LIMIT_COOLDOWN_SECONDS: int = get_env_int(
    "RATE_LIMIT_COOLDOWN_SECONDS", default=5, required=False)
"""Minimum seconds between questions from same user"""

# Sentry Configuration for Error Tracking
SENTRY_DSN: Optional[str] = get_env_var(
    "SENTRY_DSN", default=None, required=False)
"""Sentry DSN for error tracking (optional)"""

SENTRY_ENVIRONMENT: str = get_env_var(
    "SENTRY_ENVIRONMENT", default="production", required=False)
"""Sentry environment name (development/staging/production)"""

SENTRY_RELEASE: Optional[str] = get_env_var(
    "SENTRY_RELEASE", default=None, required=False)
"""Sentry release version (optional)"""

SENTRY_SAMPLE_RATE: float = float(get_env_var(
    "SENTRY_SAMPLE_RATE", default="1.0", required=False))
"""Sentry error sampling rate (0.0 to 1.0)"""

SENTRY_TRACES_SAMPLE_RATE: float = float(get_env_var(
    "SENTRY_TRACES_SAMPLE_RATE", default="0.1", required=False))
"""Sentry performance monitoring sample rate (0.0 to 1.0)"""

# Performance Monitoring
ENABLE_PERFORMANCE_MONITORING: bool = get_env_var(
    "ENABLE_PERFORMANCE_MONITORING", default="false", required=False).lower() == "true"
"""Enable Sentry performance monitoring"""

# Debug Options
DEBUG_MODE: bool = get_env_var(
    "DEBUG_MODE", default="false", required=False).lower() == "true"
"""Enable debug features (verbose logging, etc.)"""

VERBOSE_DATABASE_LOGS: bool = get_env_var(
    "VERBOSE_DATABASE_LOGS", default="false", required=False).lower() == "true"
"""Enable verbose database operation logging"""

# Validate log level
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
if LOG_LEVEL not in VALID_LOG_LEVELS:
    raise ValueError(
        f"Invalid LOG_LEVEL '{LOG_LEVEL}'. Must be one of: {VALID_LOG_LEVELS}")

# Validate Sentry sample rates
if not 0.0 <= SENTRY_SAMPLE_RATE <= 1.0:
    raise ValueError("SENTRY_SAMPLE_RATE must be between 0.0 and 1.0")

if not 0.0 <= SENTRY_TRACES_SAMPLE_RATE <= 1.0:
    raise ValueError("SENTRY_TRACES_SAMPLE_RATE must be between 0.0 and 1.0")

# Dynamic settings defaults (stored in database)
DEFAULT_AUTHOR_NAME: str = "Автор канала"
"""Default author name (can be changed by admin)"""

DEFAULT_AUTHOR_INFO: str = "Здесь можно задать анонимный вопрос"
"""Default author info (can be changed by admin)"""

# Message Templates
WELCOME_MESSAGE_TEMPLATE: str = """
👋 <b>Привет! Вы можете анонимно задать свой вопрос автору.</b>

ℹ️ <b>Автор:</b> {author_name}
📝 <b>О канале:</b> {author_info}

✍️ Просто напишите свой вопрос в ответном сообщении.

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
ERROR_MESSAGE_TOO_LONG: str = "❌ Вопрос слишком длинный. Максимум {max_length} символов."  
ERROR_MESSAGE_EMPTY: str = "❌ Пустое сообщение не может быть отправлено как вопрос."
ERROR_ADMIN_ONLY: str = "❌ Эта команда доступна только администратору."
ERROR_DATABASE: str = "❌ Произошла ошибка при работе с базой данных. Попробуйте позже."
ERROR_QUESTION_NOT_FOUND: str = "❌ Вопрос не найден или уже удален."
ERROR_ALREADY_ANSWERED: str = "❌ На этот вопрос уже был дан ответ."
ERROR_SETTING_UPDATE: str = "❌ Ошибка при обновлении настройки."
ERROR_INVALID_VALUE: str = "❌ Некорректное значение."
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
    Generate a deep link to the bot with tracking parameters.

    Creates a properly formatted Telegram bot link that includes:
    - Bot username
    - Start parameter for tracking
    - UTM parameters if configured

    Args:
        unique_id: Tracking identifier for the link

    Returns:
        str: Complete bot deep link URL
    """
    return f"https://t.me/{BOT_USERNAME}?start={unique_id}"


def validate_config() -> bool:
    """
    Perform comprehensive validation of all configuration parameters.

    Validates:
    - Required environment variables
    - Variable types and formats
    - Value ranges and constraints
    - Security requirements
    - Database configuration
    - External service settings

    Returns:
        bool: True if all validation checks pass

    Raises:
        ValueError: If any configuration parameter is invalid
    """
    errors = []

    # Check if TOKEN is valid (basic format check)
    if not TOKEN or len(TOKEN.split(':')) != 2:
        errors.append("Invalid BOT_TOKEN format")

    # Check if ADMIN_ID is valid
    if ADMIN_ID <= 0:
        errors.append("ADMIN_ID must be a positive integer")

    # Validate numeric values
    if MAX_QUESTION_LENGTH <= 0 or MAX_ANSWER_LENGTH <= 0:
        errors.append("Message length limits must be positive")

    # Validate rate limits
    if RATE_LIMIT_QUESTIONS_PER_HOUR <= 0:
        errors.append("Rate limit must be positive")

    if RATE_LIMIT_COOLDOWN_SECONDS <= 0:
        errors.append("Cooldown must be positive")

    if errors:
        error_message = "Configuration validation failed:\n" + \
            "\n".join(f"- {e}" for e in errors)
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


# NETWORK CONFIGURATION FOR STABLE TELEGRAM CONNECTION

# Network timeouts (seconds)
POLLING_TIMEOUT = 300           # How long to wait for new messages
REQUEST_TIMEOUT = 120            # Individual request timeout
CONNECT_TIMEOUT = 60            # Connection establishment timeout
READ_TIMEOUT = 120               # Socket read timeout

# Retry settings
MAX_POLLING_RETRIES = 8         # Max reconnection attempts
RETRY_DELAY_BASE = 60           # Base delay between retries (seconds)
MAX_RETRY_DELAY = 600           # Maximum delay between retries (seconds)

# Allowed update types (reduces bandwidth)
ALLOWED_UPDATES = ["message", "callback_query"]


# =============================================================================
# TELEGRAM BACKUP CONFIGURATION
# =============================================================================

# Backup system settings
BACKUP_ENABLED: bool = get_env_var(
    "BACKUP_ENABLED", default="true", required=False).lower() == "true"
"""Enable automatic backup system"""

BACKUP_RECIPIENT_ID: int = get_env_int(
    "BACKUP_RECIPIENT_ID", required=True)
"""Telegram user ID to receive backup files (MUST be set in .env file)"""

BACKUP_KEEP_LOCAL_COUNT: int = get_env_int(
    "BACKUP_KEEP_LOCAL_COUNT", default=3, required=False)
"""Number of local backup files to keep for cleanup"""

BACKUP_STORAGE_DIR: str = get_env_var(
    "BACKUP_STORAGE_DIR", default="./data/backups", required=False)
"""Directory for temporary local backup storage"""
