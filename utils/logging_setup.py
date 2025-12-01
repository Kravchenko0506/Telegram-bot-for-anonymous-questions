"""Logging configuration with file rotation and Sentry integration."""

import logging
import logging.handlers
import sys
from datetime import datetime, timezone
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
from utils.time_helper import ADMIN_TZ


class ColoredFormatter(logging.Formatter):
    """Formatter with color support for console output."""

    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[41m',
    }
    RESET = '\033[0m'

    def format(self, record):
        if sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class TzFormatter(logging.Formatter):
    """Formatter that renders time in ADMIN_TZ."""

    def __init__(self, fmt: str, datefmt: str | None = None, tz=None):
        super().__init__(fmt, datefmt)
        self.tz = tz or ADMIN_TZ

    def formatTime(self, record, datefmt=None):
        try:
            dt = datetime.fromtimestamp(
                record.created, timezone.utc).astimezone(self.tz)
            return dt.strftime(datefmt) if datefmt else dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return super().formatTime(record, datefmt)


def setup_sentry() -> bool:
    """Initialize Sentry error tracking."""
    if not SENTRY_DSN:
        return False

    try:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=SENTRY_ENVIRONMENT,
            release=SENTRY_RELEASE,
            sample_rate=SENTRY_SAMPLE_RATE,
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE if ENABLE_PERFORMANCE_MONITORING else 0.0,
            integrations=[sentry_logging,
                          AsyncioIntegration(), SqlalchemyIntegration()],
            attach_stacktrace=True,
            send_default_pii=False,
            enable_tracing=ENABLE_PERFORMANCE_MONITORING,
        )

        from config import ADMIN_ID
        sentry_sdk.set_user({"id": str(ADMIN_ID), "role": "admin"})
        sentry_sdk.set_tag("component", "telegram_bot")

        print("✅ Sentry initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize Sentry: {e}")
        return False


def setup_logging() -> None:
    """Configure logging with file rotation and console output."""
    if LOG_TO_FILE:
        Path(LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    root_logger.handlers.clear()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_handler.setFormatter(ColoredFormatter(LOG_FORMAT))
    root_logger.addHandler(console_handler)

    
    if LOG_TO_FILE:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, LOG_LEVEL))
        file_handler.setFormatter(TzFormatter(LOG_FORMAT))
        root_logger.addHandler(file_handler)

    _configure_logger_levels()
    sentry_initialized = setup_sentry()

    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("Logging system initialized")
    logger.info(f" Log level: {LOG_LEVEL}")
    logger.info(f"File logging: {'✅' if LOG_TO_FILE else '❌'}")
    logger.info(f"Sentry: {'✅' if sentry_initialized else '❌'}")
    logger.info(f"Debug: {'✅' if DEBUG_MODE else '❌'}")
    logger.info("=" * 50)


def _configure_logger_levels() -> None:
    """Configure logger levels to reduce noise."""
    # Third-party
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

    # Application loggers
    if DEBUG_MODE:
        for name in ("handlers", "models", "middlewares", "utils"):
            logging.getLogger(name).setLevel(logging.DEBUG)
    else:
        logging.getLogger("handlers").setLevel(logging.DEBUG)
        logging.getLogger("models").setLevel(logging.WARNING)
        logging.getLogger("middlewares").setLevel(logging.INFO)
        logging.getLogger("utils").setLevel(logging.INFO)
        logging.getLogger("periodic_tasks").setLevel(logging.ERROR)
        logging.getLogger("handlers.admin").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)


def capture_error(error: Exception, context: Optional[dict] = None) -> None:
    """Capture error to Sentry with optional context."""
    if SENTRY_DSN:
        if context:
            sentry_sdk.set_extra("context", context)
        sentry_sdk.capture_exception(error)
