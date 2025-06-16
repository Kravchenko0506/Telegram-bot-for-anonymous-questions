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
from utils.logger import get_admin_logger

router = Router()
logger = get_admin_logger()


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
- /set_rate_limit <число> - вопросов в час (1-100)
- /set_cooldown <секунды> - задержка (0-3600)
- /set_max_question <длина> - макс. вопрос (10-10000)
- /set_max_answer <длина> - макс. ответ (10-10000)
- /set_per_page <число> - на странице (1-50)
- /set_max_pages <число> - макс. страниц (10-1000)
"""
        await message.answer(limits_text)
        logger.info(f"Admin {message.from_user.id} viewed limits")

    except Exception as e:
        await message.answer("❌ Ошибка при получении настроек")
        logger.error(f"Error getting limits: {e}")


@router.message(Command("set_rate_limit"))
async def set_rate_limit_command(message: Message):
    """Set questions per hour limit."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = await SettingsManager.get_rate_limit_per_hour()
        await message.answer(
            f"ℹ️ Текущий лимит: <b>{current}</b> вопросов в час\n\n"
            "📝 Чтобы изменить, отправьте:\n"
            "/set_rate_limit <i>число от 1 до 100</i>"
        )
        return

    try:
        new_value = int(args[1])
        if await SettingsManager.set_rate_limit_per_hour(new_value):
            await message.answer(
                f"✅ Лимит вопросов изменен на {new_value} в час"
            )
            logger.info(f"Admin updated rate limit to: {new_value}")
        else:
            await message.answer("❌ Неверное значение. Допустимо: 1-100")
    except ValueError:
        await message.answer("❌ Укажите число")


@router.message(Command("set_cooldown"))
async def set_cooldown_command(message: Message):
    """Set cooldown between questions."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = await SettingsManager.get_rate_limit_cooldown()
        await message.answer(
            f"ℹ️ Текущая задержка: <b>{current}</b> секунд\n\n"
            "📝 Чтобы изменить, отправьте:\n"
            "/set_cooldown <i>секунды от 0 до 3600</i>"
        )
        return

    try:
        new_value = int(args[1])
        if await SettingsManager.set_rate_limit_cooldown(new_value):
            await message.answer(
                f"✅ Задержка изменена на {new_value} секунд"
            )
            logger.info(f"Admin updated cooldown to: {new_value}")
        else:
            await message.answer("❌ Неверное значение. Допустимо: 0-3600 секунд")
    except ValueError:
        await message.answer("❌ Укажите число")


@router.message(Command("set_max_question"))
async def set_max_question_command(message: Message):
    """Set maximum question length."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = await SettingsManager.get_max_question_length()
        await message.answer(
            f"ℹ️ Текущий максимум: <b>{current}</b> символов\n\n"
            "📝 Чтобы изменить, отправьте:\n"
            "/set_max_question <i>длина от 10 до 10000</i>"
        )
        return

    try:
        new_value = int(args[1])
        if await SettingsManager.set_max_question_length(new_value):
            await message.answer(
                f"✅ Максимальная длина вопроса изменена на {new_value} символов"
            )
            logger.info(f"Admin updated max question length to: {new_value}")
        else:
            await message.answer("❌ Неверное значение. Допустимо: 10-10000")
    except ValueError:
        await message.answer("❌ Укажите число")


@router.message(Command("set_max_answer"))
async def set_max_answer_command(message: Message):
    """Set maximum answer length."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = await SettingsManager.get_max_answer_length()
        await message.answer(
            f"ℹ️ Текущий максимум: <b>{current}</b> символов\n\n"
            "📝 Чтобы изменить, отправьте:\n"
            "/set_max_answer <i>длина от 10 до 10000</i>"
        )
        return

    try:
        new_value = int(args[1])
        if await SettingsManager.set_max_answer_length(new_value):
            await message.answer(
                f"✅ Максимальная длина ответа изменена на {new_value} символов"
            )
            logger.info(f"Admin updated max answer length to: {new_value}")
        else:
            await message.answer("❌ Неверное значение. Допустимо: 10-10000")
    except ValueError:
        await message.answer("❌ Укажите число")


@router.message(Command("set_per_page"))
async def set_per_page_command(message: Message):
    """Set questions per page."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = await SettingsManager.get_questions_per_page()
        await message.answer(
            f"ℹ️ Текущее значение: <b>{current}</b> вопросов на странице\n\n"
            "📝 Чтобы изменить, отправьте:\n"
            "/set_per_page <i>число от 1 до 50</i>"
        )
        return

    try:
        new_value = int(args[1])
        if await SettingsManager.set_questions_per_page(new_value):
            await message.answer(
                f"✅ Количество вопросов на странице изменено на {new_value}"
            )
            logger.info(f"Admin updated questions per page to: {new_value}")
        else:
            await message.answer("❌ Неверное значение. Допустимо: 1-50")
    except ValueError:
        await message.answer("❌ Укажите число")


@router.message(Command("set_max_pages"))
async def set_max_pages_command(message: Message):
    """Set maximum pages to show."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = await SettingsManager.get_max_pages_to_show()
        await message.answer(
            f"ℹ️ Текущее значение: <b>{current}</b> страниц\n\n"
            "📝 Чтобы изменить, отправьте:\n"
            "/set_max_pages <i>число от 10 до 1000</i>"
        )
        return

    try:
        new_value = int(args[1])
        if await SettingsManager.set_max_pages_to_show(new_value):
            await message.answer(
                f"✅ Максимальное количество страниц изменено на {new_value}"
            )
            logger.info(f"Admin updated max pages to: {new_value}")
        else:
            await message.answer("❌ Неверное значение. Допустимо: 10-1000")
    except ValueError:
        await message.answer("❌ Укажите число")


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
