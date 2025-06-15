# utils/logger.py
"""
Logging System for Anonymous Questions Bot

A comprehensive logging system that provides:
- Separate loggers for different components
- File rotation
- Console output options
- Customizable formatting
- Duplicate handler prevention
- UTF-8 encoding support

Features:
- Bot activity logging
- Admin action logging
- Question processing logging
- Automatic log directory creation
- Log file rotation
- Console output configuration
- Custom log formatting
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)


def configure_logger(
    logger_name: str,
    log_file: str,
    level: int = logging.INFO,
    formatter_string: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 5,
    add_console_handler: bool = False
):
    """
    Configure and return a logger instance with advanced features.

    This function creates a logger with:
    - File rotation support
    - Duplicate handler prevention
    - Console output option
    - Custom formatting
    - UTF-8 encoding

    Args:
        logger_name: Unique name for the logger
        log_file: Path to the log file
        level: Logging level (DEBUG, INFO, etc.)
        formatter_string: Custom format for log messages
        max_bytes: Maximum size for each log file
        backup_count: Number of backup files to keep
        add_console_handler: Whether to add console output

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(logger_name)

    logger.propagate = False  # Prevents messages from propagating to the root logger

    if not logger.level or logger.level > level:
        logger.setLevel(level)

    has_file_handler_for_this_file = any(
        isinstance(h, logging.FileHandler) and os.path.abspath(
            h.baseFilename) == os.path.abspath(log_file)
        for h in logger.handlers
    )

    if not has_file_handler_for_this_file:
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        formatter = logging.Formatter(formatter_string)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if add_console_handler:
        has_console_handler = any(isinstance(h, logging.StreamHandler) and not isinstance(
            h, logging.FileHandler) for h in logger.handlers)
        if not has_console_handler:
            console_formatter = logging.Formatter(
                formatter_string if formatter_string else '%(levelname)s: %(message)s')
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(level)
            logger.addHandler(console_handler)

    return logger


# Initialize specific loggers for different components
bot_logger = configure_logger(
    logger_name="bot",
    log_file=os.path.join(LOG_DIR, "botlogger.log"),
    level=logging.DEBUG,
    add_console_handler=True,  # System messages are important in console
    # Add line number
    formatter_string='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s'
)

admin_logger = configure_logger(
    logger_name="admin",
    log_file=os.path.join(LOG_DIR, "adminlogger.log"),
    level=logging.DEBUG,
    add_console_handler=True
)

question_logger = configure_logger(
    logger_name="question_logger",
    log_file=os.path.join(LOG_DIR, "questionlogger.log"),
    level=logging.DEBUG,
    add_console_handler=True
)


def get_bot_logger() -> logging.Logger:
    """
    Get the bot activity logger.

    This logger handles:
    - Bot startup/shutdown
    - Command processing
    - Error tracking
    - System events

    Returns:
        logging.Logger: Bot logger instance
    """
    return bot_logger


def get_admin_logger() -> logging.Logger:
    """
    Get the admin action logger.

    This logger handles:
    - Admin commands
    - Configuration changes
    - State management
    - Security events

    Returns:
        logging.Logger: Admin logger instance
    """
    return admin_logger


def get_question_logger() -> logging.Logger:
    """
    Get the question processing logger.

    This logger handles:
    - Question submissions
    - Answer processing
    - Moderation actions
    - Rate limiting

    Returns:
        logging.Logger: Question logger instance
    """
    return question_logger


# Initialize loggers
bot_logger.info("Bot logger successfully configured.")
admin_logger.info("Admin logger successfully configured.")
question_logger.info("Question logger successfully configured.")
