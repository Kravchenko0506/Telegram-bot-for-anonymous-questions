"""
Admin Handlers with Interactive Features
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
    """Handle admin callback queries only."""
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
                new_keyboard = get_admin_question_keyboard(question_id, is_favorite=question.is_favorite)
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
    """Handle pagination for questions lists."""
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
    """Show pending questions with pagination."""
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
            page = max(0, min(page, total_pages - 1))  # Ensure page is in bounds
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
            keyboard = get_pagination_keyboard(page, total_pages, "pending_page")
        
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
            
            question_keyboard = get_admin_question_keyboard(question.id, is_favorite=question.is_favorite)
            await message.answer(question_text, reply_markup=question_keyboard)
        
        logger.info(f"Admin viewed pending questions page {page + 1}/{total_pages} ({len(questions)} questions)")
        
    except Exception as e:
        error_text = "❌ Ошибка при получении неотвеченных вопросов"
        if edit_message:
            await message.edit_text(error_text, reply_markup=None)
        else:
            await message.answer(error_text)
        logger.error(f"Error getting pending questions: {e}")


async def show_favorites_page(message: Message, page: int = 0, edit_message: bool = False):
    """Show favorite questions with pagination."""
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
            page = max(0, min(page, total_pages - 1))  # Ensure page is in bounds
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
            keyboard = get_pagination_keyboard(page, total_pages, "favorites_page")
        
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

📅 {created_at} | {status}
"""
            
            question_keyboard = get_favorite_question_keyboard(question.id)
            await message.answer(question_text, reply_markup=question_keyboard)
        
        logger.info(f"Admin viewed favorites page {page + 1}/{total_pages} ({len(questions)} questions)")
        
    except Exception as e:
        error_text = "❌ Ошибка при получении избранных вопросов"
        if edit_message:
            await message.edit_text(error_text, reply_markup=None)
        else:
            await message.answer(error_text)
        logger.error(f"Error getting favorite questions: {e}")


async def handle_clear_all_questions(callback: CallbackQuery):
    """Handle clearing all questions from database."""
    try:
        async with async_session() as session:
            # Soft delete all questions
            stmt = select(Question).where(Question.is_deleted == False)
            result = await session.execute(stmt)
            questions = result.scalars().all()
            
            count = 0
            for question in questions:
                question.is_deleted = True
                question.deleted_at = datetime.utcnow()
                count += 1
            
            await session.commit()
        
        await callback.message.edit_text(
            f"✅ <b>Очистка завершена!</b>\n\n"
            f"Удалено вопросов: {count}\n\n"
            f"<i>Все вопросы перемещены в архив.</i>",
            reply_markup=None
        )
        
        await callback.answer(f"Удалено {count} вопросов")
        logger.info(f"Admin cleared {count} questions")
        
    except Exception as e:
        await callback.message.edit_text(
            "❌ Ошибка при очистке вопросов",
            reply_markup=None
        )
        await callback.answer("Ошибка при очистке", show_alert=True)
        logger.error(f"Error clearing questions: {e}")


@router.message(Command("test"))
async def test_command(message: Message):
    """Test command to check if commands work."""
    logger.info(f"Test command from user {message.from_user.id}")
    await message.answer(f"✅ Команды работают! Ваш ID: {message.from_user.id}")


@router.message(Command("admin"))
async def admin_command(message: Message):
    """Enhanced admin command with actual functions."""
    user_id = message.from_user.id
    logger.info(f"Admin command from user {user_id}, ADMIN_ID={ADMIN_ID}, match={user_id == ADMIN_ID}")
    
    if user_id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        logger.warning(f"Non-admin access attempt: {user_id}")
        return
    
    logger.info("Admin access granted, processing command")
    
    try:
        # Get quick stats
        async with async_session() as session:
            total = await session.scalar(
                select(func.count(Question.id)).where(Question.is_deleted == False)
            ) or 0
            
            pending = await session.scalar(
                select(func.count(Question.id)).where(
                    Question.is_deleted == False,
                    Question.answer.is_(None)
                )
            ) or 0
            
            favorites = await session.scalar(
                select(func.count(Question.id)).where(
                    Question.is_deleted == False,
                    Question.is_favorite == True
                )
            ) or 0
        
        admin_panel = f"""
🛠 <b>Админ-панель</b>

📊 <b>Быстрая статистика:</b>
• Всего вопросов: {total}
• Ожидают ответа: {pending}
• В избранном: {favorites}

📋 <b>Команды:</b>
• /stats - Подробная статистика
• /pending - Неотвеченные вопросы ({pending})
• /favorites - Избранные вопросы ({favorites})

💡 <b>Как отвечать:</b>
1. Нажмите "✉️ Ответить" под вопросом
2. Напишите ваш ответ
3. Ответ автоматически отправится пользователю

🔗 <b>Ссылка для пользователей:</b>
<code>https://t.me/{BOT_USERNAME}?start=channel</code>
"""
        
        await message.answer(admin_panel)
        logger.info(f"Admin panel accessed with stats: total={total}, pending={pending}, favorites={favorites}")
        
    except Exception as e:
        await message.answer("❌ Ошибка при загрузке админ-панели")
        logger.error(f"Error in admin command: {e}")


@router.message(Command("favorites"))
async def favorites_command(message: Message):
    """Show favorites with pagination."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    
    await show_favorites_page(message, page=0)


@router.message(Command("pending"))
async def pending_command(message: Message):
    """Show pending questions with pagination."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    
    await show_pending_questions_page(message, page=0)


@router.message(Command("stats"))
async def stats_command(message: Message):
    """Enhanced statistics."""
    user_id = message.from_user.id
    logger.info(f"Stats command from user {user_id}")
    
    if user_id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    
    try:
        async with async_session() as session:
            total = await session.scalar(
                select(func.count(Question.id)).where(Question.is_deleted == False)
            ) or 0
            
            answered = await session.scalar(
                select(func.count(Question.id)).where(
                    Question.is_deleted == False,
                    Question.answer.is_not(None)
                )
            ) or 0
            
            favorites = await session.scalar(
                select(func.count(Question.id)).where(
                    Question.is_deleted == False,
                    Question.is_favorite == True
                )
            ) or 0
            
            deleted = await session.scalar(
                select(func.count(Question.id)).where(Question.is_deleted == True)
            ) or 0
        
        response_rate = (answered / max(total, 1) * 100)
        
        stats_text = f"""
📊 <b>Статистика вопросов</b>

📝 Всего вопросов: {total}
✅ Отвеченных: {answered}
⏳ Ожидают ответа: {total - answered}
⭐ В избранном: {favorites}
🗑️ Удаленных: {deleted}

📈 Процент ответов: {response_rate:.1f}%

💡 <b>Пагинация:</b>
Вопросы показываются по {QUESTIONS_PER_PAGE} на странице
"""
        
        keyboard = get_stats_keyboard()
        await message.answer(stats_text, reply_markup=keyboard)
        logger.info(f"Enhanced stats viewed: total={total}, answered={answered}, rate={response_rate:.1f}%")
        
    except Exception as e:
        await message.answer("❌ Ошибка при получении статистики")
        logger.error(f"Error getting enhanced stats: {e}")


@router.message(Command("set_author"))
async def set_author_command(message: Message):
    """Command to change author name."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    
    # Check if user provided new name
    command_text = message.text.strip()
    if len(command_text.split()) < 2:
        current_name = await SettingsManager.get_author_name()
        await message.answer(
            f"✏️ <b>Текущее имя автора:</b> {current_name}\n\n"
            f"Для изменения используйте:\n"
            f"<code>/set_author Новое имя автора</code>"
        )
        return
    
    # Extract new name (everything after the command)
    new_name = command_text[len("/set_author"):].strip()
    
    if not new_name:
        await message.answer("❌ Имя автора не может быть пустым.")
        return
    
    if len(new_name) > 100:
        await message.answer("❌ Имя автора слишком длинное (максимум 100 символов).")
        return
    
    try:
        success = await SettingsManager.set_author_name(new_name)
        if success:
            await message.answer(
                f"✅ <b>Имя автора обновлено!</b>\n\n"
                f"<b>Новое значение:</b> {new_name}\n\n"
                f"<i>Изменения будут видны новым пользователям при запуске бота.</i>"
            )
            logger.info(f"Admin updated author name to: {new_name}")
        else:
            await message.answer("❌ Ошибка при сохранении имени автора.")
    except Exception as e:
        await message.answer("❌ Ошибка при обновлении настройки.")
        logger.error(f"Error updating author name: {e}")


@router.message(Command("set_info"))
async def set_info_command(message: Message):
    """Command to change author info."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    
    # Check if user provided new info
    command_text = message.text.strip()
    if len(command_text.split()) < 2:
        current_info = await SettingsManager.get_author_info()
        await message.answer(
            f"📝 <b>Текущее описание канала:</b> {current_info}\n\n"
            f"Для изменения используйте:\n"
            f"<code>/set_info Новое описание канала</code>"
        )
        return
    
    # Extract new info (everything after the command)
    new_info = command_text[len("/set_info"):].strip()
    
    if not new_info:
        await message.answer("❌ Описание канала не может быть пустым.")
        return
    
    if len(new_info) > 500:
        await message.answer("❌ Описание канала слишком длинное (максимум 500 символов).")
        return
    
    try:
        success = await SettingsManager.set_author_info(new_info)
        if success:
            await message.answer(
                f"✅ <b>Описание канала обновлено!</b>\n\n"
                f"<b>Новое значение:</b> {new_info}\n\n"
                f"<i>Изменения будут видны новым пользователям при запуске бота.</i>"
            )
            logger.info(f"Admin updated author info to: {new_info}")
        else:
            await message.answer("❌ Ошибка при сохранении описания канала.")
    except Exception as e:
        await message.answer("❌ Ошибка при обновлении настройки.")
        logger.error(f"Error updating author info: {e}")


@router.message(Command("settings"))
async def settings_command(message: Message):
    """Show current bot settings."""
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    
    try:
        author_name = await SettingsManager.get_author_name()
        author_info = await SettingsManager.get_author_info()
        
        settings_text = f"""
⚙️ <b>Текущие настройки бота</b>

👤 <b>Имя автора:</b> {author_name}
📝 <b>Описание канала:</b> {author_info}

<b>Команды для изменения:</b>
• <code>/set_author Новое имя</code>
• <code>/set_info Новое описание</code>

<i>Изменения применяются сразу для новых пользователей.</i>
"""
        
        await message.answer(settings_text)
        logger.info("Admin viewed current settings")
        
    except Exception as e:
        await message.answer("❌ Ошибка при получении настроек")
        logger.error(f"Error getting settings: {e}")
        
def get_questions_per_page() -> int:
    """Get questions per page safely."""
    return 10