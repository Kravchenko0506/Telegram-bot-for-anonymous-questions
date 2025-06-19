"""
Anonymous Questions Telegram Bot

A production-ready Telegram bot that enables anonymous question submission with 
comprehensive admin management and security features.

Core Features:
- Anonymous question submission and management
- Admin interface with extensive controls
- Rate limiting and spam protection
- Error tracking and logging (Sentry integration)
- Database persistence (PostgreSQL)
- Periodic maintenance tasks
- Comprehensive security measures

Technical Features:
- Asynchronous architecture
- Middleware-based request processing
- Structured error handling
- Database connection pooling
- Resource cleanup on shutdown
- Admin notifications
- Command menu management
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, CallbackQuery

from config import TOKEN, ADMIN_ID, validate_config, SENTRY_DSN
from models.database import init_db, close_db, check_db_connection
from handlers import start, questions, admin, admin_states
from middlewares.rate_limit import RateLimitMiddleware, CallbackRateLimitMiddleware
from middlewares.error_handler import ErrorHandlerMiddleware
from utils.logging_setup import setup_logging, get_logger, capture_error
from utils.periodic_tasks import start_periodic_tasks, stop_periodic_tasks

setup_logging()
logger = get_logger(__name__)


async def setup_bot() -> tuple[Bot, Dispatcher]:
    """
    Initialize and configure bot and dispatcher instances.

    This function:
    - Validates all configuration parameters
    - Creates bot instance with HTML parsing
    - Sets up dispatcher with middleware stack
    - Configures error handling and rate limiting

    Returns:
        tuple[Bot, Dispatcher]: Configured bot and dispatcher instances
    """
    # Validate configuration
    validate_config()

    # Create bot instance with default properties
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    # Create dispatcher
    dp = Dispatcher()

    # Add middleware in correct order
    # 1. Error handler (outermost - catches all errors)
    dp.message.middleware(ErrorHandlerMiddleware(notify_admin=True))
    dp.callback_query.middleware(ErrorHandlerMiddleware(notify_admin=True))

    # 2. Rate limiting
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(CallbackRateLimitMiddleware())

    return bot, dp


async def setup_bot_menu(bot: Bot) -> None:
    """
    Configure bot command menu for regular users and admin.

    Sets up two different command sets:
    - Regular users: Basic commands (/start)
    - Admin: Extended command set for bot management

    The admin commands include:
    - Channel management (/set_author, /set_info)
    - Bot settings (/settings)
    - Statistics (/stats)
    - Question management (/pending, /favorites)

    Args:
        bot: Bot instance to configure commands for
    """
    try:
        # Only /start command for all users
        user_commands = [
            BotCommand(command="start", description="🚀 Начать работу с ботом"),
        ]

        # Admin gets additional editing commands
        admin_commands = [
            BotCommand(command="start", description="🚀 Админ-панель"),
            BotCommand(command="set_author",
                       description="✏️ Изменить имя автора"),
            BotCommand(command="set_info",
                       description="📝 Изменить описание канала"),
            BotCommand(command="settings", description="⚙️ Текущие настройки"),
            BotCommand(command="stats", description="📊 Статистика"),
            BotCommand(command="pending",
                       description="⏳ Неотвеченные вопросы"),
            BotCommand(command="favorites", description="⭐ Избранные"),
        ]

        # Set commands for all users (only /start)
        await bot.set_my_commands(user_commands, BotCommandScopeDefault())

        # Set admin-specific commands
        await bot.set_my_commands(
            admin_commands,
            BotCommandScopeChat(chat_id=ADMIN_ID)
        )

        logger.info("Bot menu configured successfully")

    except Exception as e:
        logger.error(f"Failed to setup bot menu: {e}")


async def register_handlers(dp: Dispatcher) -> None:
    """
    Register all message and callback handlers in the correct order.

    Handler Registration Priority:
    1. Admin states - Highest priority, handles interactive admin mode
    2. Admin handlers - Processes admin callbacks and commands
    3. Start/help commands - Basic user interaction
    4. Question handlers - Catch-all for user questions (lowest priority)

    The order is critical for proper message routing.

    Args:
        dp: Dispatcher instance to register handlers with
    """
    # Register handlers in order of specificity
    dp.include_router(admin_states.router)  # Admin interactive states
    dp.include_router(admin.router)         # Admin callbacks and commands
    dp.include_router(start.router)         # Start and help commands
    # Question processing (catch-all, LAST)
    dp.include_router(questions.router)

    logger.info("All handlers registered successfully")


async def on_startup(bot: Bot) -> None:
    """
    Perform necessary startup tasks when the bot begins operation.

    Tasks performed:
    1. Database connection verification
    2. Start periodic maintenance tasks
    3. Retrieve and log bot information
    4. Send startup notification to admin

    Args:
        bot: Bot instance to use for startup tasks

    Raises:
        Exception: If database connection fails
    """
    logger.info("Running startup tasks...")

    # Verify database connection
    if not await check_db_connection():
        raise Exception("Database connection failed")

    # Start periodic tasks
    await start_periodic_tasks()

    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")

    # Notify admin
    """
    try:
        await bot.send_message(
            ADMIN_ID,
            "✅ Бот запущен и готов к работе!\n\n"
            f"Версия: Production Ready\n"
            f"Имя: @{bot_info.username}"
        )
    except Exception as e:
        logger.error(f"Failed to notify admin on startup: {e}")
    """


async def on_shutdown(bot: Bot) -> None:
    """
    Perform cleanup tasks when the bot is shutting down.

    Tasks performed:
    1. Stop periodic maintenance tasks
    2. Send shutdown notification to admin
    3. Close bot session

    Args:
        bot: Bot instance to perform shutdown tasks with
    """
    logger.info("Running shutdown tasks...")

    # Stop periodic tasks
    await stop_periodic_tasks()

    # Notify admin
    """
    try:
        await bot.send_message(ADMIN_ID, "⚠️ Бот остановлен")
    except Exception:
        pass  # Ignore errors on shutdown
    """

    # Close bot session
    await bot.session.close()


async def main() -> None:
    """
    Main application entry point and lifecycle manager.

    Responsibilities:
    1. Database initialization
    2. Bot and dispatcher setup
    3. Command menu configuration
    4. Handler registration
    5. Startup/shutdown handler registration
    6. Bot polling management
    7. Resource cleanup

    Error Handling:
    - Graceful handling of keyboard interrupts
    - Critical error logging
    - Resource cleanup in all cases
    """
    try:
        logger.info("Starting Anonymous Questions Bot (Production Mode)...")

        # Initialize database
        logger.info("Initializing PostgreSQL database...")
        await init_db()

        # Setup bot and dispatcher
        bot, dp = await setup_bot()

        # Setup bot menu
        await setup_bot_menu(bot)

        # Register handlers
        await register_handlers(dp)

        # Set startup and shutdown hooks
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        # Start bot polling
        logger.info("Bot is starting polling...")

        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")

    except Exception as e:
        logger.error(f"Critical error: {e}")
        capture_error(e, {"phase": "main_application"})
        raise

    finally:
        # Cleanup resources
        try:
            await close_db()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    """
    Application entry point.

    Sets up proper logging and runs the main coroutine.
    """

    print("🚀 Starting bot...")
    print("📁 Logs: console + persistent log files")
    print("🔒 Security features enabled")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Bot stopped")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        logging.exception("Critical startup error")
        exit(1)
