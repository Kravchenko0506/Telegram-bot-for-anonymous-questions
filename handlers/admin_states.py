"""Admin state management for question answering mode."""
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

# Admin answer state storage
_admin_answer_states = {}

def _preview_text(text: str, max_len: int = 100) -> str:
    """Truncate text for preview display."""
    return text if len(text) <= max_len else text[:max_len] + "..."

def _cleanup_expired_states():
    """Clean up expired states (older than 30 minutes)."""
    cutoff = datetime.utcnow() - timedelta(minutes=30)
    expired = [
        admin_id for admin_id, state in _admin_answer_states.items()
        if state.get('created_at', cutoff) < cutoff
    ]
    
    for admin_id in expired:
        _admin_answer_states.pop(admin_id, None)
        logger.warning(f"Cleaned expired state for admin {admin_id}")

def is_admin_in_answer_mode(admin_id: int) -> bool:
    """Check if admin is currently in answer mode."""
    _cleanup_expired_states()
    state = _admin_answer_states.get(admin_id)
    return bool(state and state.get('mode') == 'waiting_answer')

async def start_answer_mode(callback: CallbackQuery, question_id: int, question=None):
    """Start answer mode for a question.
    
    Args:
        callback: Telegram callback query
        question_id: Question identifier  
        question: Optional Question object to avoid DB query
    """
    admin_id = callback.from_user.id
    _cleanup_expired_states()

    try:
        # Use provided question or fetch from DB
        if question is None:
            question = await _get_question_from_db(question_id)
            
        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return
            
        # Check if question can be answered
        if await _is_question_unanswerable(question, callback):
            return

        # Set admin state
        _admin_answer_states[admin_id] = {
            'question_id': question_id,
            'question_text': question.text or "",  # Handle None text
            'user_id': question.user_id,
            'mode': 'waiting_answer',
            'created_at': datetime.utcnow()
        }

        # Send answer interface
        await _send_answer_interface(callback, question_id, question.text or "")
        logger.info(f"Admin {admin_id} started answering question {question_id}")

    except Exception as e:
        _admin_answer_states.pop(admin_id, None)
        await callback.answer("❌ Ошибка входа в режим ответа", show_alert=True)
        logger.error(f"Error starting answer mode: {e}")


async def _get_question_from_db(question_id: int) -> Question:
    """Get question from database."""
    async with async_session() as session:
        return await session.get(Question, question_id)


async def _is_question_unanswerable(question: Question, callback: CallbackQuery) -> bool:
    """Check if question cannot be answered."""
    if not question or question.is_deleted:
        await callback.answer("❌ Вопрос не найден", show_alert=True)
        return True
        
    if question.is_answered:
        await callback.answer("❌ Уже отвечен", show_alert=True)
        return True
        
    return False


async def _send_answer_interface(callback: CallbackQuery, question_id: int, question_text: str):
    """Send answer interface for the question."""
    safe_question_text = question_text or "(пустой вопрос)"
    
    await callback.message.reply(
        f"💬 <b>Ответ на вопрос #{question_id}</b>\n\n"
        f"<b>Вопрос:</b>\n<i>{safe_question_text}</i>\n\n"
        "📝 <b>Напишите ответ:</b>\n"
        "<i>⏰ Режим ответа отключится через 30 минут</i>",
        reply_markup=get_cancel_answer_keyboard(question_id)
    )
    await callback.answer("💡 Введите ответ в следующем сообщении")


async def handle_admin_answer(message: Message):
    """Process admin's answer to a question."""
    admin_id = message.from_user.id
    _cleanup_expired_states()
    
    # Check admin state
    state = _admin_answer_states.get(admin_id)
    if not state or state.get('mode') != 'waiting_answer':
        _admin_answer_states.pop(admin_id, None)
        return False

    # Process answer text
    answer_text = message.text.strip()
    if not answer_text:
        await message.answer("❌ Ответ не может быть пустым")
        return True

    # Extract state data
    question_id = state['question_id']
    user_id = state['user_id']
    question_text = state['question_text']
    
    # Clear state immediately
    del _admin_answer_states[admin_id]
    
    try:
        # Save answer to DB
        if not await _save_answer_to_db(question_id, answer_text):
            await message.answer("❌ Вопрос недоступен")
            return True

        # Notify user
        user_notified = await _notify_user_with_answer(message, user_id, question_text, answer_text)
        
        # Confirm to admin
        await _confirm_answer_to_admin(message, question_text, answer_text, user_notified)
        logger.info(f"Answer sent for question {question_id}")
        return True
        
    except Exception as e:
        await message.answer("❌ Ошибка сохранения")
        logger.error(f"Error saving answer: {e}")
        return True


async def _save_answer_to_db(question_id: int, answer_text: str) -> bool:
    """Save answer to database."""
    async with async_session() as session:
        question = await session.get(Question, question_id)
        if not question or question.is_answered:
            return False
            
        question.answer = answer_text
        question.answered_at = datetime.utcnow()
        await session.commit()
        return True


async def _notify_user_with_answer(message: Message, user_id: int, question_text: str, answer_text: str) -> bool:
    """Send answer to user. Returns True if successful."""
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=USER_ANSWER_RECEIVED.format(question=question_text, answer=answer_text) +
                 "\n\n💬 <b>Хотите задать новый вопрос?</b>",
            reply_markup=get_user_question_sent_keyboard()
        )
        await UserStateManager.set_user_state(user_id, UserStateManager.STATE_QUESTION_SENT)
        return True
        
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")
        return False


async def _confirm_answer_to_admin(message: Message, question_text: str, answer_text: str, user_notified: bool):
    """Confirm answer delivery to admin."""
    if user_notified:
        await message.answer(
            "✅ <b>Ответ отправлен!</b>\n\n"
            f"<b>Вопрос:</b> {_preview_text(question_text)}\n"
            f"<b>Ответ:</b> {_preview_text(answer_text)}\n\n"
            "<i>Доставлено анонимно</i>"
        )
    else:
        await message.answer(
            "✅ <b>Ответ сохранен!</b>\n\n"
            f"<b>Вопрос:</b> {_preview_text(question_text)}\n"
            f"<b>Ответ:</b> {_preview_text(answer_text)}\n\n"
            "⚠️ Не удалось отправить пользователю"
        )


async def cancel_answer_mode(source):
    """Cancel answer mode from CallbackQuery or Message."""
    if isinstance(source, CallbackQuery):
        admin_id = source.from_user.id
        callback = source
        message = source.message
    elif isinstance(source, Message):
        admin_id = source.from_user.id
        callback = None
        message = source
    else:
        logger.error(f"Invalid source type for cancel_answer_mode: {type(source)}")
        return
    
    # Cancel state
    state = _admin_answer_states.pop(admin_id, None)
    if state:
        try:
            await message.edit_text("❌ Режим ответа отменен", reply_markup=None)
        except Exception:
            # If edit fails, send new message
            await message.answer("❌ Режим ответа отменен")
            
        if callback:
            await callback.answer("Отменено")
        logger.info(f"Admin {admin_id} canceled answer for question {state['question_id']}")
    else:
        if callback:
            await callback.answer("Режим ответа не активен")
        else:
            logger.warning(f"Admin {admin_id} tried to cancel inactive answer mode")


def force_clear_admin_state(admin_id: int) -> bool:
    """Force clear admin state."""
    return bool(_admin_answer_states.pop(admin_id, None))


def get_admin_state_info(admin_id: int) -> dict:
    """Get admin state info for debugging."""
    if admin_id in _admin_answer_states:
        return _admin_answer_states[admin_id]
    return {}