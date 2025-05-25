"""
Telegram Bot for Anonymous Questions - Simplified Main Entry Point

Bot with only /start command and admin editing capabilities
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config import TOKEN, ADMIN_ID, validate_config
from models.database import init_db, close_db, check_db_connection
from handlers import start, questions, admin
from handlers import admin_states
from utils.logger import get_bot_logger


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
    
    return bot, dp


async def setup_bot_menu(bot: Bot) -> None:
    """Setup simplified bot menu - only /start command."""
    logger = get_bot_logger()
    
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
        
        logger.info("Simplified bot menu configured: only /start for users, editing commands for admin")
        
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
    
    logger = get_bot_logger()
    logger.info("All handlers registered successfully")


async def main() -> None:
    """
    Main application entry point.
    
    Process:
    1. Setup logging
    2. Initialize database
    3. Create bot and dispatcher
    4. Setup simplified bot menu
    5. Register handlers
    6. Start polling
    7. Handle graceful shutdown
    """
    logger = get_bot_logger()
    
    try:
        logger.info("Starting Anonymous Questions Bot...")
        
        # Initialize database
        logger.info("Initializing PostgreSQL database...")
        await init_db()
        
        # Check database connection
        if not await check_db_connection():
            raise Exception("Database connection failed")
        
        logger.info("Database connection verified")
        
        # Setup bot and dispatcher
        bot, dp = await setup_bot()
        
        # Setup simplified bot menu
        await setup_bot_menu(bot)
        
        # Register handlers
        await register_handlers(dp)
        
        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"Bot started: @{bot_info.username}")
        logger.info(f"Simplified menu: only /start for users, editing commands for admin")
        
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
    # Setup basic logging for startup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Failed to start bot: {e}")
        exit(1)