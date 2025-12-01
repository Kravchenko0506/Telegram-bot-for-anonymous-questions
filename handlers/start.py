"""
Start Command Handler
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject

from config import ADMIN_ID, WELCOME_MESSAGE_TEMPLATE, MIN_QUESTION_LENGTH, MAX_QUESTION_LENGTH, BOT_USERNAME
from utils.logging_setup import get_logger
from models.settings import SettingsManager
from models.user_states import UserStateManager

router = Router()
logger = get_logger(__name__)


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject):
    """Process /start command with role-based routing"""
    user_id = message.from_user.id
    unique_id = command.args if command.args else None

    await _log_start_event(user_id, unique_id)

    if user_id == ADMIN_ID:
        await _handle_admin_start(message)
    else:
        await _handle_user_start(message, user_id, unique_id)


async def _log_start_event(user_id: int, unique_id: str):
    """Log start event with tracking information"""
    log_message = f"/start from user {user_id}"
    if unique_id:
        log_message += f" with unique_id: {unique_id}"
    logger.info(log_message)


async def _handle_admin_start(message: Message):
    """Handle /start command for administrator"""
    admin_panel = _build_admin_panel()
    await message.answer(admin_panel)
    logger.info(f"Admin {message.from_user.id} accessed admin panel")


def _build_admin_panel() -> str:
    """Build administrator control panel text"""
    link = get_bot_link("channel")
    return (
        "👋 <b>Привет!</b>\n\n"
        "Этот бот позволяет получать анонимные вопросы от подписчиков. "
        "Пользователи пишут — ты отвечаешь, и ответ приходит им в личку.\n\n"
        "📂 <b>Команды:</b>\n"
        "⏳ /pending - неотвеченные\n"
        "⭐ /favorites - избранные\n"
        "✅ /answered - отвеченные\n"
        "📊 /stats - статистика\n"
        "⚙️ /settings - настройки\n"
        "📏 /limits - лимиты\n"
        "💾 /backup_info - резервная копия\n\n"
        "🔗 <b>Ссылка для пользователей:</b>\n"
        f"<code>{link}</code>"
    )


def get_bot_link(param: str = "") -> str:
    """Generate bot link with optional parameter"""
    link = f"https://t.me/{BOT_USERNAME}"
    if param:
        link += f"?start={param}"
    return link


async def _handle_user_start(message: Message, user_id: int, unique_id: str):
    """Handle /start command for regular users"""
    # Reset user state to idle
    await UserStateManager.reset_to_idle(user_id)
    try:
        # Get dynamic settings from database
        author_name, author_info, min_length, max_length = await _get_user_settings()
        welcome_text = WELCOME_MESSAGE_TEMPLATE.format(
            author_name=author_name,
            author_info=author_info,
            min_length=min_length,
            max_length=max_length
        )
        logger.info(f"User {user_id} received welcome with dynamic settings")
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        welcome_text = _get_fallback_welcome()
        logger.warning(f"User {user_id} received fallback welcome message")

    await message.answer(welcome_text)

    if unique_id:
        logger.info(
            f"User {user_id} started bot with tracking ID: {unique_id}")
    else:
        logger.info(f"User {user_id} started bot without tracking")


async def _get_user_settings() -> tuple:
    """Get dynamic settings for welcome message"""
    return (
        await SettingsManager.get_author_name(),
        await SettingsManager.get_author_info(),
        await SettingsManager.get_min_question_length(),
        await SettingsManager.get_max_question_length()
    )


def _get_fallback_welcome() -> str:
    """Generate fallback welcome message with default values"""
    return WELCOME_MESSAGE_TEMPLATE.format(
        author_name="Автор канала",
        author_info="Здесь можно задать анонимный вопрос",
        min_length=MIN_QUESTION_LENGTH,
        max_length=MAX_QUESTION_LENGTH
    )
