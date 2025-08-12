"""
Start Command Handler

A comprehensive handler for the /start command that provides different
functionality for admin and regular users with dynamic configuration.

Features:
- Admin panel access
- User welcome messages
- Dynamic settings
- State management
- Error handling
- User tracking
- Logging support

Technical Features:
- Role-based access
- Dynamic configuration
- State management
- Error recovery
- User analytics
- Logging integration
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject

from config import ADMIN_ID, WELCOME_MESSAGE_TEMPLATE, MAX_QUESTION_LENGTH, BOT_USERNAME
from utils.logging_setup import get_logger
from models.settings import SettingsManager

router = Router()
logger = get_logger(__name__)


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject):
    """
    Process /start command with comprehensive functionality.

    This handler provides:
    - Role-based responses (admin/user)
    - Dynamic configuration
    - State management
    - User tracking
    - Error handling

    Features:
    - Admin panel for administrators
    - Welcome message for users
    - Dynamic settings integration
    - State reset functionality
    - User tracking support
    - Error recovery

    Flow:
    1. Identify user role
    2. For admin:
       - Show admin panel with commands
       - Log admin access
    3. For users:
       - Reset user state
       - Load dynamic settings
       - Show welcome message
       - Track user source

    Args:
        message: Telegram message object
        command: Command object with arguments

    Technical Details:
    - Handles circular imports
    - Provides fallback messages
    - Implements error recovery
    - Maintains user state
    - Tracks user sources
    """
    user_id = message.from_user.id
    unique_id = command.args if command.args else None

    logger.info(
        f"/start from user {user_id} "
        f"{'with unique_id: ' + unique_id if unique_id else 'without unique_id'}"
    )

    # Check if user is admin
    if user_id == ADMIN_ID:
        admin_panel = f"""
🛠 <b>Админ-панель бота</b>

📋 <b>Управление настройками:</b>
• /set_author - Изменить имя автора
• /set_info - Изменить описание канала
• /settings - Просмотр текущих настроек

📊 <b>Управление вопросами:</b>
• /pending - Неотвеченные вопросы
• /favorites - Избранные вопросы
• /stats - Статистика

🔗 <b>Ссылка для пользователей:</b>
<code>https://t.me/{BOT_USERNAME}?start=channel</code>

<i>Пользователи видят только команду /start</i>
"""

        await message.answer(admin_panel)
        logger.info(f"Admin {user_id} accessed simplified admin panel")
        return

    # Regular user - show welcome message with dynamic settings
    try:
        # Import here to avoid circular imports
        from models.settings import SettingsManager
        from models.user_states import UserStateManager

        # Reset user state to idle when they use /start
        await UserStateManager.reset_to_idle(user_id)

        author_name = await SettingsManager.get_author_name()
        author_info = await SettingsManager.get_author_info()

        max_length = await SettingsManager.get_max_question_length()  
        welcome_text = WELCOME_MESSAGE_TEMPLATE.format(
            author_name=author_name,
            author_info=author_info,
            max_length=max_length
        )

        await message.answer(welcome_text)
        logger.info(
            f"User {user_id} got welcome with dynamic settings, state reset to idle")

    except Exception as e:
        # Fallback to defaults if settings can't be loaded
        logger.error(f"Error loading dynamic settings: {e}")

        fallback_message = WELCOME_MESSAGE_TEMPLATE.format(
            author_name="Автор канала",
            author_info="Здесь можно задать анонимный вопрос",
            max_length=MAX_QUESTION_LENGTH
        )

        await message.answer(fallback_message)
        logger.warning(f"User {user_id} got fallback welcome message")

    # Log user start with tracking info
    if unique_id:
        logger.info(
            f"User {user_id} started bot with tracking ID: {unique_id}")
    else:
        logger.info(f"User {user_id} started bot without tracking")
