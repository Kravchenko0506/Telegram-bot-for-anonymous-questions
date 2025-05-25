"""
Telegram Bot for Anonymous Questions - Main Entry Point

Этот модуль является точкой входа для бота анонимных вопросов.
Бот позволяет пользователям отправлять анонимные вопросы админу канала
и получать ответы через бота.

Основные функции:
- Инициализация бота и диспетчера
- Регистрация обработчиков команд
- Запуск polling для получения обновлений

Architecture:
Bot -> Dispatcher -> Handlers -> Database
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import TOKEN, ADMIN_ID
from handlers import common, admin, user
from models import init_db


def setup_logging() -> None:
    """
    Configure logging for the application.
    
    Sets up basic logging configuration with INFO level
    to track bot operations and potential issues.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def register_handlers(dp: Dispatcher) -> None:
    """
    Register all message and callback handlers.
    
    Args:
        dp (Dispatcher): The aiogram dispatcher instance
        
    Handler registration order matters:
    1. Admin handlers (specific commands first)
    2. Common handlers (general commands)
    3. User handlers (catch-all for questions)
    """
    # Register admin handlers first (more specific)
    dp.include_router(admin.router)
    
    # Register common handlers (start, help commands)
    dp.include_router(common.router)
    
    # Register user handlers last (catch-all for questions)
    dp.include_router(user.router)


async def main() -> None:
    """
    Main application entry point.
    
    Initializes the bot, database, registers handlers and starts polling.
    Handles graceful shutdown on KeyboardInterrupt.
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize bot and dispatcher
    bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Register all handlers
        await register_handlers(dp)
        logger.info("Handlers registered successfully")
        
        # Start bot polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Cleanup
        await bot.session.close()
        logger.info("Bot session closed")


if __name__ == "__main__":
    """
    Application entry point.
    
    Runs the main coroutine using asyncio.run() which handles
    the event loop creation and cleanup automatically.
    """
    asyncio.run(main())

