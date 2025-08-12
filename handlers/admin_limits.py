"""
Admin Limits Management System

A comprehensive system for managing bot limits and restrictions through
admin commands. This module provides commands for viewing and updating
various bot limits.

Features:
- Limit viewing
- Limit updating
- Value validation
- Error handling
- User feedback
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from config import ADMIN_ID, ERROR_ADMIN_ONLY
from models.settings import SettingsManager
from utils.logging_setup import get_logger

router = Router()
logger = get_logger(__name__)

# Конфигурация команд для управления лимитами
LIMIT_COMMANDS = {
    "rate_limit": {
        "command": "set_rate_limit",
        "getter": SettingsManager.get_rate_limit_per_hour,
        "setter": SettingsManager.set_rate_limit_per_hour,
        "range": (1, 100),
        "unit": "",
        "name": "Лимит вопросов",
        "description": "вопросов в час"
    },
    "cooldown": {
        "command": "set_cooldown",
        "getter": SettingsManager.get_rate_limit_cooldown,
        "setter": SettingsManager.set_rate_limit_cooldown,
        "range": (0, 3600),
        "unit": "сек",
        "name": "Задержка",
        "description": "секунд"
    },
    "max_question": {
        "command": "set_max_question",
        "getter": SettingsManager.get_max_question_length,
        "setter": SettingsManager.set_max_question_length,
        "range": (10, 10000),
        "unit": "символов",
        "name": "Максимальная длина вопроса",
        "description": "символов"
    },
    "max_answer": {
        "command": "set_max_answer",
        "getter": SettingsManager.get_max_answer_length,
        "setter": SettingsManager.set_max_answer_length,
        "range": (10, 10000),
        "unit": "символов",
        "name": "Максимальная длина ответа",
        "description": "символов"
    },
    "per_page": {
        "command": "set_per_page",
        "getter": SettingsManager.get_questions_per_page,
        "setter": SettingsManager.set_questions_per_page,
        "range": (1, 50),
        "unit": "",
        "name": "Вопросов на странице",
        "description": "вопросов на странице"
    },
    "max_pages": {
        "command": "set_max_pages",
        "getter": SettingsManager.get_max_pages_to_show,
        "setter": SettingsManager.set_max_pages_to_show,
        "range": (10, 1000),
        "unit": "",
        "name": "Максимум страниц",
        "description": "страниц"
    }
}


@router.message(Command("limits"))
async def limits_command(message: Message):
    """Show current limits and restrictions."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    try:
        # Get current values from DB
        rate_limit = await SettingsManager.get_rate_limit_per_hour()
        cooldown = await SettingsManager.get_rate_limit_cooldown()
        max_question = await SettingsManager.get_max_question_length()
        max_answer = await SettingsManager.get_max_answer_length()
        per_page = await SettingsManager.get_questions_per_page()
        max_pages = await SettingsManager.get_max_pages_to_show()

        commands_list = "\n".join(
            f"- /{config['command']} Значение - {config['description']} "
            f"({config['range'][0]}-{config['range'][1]})"
            for config in LIMIT_COMMANDS.values()
        )

        limits_text = f"""
⚙️ <b>Текущие лимиты и ограничения</b>

📊 <b>Лимиты пользователей:</b>
- Вопросов в час: {rate_limit}
- Задержка между вопросами: {cooldown} сек
- Макс. длина вопроса: {max_question} символов
- Макс. длина ответа: {max_answer} символов

📄 <b>Настройки пагинации:</b>
- Вопросов на странице: {per_page}
- Максимум страниц: {max_pages}

💡 <b>Команды для изменения:</b>
{commands_list}
"""
        await message.answer(limits_text)
        logger.info(f"Admin {message.from_user.id} viewed limits")

    except Exception as e:
        await message.answer("❌ Ошибка при получении настроек")
        logger.error(f"Error getting limits: {e}")


async def handle_set_command(message: Message, config: dict):
    """Общая обработка команд установки лимитов."""
    args = message.text.split(maxsplit=1)
    min_val, max_val = config["range"]
    unit = config["unit"]
    
    if len(args) < 2:
        current = await config["getter"]()
        unit_text = f" {unit}" if unit else ""
        await message.answer(
            f"ℹ️ Текущее значение: <b>{current}{unit_text}</b>\n\n"
            f"📝 Чтобы изменить, отправьте:\n"
            f"/{config['command']} Значение от {min_val} до {max_val}"
        )
        return

    try:
        new_value = int(args[1])
        if await config["setter"](new_value):
            unit_text = f" {unit}" if unit else ""
            await message.answer(
                f"✅ {config['name']} изменено на {new_value}{unit_text}"
            )
            logger.info(f"Admin updated {config['command']} to: {new_value}")
        else:
            await message.answer(f"❌ Неверное значение. Допустимо: {min_val}-{max_val}")
    except ValueError:
        await message.answer("❌ Укажите число")


# Динамическая регистрация обработчиков команд
for key, config in LIMIT_COMMANDS.items():
    command = config["command"]
    
    @router.message(Command(command))
    async def set_command_handler(message: Message, config=config):
        if message.from_user.id != ADMIN_ID:
            await message.answer(ERROR_ADMIN_ONLY)
            return
        await handle_set_command(message, config)


@router.message(Command("reset_limits"))
async def reset_limits_command(message: Message):
    """Reset all limits to default values."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    try:
        # Reset to values from config.py
        from config import (
            RATE_LIMIT_QUESTIONS_PER_HOUR,
            RATE_LIMIT_COOLDOWN_SECONDS,
            MAX_QUESTION_LENGTH,
            MAX_ANSWER_LENGTH,
            QUESTIONS_PER_PAGE,
            MAX_PAGES_TO_SHOW
        )

        await SettingsManager.set_rate_limit_per_hour(RATE_LIMIT_QUESTIONS_PER_HOUR)
        await SettingsManager.set_rate_limit_cooldown(RATE_LIMIT_COOLDOWN_SECONDS)
        await SettingsManager.set_max_question_length(MAX_QUESTION_LENGTH)
        await SettingsManager.set_max_answer_length(MAX_ANSWER_LENGTH)
        await SettingsManager.set_questions_per_page(QUESTIONS_PER_PAGE)
        await SettingsManager.set_max_pages_to_show(MAX_PAGES_TO_SHOW)

        await message.answer(
            "✅ Все лимиты сброшены на значения по умолчанию\n\n"
            "Используйте /limits для просмотра"
        )
        logger.info("Admin reset all limits to defaults")

    except Exception as e:
        await message.answer("❌ Ошибка при сбросе настроек")
        logger.error(f"Error resetting limits: {e}")