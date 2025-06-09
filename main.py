"""
Telegram Bot for Anonymous Questions - Production Ready Version

Enhanced with security, rate limiting, and error handling.
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
from utils.logger import get_bot_logger
from utils.periodic_tasks import start_periodic_tasks, stop_periodic_tasks

# Initialize Sentry if configured
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                AsyncioIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                ),
            ],
            traces_sample_rate=0.1,
            environment="production"
        )
        logger = get_bot_logger()
        logger.info("Sentry error tracking initialized")
    except ImportError:
        logger = get_bot_logger()
        logger.warning("Sentry SDK not installed, skipping error tracking")
else:
    logger = get_bot_logger()


async def setup_bot() -> tuple[Bot, Dispatcher]:
    """Initialize bot and dispatcher with proper configuration."""
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
    """Setup simplified bot menu - only /start command."""
    try:
        # Only /start command for all users
        user_commands = [
            BotCommand(command="start", description="🚀 Начать работу с ботом"),
        ]
        
        # Admin gets additional editing commands
        admin_commands = [
            BotCommand(command="start", description="🚀 Админ-панель"),
            BotCommand(command="set_author", description="✏️ Изменить имя автора"),
            BotCommand(command="set_info", description="📝 Изменить описание канала"),
            BotCommand(command="settings", description="⚙️ Текущие настройки"),
            BotCommand(command="stats", description="📊 Статистика"),
            BotCommand(command="pending", description="⏳ Неотвеченные вопросы"),
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
    Register all message and callback handlers.
    
    Handler registration order is important:
    1. Admin states (highest priority - interactive mode)
    2. Admin handlers (callbacks and commands)
    3. Start/help commands  
    4. Question handlers (catch-all, must be last)
    """
    # Register handlers in order of specificity
    dp.include_router(admin_states.router)  # Admin interactive states
    dp.include_router(admin.router)         # Admin callbacks and commands
    dp.include_router(start.router)         # Start and help commands
    dp.include_router(questions.router)     # Question processing (catch-all, LAST)
    
    logger.info("All handlers registered successfully")


async def on_startup(bot: Bot) -> None:
    """Actions to perform on bot startup."""
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
    try:
        await bot.send_message(
            ADMIN_ID,
            "✅ Бот запущен и готов к работе!\n\n"
            f"Версия: Production Ready\n"
            f"Имя: @{bot_info.username}"
        )
    except Exception as e:
        logger.error(f"Failed to notify admin on startup: {e}")


async def on_shutdown(bot: Bot) -> None:
    """Actions to perform on bot shutdown."""
    logger.info("Running shutdown tasks...")
    
    # Stop periodic tasks
    await stop_periodic_tasks()
    
    # Notify admin
    try:
        await bot.send_message(ADMIN_ID, "⚠️ Бот остановлен")
    except Exception:
        pass  # Ignore errors on shutdown
    
    # Close bot session
    await bot.session.close()


async def main() -> None:
    """
    Main application entry point.
    
    Process:
    1. Setup logging
    2. Initialize database
    3. Create bot and dispatcher
    4. Setup bot menu
    5. Register handlers
    6. Start polling with startup/shutdown hooks
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
        dp.startup.register( on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Start bot polling
        logger.info("Bot is starting polling...")
        
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
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
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )
    
    # Suppress noisy loggers
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    print("🚀 Starting bot...")
    print("📁 Logs: console + bot.log file")
    print("🔒 Security features enabled")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Bot stopped")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        logging.exception("Critical startup error")
        exit(1)