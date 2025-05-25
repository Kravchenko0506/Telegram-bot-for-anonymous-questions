"""
Admin States for Interactive Answer System
"""

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from datetime import datetime

from config import ADMIN_ID, USER_ANSWER_RECEIVED
from models.database import async_session
from models.questions import Question
from utils.logger import get_admin_logger

router = Router()
logger = get_admin_logger()

# Storage for admin states
admin_answer_states = {}


async def start_answer_mode(callback: CallbackQuery, question_id: int):
    """Start interactive answer mode for admin."""
    admin_id = callback.from_user.id
    
    try:
        # Get question details
        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question or question.is_deleted:
                await callback.answer("❌ Вопрос не найден", show_alert=True)
                return
            
            if question.is_answered:
                await callback.answer("❌ На этот вопрос уже дан ответ", show_alert=True)
                return
        
        # Set admin state
        admin_answer_states[admin_id] = {
            'question_id': question_id,
            'question_text': question.text,
            'user_id': question.user_id,
            'mode': 'waiting_answer'
        }
        
        # Send answer prompt
        answer_text = f"""
💬 <b>Режим ответа на вопрос #{question_id}</b>

<b>Вопрос:</b>
<i>{question.text}</i>

📝 <b>Напишите ваш ответ:</b>
"""
        
        from keyboards.inline import get_cancel_answer_keyboard
        keyboard = get_cancel_answer_keyboard(question_id)
        
        await callback.message.reply(
            text=answer_text,
            reply_markup=keyboard
        )
        
        await callback.answer("💡 Введите ваш ответ в следующем сообщении")
        logger.info(f"Admin {admin_id} started answer mode for question {question_id}")
        
    except Exception as e:
        await callback.answer("❌ Ошибка при переходе в режим ответа", show_alert=True)
        logger.error(f"Error starting answer mode: {e}")


async def handle_admin_answer(message: Message):
    """Handle admin's answer when in answer mode."""
    admin_id = message.from_user.id
    
    if admin_id not in admin_answer_states:
        return False
    
    state = admin_answer_states[admin_id]
    if state['mode'] != 'waiting_answer':
        return False
    
    answer_text = message.text.strip()
    question_id = state['question_id']
    user_id = state['user_id']
    question_text = state['question_text']
    
    if not answer_text:
        await message.answer("❌ Ответ не может быть пустым. Попробуйте еще раз.")
        return True
    
    try:
        # Save answer to database
        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question:
                await message.answer("❌ Вопрос не найден")
                del admin_answer_states[admin_id]
                return True
            
            question.answer = answer_text
            question.answered_at = datetime.utcnow()
            await session.commit()
        
        # Send answer to user
        user_message = USER_ANSWER_RECEIVED.format(
            question=question_text,
            answer=answer_text
        )
        
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=user_message
            )
            
            confirmation = f"""
✅ <b>Ответ успешно отправлен!</b>

<b>Вопрос:</b> {question_text[:100]}...
<b>Ваш ответ:</b> {answer_text[:100]}...
<b>Пользователю:</b> #{user_id}
"""
            
            await message.answer(confirmation)
            logger.info(f"Answer sent for question {question_id}")
            
        except Exception as e:
            await message.answer("✅ Ответ сохранен, но не удалось отправить пользователю.")
            logger.error(f"Failed to send answer to user {user_id}: {e}")
        
        # Clear admin state
        del admin_answer_states[admin_id]
        return True
        
    except Exception as e:
        await message.answer("❌ Ошибка при сохранении ответа")
        logger.error(f"Error saving answer: {e}")
        del admin_answer_states[admin_id]
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
        logger.info(f"Admin canceled answer mode for question {question_id}")
    else:
        await callback.answer("Режим ответа уже завершен")


def is_admin_in_answer_mode(admin_id: int) -> bool:
    """Check if admin is currently in answer mode."""
    return admin_id in admin_answer_states and admin_answer_states[admin_id]['mode'] == 'waiting_answer'