"""Main bot launch module."""

import asyncio
import signal
from contextlib import suppress
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from config import TOKEN, ADMIN_ID, validate_config, SENTRY_DSN
from models.database import init_db, close_db, check_db_connection
from handlers import start, questions, admin, admin_states, admin_limits
from middlewares.rate_limit import RateLimitMiddleware, CallbackRateLimitMiddleware
from middlewares.error_handler import ErrorHandlerMiddleware
from utils.logging_setup import setup_logging, get_logger, capture_error
from utils.periodic_tasks import start_periodic_tasks, stop_periodic_tasks

setup_logging()
logger = get_logger(__name__)

_shutdown_flag = asyncio.Event()


def _install_signals() -> None:
    """Install SIGINT/SIGTERM handlers if supported by the platform."""
    loop = asyncio.get_running_loop()
    for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        if sig is None:
            continue
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _shutdown_flag.set)


async def setup_bot() -> tuple[Bot, Dispatcher]:
    """Create Bot & Dispatcher instances and attach middlewares."""
    validate_config()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    # Errors first
    err_mw = ErrorHandlerMiddleware(notify_admin=True)
    dp.message.middleware(err_mw)
    dp.callback_query.middleware(err_mw)
    # Rate limits
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(CallbackRateLimitMiddleware())
    return bot, dp


USER_COMMANDS: list[tuple[str, str]] = [
    ("start", "🚀 Начать работу"),
]

ADMIN_COMMANDS: list[tuple[str, str]] = [
    
    ("start", "🚀 Главная"),
    ("settings", "⚙️ Настройки"),
    ("limits", "📏 Управление лимитами"),
    ("stats", "📊 Статистика"),
    ("pending", "⏳ Неотвеченные"),
    ("favorites", "⭐ Избранные"),
    ("answered", "✅ Отвеченные"),
    ("backup_info", "💾 Бэкап"),
    ("health", "🩺 Health"),
]


async def setup_bot_menu(bot: Bot) -> None:
    """Register user/admin command menus from USER_COMMANDS / ADMIN_COMMANDS."""
    try:
        await bot.set_my_commands(
            [BotCommand(command=c, description=d) for c, d in USER_COMMANDS],
            BotCommandScopeDefault()
        )
        await bot.set_my_commands(
            [BotCommand(command=c, description=d) for c, d in ADMIN_COMMANDS],
            BotCommandScopeChat(chat_id=ADMIN_ID)
        )
    except Exception as e:  # pragma: no cover
        logger.warning(f"Не удалось установить команды: {e}")


async def register_handlers(dp: Dispatcher) -> None:
    """Include routers ordered by specificity (states → admin → general)."""
    dp.include_router(admin_states.router)
    dp.include_router(admin.router)
    dp.include_router(admin_limits.router)
    dp.include_router(start.router)
    dp.include_router(questions.router)


async def _notify_admin(bot: Bot, text: str) -> None:
    """Safely send a notification message to admin (suppresses failures)."""
    with suppress(Exception):
        await bot.send_message(ADMIN_ID, text)


async def on_startup(bot: Bot) -> None:
    """Startup hook: check DB connectivity, start periodic tasks, notify admin."""
    logger.info("Стартую сервисы...")
    if not await check_db_connection():
        raise RuntimeError("Нет подключения к БД")
    await start_periodic_tasks()
    info = await bot.get_me()
    await _notify_admin(bot, f"✅ Бот запущен: @{info.username}")


async def on_shutdown(bot: Bot) -> None:
    """Shutdown hook: stop tasks, notify admin, close bot session."""
    logger.info("Останавливаю сервисы...")
    await stop_periodic_tasks()
    await _notify_admin(bot, "⚠️ Бот остановлен")
    await bot.session.close()


async def start_polling(bot: Bot, dp: Dispatcher) -> None:
    """Start polling with short retry backoff for transient network errors."""
    from config import POLLING_TIMEOUT, ALLOWED_UPDATES
    attempts = 0
    while not _shutdown_flag.is_set():
        try:
            await dp.start_polling(
                bot,
                timeout=POLLING_TIMEOUT,
                allowed_updates=ALLOWED_UPDATES,
                stop_signal=None,
            )
            break  # graceful stop (shutdown requested)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            attempts += 1
            logger.error(f"Polling сбой ({attempts}): {type(e).__name__}: {e}")
            if attempts >= 3:
                raise
            await asyncio.sleep(min(5 * attempts, 20))


async def main_flow() -> None:
    """Full initialization pipeline before entering polling loop."""
    logger.info("Initializing database")
    await init_db()
    bot, dp = await setup_bot()
    await setup_bot_menu(bot)
    await register_handlers(dp)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await start_polling(bot, dp)


async def safe_main() -> None:
    """Top-level guarded runner: install signals, run flow, capture fatal errors, release resources."""
    _install_signals()
    try:
        await main_flow()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.critical(f"CRITICAL ERROR: {e}", exc_info=True)
        if SENTRY_DSN:
            with suppress(Exception):
                capture_error(e, {"phase": "fatal", "type": type(e).__name__})
        raise
    finally:
        await close_db()
        logger.info("Resources released")


if __name__ == "__main__":
    asyncio.run(safe_main())
