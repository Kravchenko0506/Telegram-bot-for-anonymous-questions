"""Admin state management for answering questions."""
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timedelta

from config import ADMIN_ID, USER_ANSWER_RECEIVED
from models.database import async_session
from models.questions import Question
from utils.logging_setup import get_logger
from models.user_states import UserStateManager
from keyboards.inline import get_cancel_answer_keyboard, get_user_question_sent_keyboard

router = Router()
logger = get_logger(__name__)

# In-memory storage for admin answer states
admin_answer_states = {}

def preview_text(text: str, max_len: int = 100) -> str:
    """Truncate text for preview."""
    return text if len(text) <= max_len else text[:max_len] + "..."

def cleanup_expired_states():
    """Remove states older than 30 minutes."""
    cutoff = datetime.utcnow() - timedelta(minutes=30)
    expired = [
        admin_id for admin_id, state in admin_answer_states.items()
        if state.get('created_at', cutoff) < cutoff
    ]
    
    for admin_id in expired:
        admin_answer_states.pop(admin_id, None)
        logger.warning(f"Cleaned expired state for admin {admin_id}")

def is_admin_answering(admin_id: int) -> bool:
    """Check if admin is currently answering."""
    cleanup_expired_states()
    state = admin_answer_states.get(admin_id)
    return state and state.get('mode') == 'waiting_answer'

async def start_answer_mode(callback: CallbackQuery, question_id: int, question=None):
    """Enter answer mode for a question."""
    admin_id = callback.from_user.id
    cleanup_expired_states()

    try:
        # Fetch question if not provided
        if not question:
            async with async_session() as session:
                question = await session.get(Question, question_id)
        
        if not question or question.is_deleted:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return
            
        if question.is_answered:
            await callback.answer("❌ Уже отвечен", show_alert=True)
            return

        # Set answer state
        admin_answer_states[admin_id] = {
            'question_id': question_id,
            'question_text': question.text or "",
            'user_id': question.user_id,
            'mode': 'waiting_answer',
            'created_at': datetime.utcnow()
        }

        # Show answer interface
        await callback.message.reply(
            f"💬 <b>Ответ на вопрос #{question_id}</b>\n\n"
            f"<b>Вопрос:</b>\n<i>{question.text}</i>\n\n"
            "📝 <b>Напишите ответ:</b>\n"
            "<i>⏰ Режим ответа отключится через 30 минут</i>",
            reply_markup=get_cancel_answer_keyboard(question_id)
        )
        await callback.answer("💡 Введите ответ в следующем сообщении")
        logger.info(f"Admin {admin_id} answering question {question_id}")

    except Exception as e:
        admin_answer_states.pop(admin_id, None)
        await callback.answer("❌ Ошибка входа в режим ответа", show_alert=True)
        logger.error(f"Start answer error: {e}")

async def handle_admin_answer(message: Message):
    """Process admin's answer to a question."""
    admin_id = message.from_user.id
    cleanup_expired_states()
    
    state = admin_answer_states.get(admin_id)
    if not state or state.get('mode') != 'waiting_answer':
        admin_answer_states.pop(admin_id, None)
        return False

    answer_text = message.text.strip()
    if not answer_text:
        await message.answer("❌ Ответ не может быть пустым")
        return True

    # Extract state data
    question_id = state['question_id']
    user_id = state['user_id']
    question_text = state['question_text']
    
    # Clear state immediately
    del admin_answer_states[admin_id]
    
    try:
        # Save answer to DB
        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question or question.is_answered:
                await message.answer("❌ Вопрос недоступен")
                return True
                
            question.answer = answer_text
            question.answered_at = datetime.utcnow()
            await session.commit()

        # Notify user
        await _notify_user_with_answer(message, user_id, question_text, answer_text)
        
        # Confirm to admin
        await message.answer(
            "✅ <b>Ответ отправлен!</b>\n\n"
            f"<b>Вопрос:</b> {preview_text(question_text)}\n"
            f"<b>Ответ:</b> {preview_text(answer_text)}\n\n"
            "<i>Доставлено анонимно</i>"
        )
        logger.info(f"Answer sent for question {question_id}")
        return True
        
    except Exception as e:
        await message.answer("❌ Ошибка сохранения")
        logger.error(f"Save answer error: {e}")
        return True

async def _notify_user_with_answer(message: Message, user_id: int, question_text: str, answer_text: str):
    """Send answer to user with error handling."""
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=USER_ANSWER_RECEIVED.format(question=question_text, answer=answer_text) +
                 "\n\n💬 <b>Хотите задать новый вопрос?</b>",
            reply_markup=get_user_question_sent_keyboard()
        )
        await UserStateManager.set_user_state(user_id, UserStateManager.STATE_QUESTION_SENT)
        
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")
        await message.answer(
            "✅ <b>Ответ сохранен!</b>\n\n"
            f"<b>Вопрос:</b> {preview_text(question_text)}\n"
            f"<b>Ответ:</b> {preview_text(answer_text)}\n\n"
            "⚠️ Не удалось отправить пользователю"
        )

async def cancel_answer_mode(callback_or_message):
    """Cancel answer mode - accepts CallbackQuery or Message."""
    # Handle both CallbackQuery and Message
    if hasattr(callback_or_message, 'from_user'):
        # It's a CallbackQuery
        admin_id = callback_or_message.from_user.id
        callback = callback_or_message
        message = callback.message
    else:
        # It's a Message (from try/except in admin.py)
        admin_id = ADMIN_ID  # Admin is the only one who can cancel
        callback = None
        message = callback_or_message
    
    state = admin_answer_states.pop(admin_id, None)
    if state:
        await message.edit_text("❌ Режим ответа отменен", reply_markup=None)
        if callback:
            await callback.answer("Отменено")
        logger.info(f"Admin {admin_id} canceled answer for {state['question_id']}")
    else:
        if callback:
            await callback.answer("Режим ответа не активен")
        else:
            logger.warning(f"Admin {admin_id} tried to cancel non-active answer mode")

# Legacy compatibility
def is_admin_in_answer_mode(admin_id: int) -> bool:
    """Legacy function name - use is_admin_answering instead."""
    return is_admin_answering(admin_id)

def force_clear_admin_state(admin_id: int) -> bool:
    """Force clear admin state."""
    return bool(admin_answer_states.pop(admin_id, None))