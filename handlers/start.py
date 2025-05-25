"""
Start Command Handler for Anonymous Questions Bot

Handles /start command with unique parameter support for aiogram 3.4.1.
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject

from config import ADMIN_ID, get_welcome_message, ADMIN_HELP_MESSAGE
from utils.logger import get_bot_logger

router = Router()
logger = get_bot_logger()


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject):
    """
    Handle /start command with optional unique parameter.
    
    Supports:
    - /start - regular start for new users
    - /start unique_id - start with tracking parameter
    """
    user_id = message.from_user.id
    unique_id = command.args if command.args else None
    
    logger.info(
        f"/start from user {user_id} "
        f"{'with unique_id: ' + unique_id if unique_id else 'without unique_id'}"
    )
    
    # Check if user is admin
    if user_id == ADMIN_ID:
        await message.answer("🔄 <b>Админ-панель перезагружена</b>\n\nИспользуйте /admin для управления ботом")
        logger.info(f"Admin {user_id} reloaded start")
        logger.info(f"Admin {user_id} started the bot")
        return
    
    # Regular user - show welcome message
    welcome_text = get_welcome_message(unique_id)
    
    await message.answer(welcome_text)
    
    # Log user start with tracking info
    if unique_id:
        logger.info(f"User {user_id} started bot with tracking ID: {unique_id}")
    else:
        logger.info(f"User {user_id} started bot without tracking")


@router.message(Command("help"))
async def help_handler(message: Message):
    """Handle /help command."""
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        await message.answer(ADMIN_HELP_MESSAGE)
    else:
        from config import WELCOME_MESSAGE, MAX_QUESTION_LENGTH
        help_text = f"""
🆘 <b>Помощь по использованию бота</b>

<b>Для пользователей:</b>
• Просто напишите ваш вопрос
• Вопрос будет отправлен анонимно
• Ответ придет в этот же чат (если автор ответит)

<b>Команды:</b>
/start - Начать работу с ботом
/help - Показать это сообщение

<i>Максимальная длина вопроса: {MAX_QUESTION_LENGTH} символов</i>
"""
        await message.answer(help_text)
    
    logger.info(f"Help requested by user {user_id}")


@router.message(Command("admin"))
async def admin_command_handler(message: Message):
    """Handle /admin command - admin panel access."""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        from config import ERROR_ADMIN_ONLY
        await message.answer(ERROR_ADMIN_ONLY)
        logger.warning(f"Non-admin user {user_id} attempted to access admin panel")
        return
    
    admin_panel_text = """
🛠 <b>Админ-панель</b>

<b>Доступные команды:</b>
• /favorites - Избранные вопросы
• /stats - Статистика вопросов
• /pending - Неотвеченные вопросы

<b>Управление вопросами:</b>
• Отвечайте на вопросы через Reply
• Используйте кнопки под каждым вопросом

<b>Генерация ссылок:</b>
Используйте: https://t.me/{bot_username}?start=unique_id
""".format(bot_username=message.bot.username or "YourBot")
    
    await message.answer(admin_panel_text)
    logger.info(f"Admin {user_id} accessed admin panel")