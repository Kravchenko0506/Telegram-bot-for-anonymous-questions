"""
Only /start command with admin editing capabilities.
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject

from config import ADMIN_ID, WELCOME_MESSAGE_TEMPLATE, MAX_QUESTION_LENGTH, BOT_USERNAME
from utils.logger import get_bot_logger

router = Router()
logger = get_bot_logger()


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject):
    """
    Handle /start command with optional unique parameter.
    
    For users: Shows welcome message
    For admin: Shows admin panel with editing commands
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
        
        welcome_text = WELCOME_MESSAGE_TEMPLATE.format(
            author_name=author_name,
            author_info=author_info,
            max_length=MAX_QUESTION_LENGTH
        )
        
        await message.answer(welcome_text)
        logger.info(f"User {user_id} got welcome with dynamic settings, state reset to idle")
        
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
        logger.info(f"User {user_id} started bot with tracking ID: {unique_id}")
    else:
        logger.info(f"User {user_id} started bot without tracking")

