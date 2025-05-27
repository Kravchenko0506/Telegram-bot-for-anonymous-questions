"""
Admin States - Robust Version with Error Protection
"""

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timedelta

from config import ADMIN_ID, USER_ANSWER_RECEIVED
from models.database import async_session
from models.questions import Question
from utils.logger import get_admin_logger

router = Router()
logger = get_admin_logger()

# Storage for admin states with timestamp for cleanup
admin_answer_states = {}


def cleanup_expired_states():
    """Clean up states older than 10 minutes."""
    current_time = datetime.utcnow()
    expired_admins = []
    
    for admin_id, state in admin_answer_states.items():
        if 'created_at' in state:
            time_diff = current_time - state['created_at']
            if time_diff > timedelta(minutes=10):
                expired_admins.append(admin_id)
                logger.warning(f"Cleaning up expired state for admin {admin_id}")
    
    for admin_id in expired_admins:
        del admin_answer_states[admin_id]


async def start_answer_mode(callback: CallbackQuery, question_id: int):
    """Start interactive answer mode for admin."""
    admin_id = callback.from_user.id
    
    try:
        # Clean up any expired states
        cleanup_expired_states()
        
        # Get question details
        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question or question.is_deleted:
                await callback.answer("❌ Вопрос не найден", show_alert=True)
                return
            
            if question.is_answered:
                await callback.answer("❌ На этот вопрос уже дан ответ", show_alert=True)
                return
        
        # Clear any existing state for this admin
        if admin_id in admin_answer_states:
            logger.warning(f"Admin {admin_id} already in answer mode, clearing previous state")
            del admin_answer_states[admin_id]
        
        # Set admin state with timestamp
        admin_answer_states[admin_id] = {
            'question_id': question_id,
            'question_text': question.text,
            'user_id': question.user_id,
            'mode': 'waiting_answer',
            'created_at': datetime.utcnow()
        }
        
        # Send answer prompt
        answer_text = f"""💬 <b>Режим ответа на вопрос #{question_id}</b>

<b>Вопрос:</b>
<i>{question.text}</i>

📝 <b>Напишите ваш ответ:</b>

<i>⏰ Режим ответа автоматически отключится через 10 минут</i>"""
        
        from keyboards.inline import get_cancel_answer_keyboard
        keyboard = get_cancel_answer_keyboard(question_id)
        
        await callback.message.reply(
            text=answer_text,
            reply_markup=keyboard
        )
        
        await callback.answer("💡 Введите ваш ответ в следующем сообщении")
        logger.info(f"Admin {admin_id} started answer mode for question {question_id}")
        
    except Exception as e:
        # Clean up state on error
        if admin_id in admin_answer_states:
            del admin_answer_states[admin_id]
        await callback.answer("❌ Ошибка при переходе в режим ответа", show_alert=True)
        logger.error(f"Error starting answer mode: {e}")


async def handle_admin_answer(message: Message):
    """Handle admin's answer when in answer mode."""
    admin_id = message.from_user.id
    
    # Clean up expired states first
    cleanup_expired_states()
    
    if admin_id not in admin_answer_states:
        logger.warning(f"Admin {admin_id} not in answer mode")
        return False
    
    state = admin_answer_states[admin_id]
    
    if state['mode'] != 'waiting_answer':
        logger.warning(f"Admin {admin_id} in wrong mode: {state['mode']}")
        # Clean up bad state
        del admin_answer_states[admin_id]
        return False
    
    answer_text = message.text.strip()
    question_id = state['question_id']
    user_id = state['user_id']
    question_text = state['question_text']
    
    if not answer_text:
        await message.answer("❌ Ответ не может быть пустым. Попробуйте еще раз.")
        return True
    
    # Immediately clear admin state to prevent double processing
    del admin_answer_states[admin_id]
    logger.info(f"Admin {admin_id} state cleared for question {question_id}")
    
    try:
        # Save answer to database
        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question:
                await message.answer("❌ Вопрос не найден")
                return True
            
            if question.is_answered:
                await message.answer("❌ На этот вопрос уже был дан ответ")
                return True
            
            question.answer = answer_text
            question.answered_at = datetime.utcnow()
            await session.commit()
            
            logger.info(f"Answer saved for question {question_id}")
        
        # Try to send answer to user
        try:
            from keyboards.inline import get_user_question_sent_keyboard
            from models.user_states import UserStateManager
            keyboard = get_user_question_sent_keyboard()
            
            user_message_with_button = USER_ANSWER_RECEIVED.format(
                question=question_text,
                answer=answer_text
            ) + "\n\n💬 <b>Хотите задать новый вопрос?</b>"
            
            await message.bot.send_message(
                chat_id=user_id,
                text=user_message_with_button,
                reply_markup=keyboard
            )
            
            # Set user state
            await UserStateManager.set_user_state(user_id, UserStateManager.STATE_QUESTION_SENT)
            
            # Success confirmation
            confirmation_text = f"""✅ <b>Ответ успешно отправлен!</b>

<b>Вопрос:</b> {question_text[:100]}...
<b>Ваш ответ:</b> {answer_text[:100]}...

<i>Ответ доставлен пользователю анонимно</i>"""
            
            await message.answer(confirmation_text)
            logger.info(f"Answer sent successfully for question {question_id}")
            
        except Exception as e:
            logger.error(f"Failed to send answer to user {user_id}: {e}")
            await message.answer(
                f"✅ <b>Ответ сохранен!</b>\n\n"
                f"<b>Вопрос:</b> {question_text[:100]}...\n"
                f"<b>Ваш ответ:</b> {answer_text[:100]}...\n\n"
                f"⚠️ Не удалось отправить пользователю (возможно, заблокировал бота)."
            )
        
        return True
        
    except Exception as e:
        await message.answer("❌ Ошибка при сохранении ответа")
        logger.error(f"Error saving answer: {e}")
        return True


async def cancel_answer_mode(callback: CallbackQuery):
    """Cancel answer mode for admin."""
    admin_id = callback.from_user.id
    
    if admin_id in admin_answer_states:
        question_id = admin_answer_states[admin_id]['question_id']
        del admin_answer_states[admin_id]
        
        await callback.message.edit_text(
            "❌ Режим ответа отменен",
            reply_markup=None
        )
        
        await callback.answer("Режим ответа отменен")
        logger.info(f"Admin {admin_id} canceled answer mode for question {question_id}")
    else:
        await callback.answer("Режим ответа уже завершен")


def is_admin_in_answer_mode(admin_id: int) -> bool:
    """Check if admin is currently in answer mode."""
    # Clean up expired states first
    cleanup_expired_states()
    
    in_mode = admin_id in admin_answer_states and admin_answer_states[admin_id]['mode'] == 'waiting_answer'
    
    if in_mode:
        logger.debug(f"Admin {admin_id} is in answer mode for question {admin_answer_states[admin_id]['question_id']}")
    
    return in_mode


def get_admin_state_info(admin_id: int) -> dict:
    """Get admin state info for debugging."""
    if admin_id in admin_answer_states:
        return admin_answer_states[admin_id]
    return {}


def force_clear_admin_state(admin_id: int) -> bool:
    """Force clear admin state (for emergency use)."""
    if admin_id in admin_answer_states:
        del admin_answer_states[admin_id]
        logger.warning(f"Force cleared state for admin {admin_id}")
        return True
    return False