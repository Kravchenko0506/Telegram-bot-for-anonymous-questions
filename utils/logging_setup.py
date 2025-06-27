"""
Logging Configuration System

Comprehensive logging setup with:
- Environment-based configuration
- File rotation
- Sentry integration
- Performance monitoring
- Custom formatters
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from config import (
    LOG_LEVEL, LOG_FORMAT, LOG_TO_FILE, LOG_FILE_PATH,
    LOG_MAX_SIZE_MB, LOG_BACKUP_COUNT, SENTRY_DSN,
    SENTRY_ENVIRONMENT, SENTRY_RELEASE, SENTRY_SAMPLE_RATE,
    SENTRY_TRACES_SAMPLE_RATE, ENABLE_PERFORMANCE_MONITORING,
    DEBUG_MODE, VERBOSE_DATABASE_LOGS
)

os.environ['TZ'] = 'Europe/Moscow'

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
    }
    RESET = '\033[0m'

    def format(self, record):
        if sys.stdout.isatty():  # Only colorize if output is a terminal
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_sentry() -> bool:
    """
    Initialize Sentry error tracking and performance monitoring.

    Returns:
        bool: True if Sentry was successfully initialized
    """
    if not SENTRY_DSN:
        return False

    try:
        # Configure logging integration
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )

        # Initialize Sentry
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=SENTRY_ENVIRONMENT,
            release=SENTRY_RELEASE,
            sample_rate=SENTRY_SAMPLE_RATE,
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE if ENABLE_PERFORMANCE_MONITORING else 0.0,

            # Integrations
            integrations=[
                sentry_logging,
                AsyncioIntegration(),
                SqlalchemyIntegration(),
            ],

            # Additional options
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send personally identifiable information

            # Performance monitoring
            enable_tracing=ENABLE_PERFORMANCE_MONITORING,
        )

        # Set user context (admin ID for better tracking)
        from config import ADMIN_ID
        sentry_sdk.set_user({"id": str(ADMIN_ID), "role": "admin"})

        # Set tags
        sentry_sdk.set_tag("component", "telegram_bot")
        sentry_sdk.set_tag("bot_username", getattr(
            __import__('config'), 'BOT_USERNAME', 'unknown'))

        print("✅ Sentry initialized successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to initialize Sentry: {e}")
        return False


def setup_logging() -> None:
    """
    Configure comprehensive logging system with file rotation and console output.

    Features:
    - Environment-configurable log levels
    - File rotation with size limits
    - Colored console output
    - Separate logger configurations
    - Sentry integration
    """

    # Create log directory if needed
    if LOG_TO_FILE:
        log_path = Path(LOG_FILE_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_formatter = ColoredFormatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    if LOG_TO_FILE:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,  # Convert MB to bytes
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, LOG_LEVEL))
        file_formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Configure specific loggers to reduce noise
    configure_logger_levels()

    # Initialize Sentry
    sentry_initialized = setup_sentry()

    # Log initialization status
    logger = logging.getLogger(__name__)
    logger.info("="*50)
    logger.info("🚀 Logging system initialized")
    logger.info(f"📊 Log level: {LOG_LEVEL}")
    logger.info(f"📁 File logging: {'✅' if LOG_TO_FILE else '❌'}")
    logger.info(f"🔍 Sentry monitoring: {'✅' if sentry_initialized else '❌'}")
    logger.info(f"🐛 Debug mode: {'✅' if DEBUG_MODE else '❌'}")
    logger.info("="*50)


def configure_logger_levels() -> None:
    """Configure individual logger levels to reduce noise"""

    # Third-party libraries
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # SQLAlchemy
    if VERBOSE_DATABASE_LOGS:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
    else:
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    # Our application loggers
    if DEBUG_MODE:
        logging.getLogger("handlers").setLevel(logging.DEBUG)
        logging.getLogger("models").setLevel(logging.DEBUG)
        logging.getLogger("middlewares").setLevel(logging.DEBUG)
        logging.getLogger("utils").setLevel(logging.DEBUG)
    else:
        logging.getLogger("handlers").setLevel(logging.DEBUG)
        logging.getLogger("models").setLevel(logging.WARNING)
        logging.getLogger("middlewares").setLevel(
            logging.INFO) 
        logging.getLogger("utils").setLevel(
            logging.INFO) 
        logging.getLogger("periodic_tasks").setLevel(
            logging.ERROR) 
        logging.getLogger("handlers.admin").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


# Context manager for Sentry transactions
class SentryTransaction:
    """Context manager for Sentry performance monitoring"""

    def __init__(self, name: str, op: str = "task"):
        self.name = name
        self.op = op
        self.transaction = None

    def __enter__(self):
        if SENTRY_DSN and ENABLE_PERFORMANCE_MONITORING:
            self.transaction = sentry_sdk.start_transaction(
                name=self.name,
                op=self.op
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.transaction:
            if exc_type:
                self.transaction.set_status("internal_error")
            else:
                self.transaction.set_status("ok")
            self.transaction.finish()


# Error capture helper
def capture_error(error: Exception, context: Optional[dict] = None) -> None:
    """
    Capture error to Sentry with additional context.

    Args:
        error: Exception to capture
        context: Additional context information
    """
    if SENTRY_DSN:
        if context:
            sentry_sdk.set_extra("context", context)
        sentry_sdk.capture_exception(error)
