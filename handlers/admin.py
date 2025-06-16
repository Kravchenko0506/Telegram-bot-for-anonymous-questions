"""
Admin Control System

A comprehensive system for managing administrative functions in the
Anonymous Questions Bot. This system provides powerful tools for
question management, settings control, and system monitoring.

Features:
- Question management
- Settings control
- Statistics tracking
- User interaction
- Content moderation
- System monitoring
- Data management

Technical Features:
- Interactive UI
- State management
- Database integration
- Error handling
- Logging system
- Security controls
"""

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from datetime import datetime
from sqlalchemy import select, func
import math

from config import (
    ADMIN_ID,
    ERROR_ADMIN_ONLY,
    SUCCESS_ADDED_TO_FAVORITES,
    SUCCESS_REMOVED_FROM_FAVORITES,
    SUCCESS_QUESTION_DELETED,
    ERROR_QUESTION_NOT_FOUND,
    SUCCESS_SETTING_UPDATED,
    ERROR_SETTING_UPDATE,
    ERROR_INVALID_VALUE,
    BOT_USERNAME
)
from models.database import async_session
from models.questions import Question
from keyboards.inline import (
    get_admin_question_keyboard,
    get_favorite_question_keyboard,
    get_stats_keyboard,
    get_clear_confirmation_keyboard,
    get_pagination_keyboard
)
from utils.logger import get_admin_logger
from handlers.admin_states import (
    start_answer_mode,
    cancel_answer_mode,
    handle_admin_answer,
    is_admin_in_answer_mode
)
from models.settings import SettingsManager

router = Router()
logger = get_admin_logger()

# Constants for pagination
QUESTIONS_PER_PAGE = 10
MAX_PAGES_TO_SHOW = 10


@router.callback_query(lambda c: c.from_user.id == ADMIN_ID)
async def admin_question_callback(callback: CallbackQuery):
    """
    Process admin callback queries with comprehensive functionality.

    This handler provides:
    - Question management
    - Favorite handling
    - Pagination control
    - Data cleanup
    - Error handling

    Features:
    - Question answering
    - Favorites management
    - Content deletion
    - Pagination
    - Error recovery

    Flow:
    1. Validate callback
    2. Process action
    3. Update database
    4. Provide feedback

    Args:
        callback: Admin callback query
    """
    try:
        # Handle pagination callbacks
        if callback.data.startswith("pending_page:") or callback.data.startswith("favorites_page:"):
            await handle_pagination_callback(callback)
            return

        # Handle special callbacks without question ID
        if callback.data == "clear_all_questions":
            keyboard = get_clear_confirmation_keyboard()
            await callback.message.edit_text(
                "⚠️ <b>Внимание!</b>\n\n"
                "Вы собираетесь удалить <b>ВСЕ вопросы</b> из базы данных.\n"
                "Это действие <b>необратимо</b>!\n\n"
                "Удаленные вопросы нельзя будет восстановить.",
                reply_markup=keyboard
            )
            return

        elif callback.data == "confirm_clear_all":
            await handle_clear_all_questions(callback)
            return

        elif callback.data == "cancel_clear":
            await callback.message.edit_text(
                "❌ Очистка отменена",
                reply_markup=None
            )
            await callback.answer("Очистка отменена")
            return

        # Handle question-specific callbacks
        if ":" not in callback.data:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return

        action, question_id_str = callback.data.split(":", 1)
        question_id = int(question_id_str)

        logger.info(f"Admin action: {action} on question {question_id}")

        # Handle answer cancellation
        if action == "cancel_answer":
            await cancel_answer_mode(callback)
            return

        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question or question.is_deleted:
                await callback.answer(ERROR_QUESTION_NOT_FOUND, show_alert=True)
                return

            if action == "answer":
                # Start interactive answer mode
                await start_answer_mode(callback, question_id)

            elif action == "favorite":
                question.is_favorite = not question.is_favorite
                await session.commit()

                message = SUCCESS_ADDED_TO_FAVORITES if question.is_favorite else SUCCESS_REMOVED_FROM_FAVORITES
                await callback.answer(message)

                # Update keyboard
                new_keyboard = get_admin_question_keyboard(
                    question_id, is_favorite=question.is_favorite)
                await callback.message.edit_reply_markup(reply_markup=new_keyboard)

            elif action == "remove_favorite":
                # Remove from favorites (from favorites list)
                question.is_favorite = False
                await session.commit()

                await callback.answer("⭐ Убрано из избранного")

                # Hide this question from favorites view
                await callback.message.edit_text(
                    f"⭐ <s>{callback.message.text}</s>\n\n<i>Убрано из избранного</i>",
                    reply_markup=None
                )

            elif action == "delete":
                question.is_deleted = True
                question.deleted_at = datetime.utcnow()
                await session.commit()

                await callback.answer(SUCCESS_QUESTION_DELETED)

                # Update message
                original_text = callback.message.text or ""
                deleted_text = f"🗑️ <s>{original_text}</s>\n\n<i>Вопрос удален</i>"

                try:
                    await callback.message.edit_text(deleted_text, reply_markup=None)
                except Exception:
                    pass

            else:
                await callback.answer("❌ Неизвестное действие", show_alert=True)

    except Exception as e:
        await callback.answer("❌ Произошла ошибка", show_alert=True)
        logger.error(f"Error in admin callback: {e}")


async def handle_pagination_callback(callback: CallbackQuery):
    """
    Process pagination callbacks for question lists.

    This function:
    - Validates page numbers
    - Updates question lists
    - Handles navigation
    - Manages errors

    Features:
    - Page validation
    - List updating
    - Error handling
    - Activity logging

    Args:
        callback: Pagination callback query
    """
    try:
        # Parse callback data
        if callback.data.startswith("pending_page:"):
            page = int(callback.data.split(":")[1])
            await show_pending_questions_page(callback.message, page, edit_message=True)
        elif callback.data.startswith("favorites_page:"):
            page = int(callback.data.split(":")[1])
            await show_favorites_page(callback.message, page, edit_message=True)

        await callback.answer()

    except Exception as e:
        await callback.answer("❌ Ошибка при переходе на страницу", show_alert=True)
        logger.error(f"Error in pagination: {e}")


async def show_pending_questions_page(message: Message, page: int = 0, edit_message: bool = False):
    """
    Display pending questions with pagination.

    This function provides:
    - Question listing
    - Page navigation
    - Empty state handling
    - Error recovery

    Features:
    - Dynamic loading
    - Page calculation
    - Empty handling
    - Error handling

    Flow:
    1. Count questions
    2. Calculate pages
    3. Load questions
    4. Display results

    Args:
        message: Telegram message
        page: Page number to show
        edit_message: Whether to edit existing message
    """
    try:
        async with async_session() as session:
            # Count total pending questions
            total_stmt = select(func.count(Question.id)).where(
                Question.answer.is_(None),
                Question.is_deleted == False
            )
            total_result = await session.execute(total_stmt)
            total_count = total_result.scalar() or 0

            if total_count == 0:
                text = "📭 Нет неотвеченных вопросов!"
                if edit_message:
                    await message.edit_text(text, reply_markup=None)
                else:
                    await message.answer(text)
                return

            # Calculate pagination
            total_pages = math.ceil(total_count / QUESTIONS_PER_PAGE)
            # Ensure page is in bounds
            page = max(0, min(page, total_pages - 1))
            offset = page * QUESTIONS_PER_PAGE

            # Get questions for current page
            stmt = select(Question).where(
                Question.answer.is_(None),
                Question.is_deleted == False
            ).order_by(Question.created_at.asc()).offset(offset).limit(QUESTIONS_PER_PAGE)

            result = await session.execute(stmt)
            questions = result.scalars().all()

        # Create header message
        header_text = f"⏳ <b>Неотвеченные вопросы</b>\n\n📊 Страница {page + 1} из {total_pages} | Всего: {total_count}"

        # Add pagination if needed
        keyboard = None
        if total_pages > 1:
            keyboard = get_pagination_keyboard(
                page, total_pages, "pending_page")

        if edit_message:
            await message.edit_text(header_text, reply_markup=keyboard)
        else:
            await message.answer(header_text, reply_markup=keyboard)

        # Send each question as separate message
        for question in questions:
            created_at = question.created_at.strftime("%d.%m.%Y %H:%M")
            favorite_mark = "⭐ " if question.is_favorite else ""

            question_text = f"""
❓ <b>{favorite_mark}Вопрос #{question.id}</b>

{question.text}

📅 {created_at}
"""

            question_keyboard = get_admin_question_keyboard(
                question.id, is_favorite=question.is_favorite)
            await message.answer(question_text, reply_markup=question_keyboard)

        logger.info(
            f"Admin viewed pending questions page {page + 1}/{total_pages} ({len(questions)} questions)")

    except Exception as e:
        error_text = "❌ Ошибка при получении неотвеченных вопросов"
        if edit_message:
            await message.edit_text(error_text, reply_markup=None)
        else:
            await message.answer(error_text)
        logger.error(f"Error getting pending questions: {e}")


async def show_favorites_page(message: Message, page: int = 0, edit_message: bool = False):
    """
    Display favorite questions with pagination.

    This function provides:
    - Favorite listing
    - Page navigation
    - Status tracking
    - Error recovery

    Features:
    - Dynamic loading
    - Page calculation
    - Status display
    - Error handling

    Flow:
    1. Count favorites
    2. Calculate pages
    3. Load questions
    4. Display results

    Args:
        message: Telegram message
        page: Page number to show
        edit_message: Whether to edit existing message
    """
    try:
        async with async_session() as session:
            # Count total favorite questions
            total_stmt = select(func.count(Question.id)).where(
                Question.is_favorite == True,
                Question.is_deleted == False
            )
            total_result = await session.execute(total_stmt)
            total_count = total_result.scalar() or 0

            if total_count == 0:
                text = "⭐ Нет избранных вопросов."
                if edit_message:
                    await message.edit_text(text, reply_markup=None)
                else:
                    await message.answer(text)
                return

            # Calculate pagination
            total_pages = math.ceil(total_count / QUESTIONS_PER_PAGE)
            # Ensure page is in bounds
            page = max(0, min(page, total_pages - 1))
            offset = page * QUESTIONS_PER_PAGE

            # Get questions for current page
            stmt = select(Question).where(
                Question.is_favorite == True,
                Question.is_deleted == False
            ).order_by(Question.created_at.desc()).offset(offset).limit(QUESTIONS_PER_PAGE)

            result = await session.execute(stmt)
            questions = result.scalars().all()

        # Create header message
        header_text = f"⭐ <b>Избранные вопросы</b>\n\n📊 Страница {page + 1} из {total_pages} | Всего: {total_count}"

        # Add pagination if needed
        keyboard = None
        if total_pages > 1:
            keyboard = get_pagination_keyboard(
                page, total_pages, "favorites_page")

        if edit_message:
            await message.edit_text(header_text, reply_markup=keyboard)
        else:
            await message.answer(header_text, reply_markup=keyboard)

        # Send each question as separate message
        for question in questions:
            created_at = question.created_at.strftime("%d.%m.%Y %H:%M")
            status = "✅ Отвечен" if question.is_answered else "⏳ Ожидает ответа"

            question_text = f"""
⭐ <b>Вопрос #{question.id}</b>

{question.text}

📅 {created_at} | {status}"""

            if question.answer:
                question_text += f"\n\n💬 <b>Ответ:</b>\n{question.answer}"

            keyboard = get_favorite_question_keyboard(question.id)
            await message.answer(question_text, reply_markup=keyboard)

        logger.info(
            f"Admin viewed favorites page {page + 1}/{total_pages} ({len(questions)} questions)")

    except Exception as e:
        error_text = "❌ Ошибка при получении избранных вопросов"
        if edit_message:
            await message.edit_text(error_text, reply_markup=None)
        else:
            await message.answer(error_text)
        logger.error(f"Error getting favorite questions: {e}")


async def handle_clear_all_questions(callback: CallbackQuery):
    """
    Process database cleanup request.

    This function:
    - Validates request
    - Performs cleanup
    - Updates status
    - Handles errors

    Features:
    - Safe deletion
    - Status tracking
    - Error handling
    - Activity logging

    Flow:
    1. Confirm action
    2. Delete questions
    3. Update status
    4. Log changes

    Args:
        callback: Cleanup confirmation callback
    """
    try:
        async with async_session() as session:
            # Mark all questions as deleted
            stmt = select(Question).where(Question.is_deleted == False)
            result = await session.execute(stmt)
            questions = result.scalars().all()

            deleted_count = 0
            for question in questions:
                question.is_deleted = True
                question.deleted_at = datetime.utcnow()
                deleted_count += 1

            await session.commit()

            await callback.message.edit_text(
                f"✅ Удалено вопросов: {deleted_count}",
                reply_markup=None
            )
            await callback.answer("Очистка завершена")
            logger.warning(f"Admin cleared {deleted_count} questions")

    except Exception as e:
        await callback.message.edit_text(
            "❌ Ошибка при очистке базы данных",
            reply_markup=None
        )
        await callback.answer("Ошибка при очистке", show_alert=True)
        logger.error(f"Error clearing database: {e}")


@router.message(Command("test"))
async def test_command(message: Message):
    """
    Test bot functionality and permissions.

    This command:
    - Validates permissions
    - Tests features
    - Reports status

    Features:
    - Permission check
    - Feature testing
    - Status reporting
    - Error handling

    Args:
        message: Command message
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    await message.answer("✅ Бот работает нормально\n\n👤 Вы администратор")


@router.message(Command("admin"))
async def admin_command(message: Message):
    """
    Display admin control panel.

    This command provides:
    - Command overview
    - Feature access
    - Status display
    - Help information

    Features:
    - Command listing
    - Permission check
    - Help display
    - Error handling

    Args:
        message: Command message
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    admin_help = f"""
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

    await message.answer(admin_help)
    logger.info(f"Admin {message.from_user.id} viewed help")


@router.message(Command("favorites"))
async def favorites_command(message: Message):
    """
    Display favorite questions list.

    This command provides:
    - Favorites listing
    - Page navigation
    - Question management
    - Status tracking

    Features:
    - Dynamic loading
    - Pagination
    - Status display
    - Error handling

    Args:
        message: Command message
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    await show_favorites_page(message)


@router.message(Command("pending"))
async def pending_command(message: Message):
    """
    Display pending questions list.

    This command provides:
    - Question listing
    - Page navigation
    - Answer management
    - Status tracking

    Features:
    - Dynamic loading
    - Pagination
    - Status display
    - Error handling

    Args:
        message: Command message
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    await show_pending_questions_page(message)


@router.message(Command("stats"))
async def stats_command(message: Message):
    """
    Display bot statistics and metrics.

    This command provides:
    - Usage statistics
    - Question metrics
    - System status
    - Performance data

    Features:
    - Data aggregation
    - Metric calculation
    - Status display
    - Error handling

    Args:
        message: Command message
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    try:
        async with async_session() as session:
            # Get total questions count
            total_stmt = select(func.count(Question.id)).where(
                Question.is_deleted == False
            )
            total_result = await session.execute(total_stmt)
            total_questions = total_result.scalar() or 0

            # Get answered questions count
            answered_stmt = select(func.count(Question.id)).where(
                Question.is_deleted == False,
                Question.answer.isnot(None)
            )
            answered_result = await session.execute(answered_stmt)
            answered_questions = answered_result.scalar() or 0

            # Get pending questions count
            pending_stmt = select(func.count(Question.id)).where(
                Question.is_deleted == False,
                Question.answer.is_(None)
            )
            pending_result = await session.execute(pending_stmt)
            pending_questions = pending_result.scalar() or 0

            # Get favorite questions count
            favorite_stmt = select(func.count(Question.id)).where(
                Question.is_deleted == False,
                Question.is_favorite == True
            )
            favorite_result = await session.execute(favorite_stmt)
            favorite_questions = favorite_result.scalar() or 0

            # Get deleted questions count
            deleted_stmt = select(func.count(Question.id)).where(
                Question.is_deleted == True
            )
            deleted_result = await session.execute(deleted_stmt)
            deleted_questions = deleted_result.scalar() or 0

            # Calculate answer rate
            answer_rate = round(
                (answered_questions / total_questions * 100) if total_questions > 0 else 0, 1)

            stats_text = f"""
📊 <b>Статистика бота</b>

📝 <b>Вопросы:</b>
• Всего: {total_questions}
• Отвечено: {answered_questions}
• Ожидают: {pending_questions}
• В избранном: {favorite_questions}
• Удалено: {deleted_questions}

📈 <b>Показатели:</b>
• Процент ответов: {answer_rate}%
"""

            keyboard = get_stats_keyboard()
            await message.answer(stats_text, reply_markup=keyboard)
            logger.info(f"Admin {message.from_user.id} viewed statistics")

    except Exception as e:
        await message.answer("❌ Ошибка при получении статистики")
        logger.error(f"Error getting statistics: {e}")


@router.message(Command("set_author"))
async def set_author_command(message: Message):
    """
    Update author name setting.

    This command provides:
    - Setting validation
    - Value updating
    - Status feedback
    - Error handling

    Features:
    - Input validation
    - Database update
    - Status display
    - Error recovery

    Flow:
    1. Validate input
    2. Update setting
    3. Confirm change
    4. Handle errors

    Args:
        message: Command message
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    # Check if command has argument
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        current_name = await SettingsManager.get_author_name()
        await message.answer(
            f"ℹ️ Текущее имя автора: <b>{current_name}</b>\n\n"
            "📝 Чтобы изменить, отправьте:\n"
            "/set_author <i>новое имя</i>"
        )
        return

    new_name = command_parts[1].strip()
    if not new_name:
        await message.answer(ERROR_INVALID_VALUE)
        return

    try:
        await SettingsManager.set_author_name(new_name)
        await message.answer(
            SUCCESS_SETTING_UPDATED.format(
                setting="имя автора",
                value=new_name
            )
        )
        logger.info(f"Admin updated author name to: {new_name}")
    except Exception as e:
        await message.answer(ERROR_SETTING_UPDATE)
        logger.error(f"Error updating author name: {e}")


@router.message(Command("set_info"))
async def set_info_command(message: Message):
    """
    Update author info setting.

    This command provides:
    - Setting validation
    - Value updating
    - Status feedback
    - Error handling

    Features:
    - Input validation
    - Database update
    - Status display
    - Error recovery

    Flow:
    1. Validate input
    2. Update setting
    3. Confirm change
    4. Handle errors

    Args:
        message: Command message
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    # Check if command has argument
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        current_info = await SettingsManager.get_author_info()
        await message.answer(
            f"ℹ️ Текущее описание: <b>{current_info}</b>\n\n"
            "📝 Чтобы изменить, отправьте:\n"
            "/set_info <i>новое описание</i>"
        )
        return

    new_info = command_parts[1].strip()
    if not new_info:
        await message.answer(ERROR_INVALID_VALUE)
        return

    try:
        await SettingsManager.set_author_info(new_info)
        await message.answer(
            SUCCESS_SETTING_UPDATED.format(
                setting="описание канала",
                value=new_info
            )
        )
        logger.info(f"Admin updated author info to: {new_info}")
    except Exception as e:
        await message.answer(ERROR_SETTING_UPDATE)
        logger.error(f"Error updating author info: {e}")


@router.message(Command("settings"))
async def settings_command(message: Message):
    """
    Display current bot settings.

    This command provides:
    - Settings overview
    - Value display
    - Help information
    - Error handling

    Features:
    - Settings loading
    - Value formatting
    - Help display
    - Error recovery

    Args:
        message: Command message
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return

    try:
        author_name = await SettingsManager.get_author_name()
        author_info = await SettingsManager.get_author_info()

        settings_text = f"""
⚙️ <b>Текущие настройки бота</b>

👤 <b>Имя автора:</b>
{author_name}

ℹ️ <b>Описание канала:</b>
{author_info}

📝 <b>Команды для изменения:</b>
• /set_author - изменить имя
• /set_info - изменить описание
"""

        await message.answer(settings_text)
        logger.info(f"Admin {message.from_user.id} viewed settings")

    except Exception as e:
        await message.answer("❌ Ошибка при получении настроек")
        logger.error(f"Error getting settings: {e}")


def get_questions_per_page() -> int:
    """
    Get questions per page setting.

    This function:
    - Returns page size
    - Handles configuration
    - Provides defaults

    Returns:
        int: Questions per page
    """
    return QUESTIONS_PER_PAGE
