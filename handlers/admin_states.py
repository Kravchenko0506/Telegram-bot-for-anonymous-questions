"""
Admin State Management System

A comprehensive system for managing admin interaction states and answer flow
in the Anonymous Questions Bot. This system provides reliable state persistence
with automatic cleanup and error recovery.

Features:
- Answer mode management
- State persistence
- Automatic cleanup
- Error handling
- User notifications
- State validation
- Activity tracking

Technical Features:
- PostgreSQL integration
- Automatic expiration
- Memory optimization
- Error recovery
- State validation
- Logging integration
"""

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timedelta

from config import ADMIN_ID, USER_ANSWER_RECEIVED
from models.database import async_session
from models.questions import Question
from utils.logging_setup import get_logger

router = Router()
logger = get_logger(__name__)

# Storage for admin states with timestamp for cleanup
admin_answer_states = {}


def cleanup_expired_states():
    """
    Clean up expired admin states to prevent memory leaks.

    This function:
    - Checks state timestamps
    - Removes expired states
    - Logs cleanup actions
    - Maintains memory usage

    Technical Details:
    - 30-minute expiration
    - Automatic cleanup
    - Memory optimization
    - Activity logging
    """
    current_time = datetime.utcnow()
    expired_admins = []

    for admin_id, state in admin_answer_states.items():
        if 'created_at' in state:
            time_diff = current_time - state['created_at']
            if time_diff > timedelta(minutes=30):
                expired_admins.append(admin_id)
                logger.warning(
                    f"Cleaning up expired state for admin {admin_id}")

    for admin_id in expired_admins:
        del admin_answer_states[admin_id]


async def start_answer_mode(callback: CallbackQuery, question_id: int, question=None):
    """
    Initialize interactive answer mode for admin.

    This function:
    - Validates question status
    - Sets up answer state
    - Sends answer interface
    - Handles errors
    - Accepts an optional question object to prevent
    creating multiple database sessions for the same operation.

    Features:
    - Question validation
    - State initialization
    - Error handling
    - User interface
    - Activity logging

    Flow:
    1. Clean expired states
    2. Validate question
    3. Initialize answer state
    4. Show answer interface
    5. Handle errors

    Args:
        callback: Telegram callback query
        question_id: Question identifier
        question: Optional Question object from existing session
    """
    admin_id = callback.from_user.id

    try:
        # Clean up any expired states
        cleanup_expired_states()

        # If question object not provided, get it from database
        if question is None:
            async with async_session() as session:
                question = await session.get(Question, question_id)
                if not question or question.is_deleted:
                    await callback.answer("❌ Вопрос не найден", show_alert=True)
                    return

                if question.is_answered:
                    await callback.answer("❌ На этот вопрос уже дан ответ", show_alert=True)
                    return
        else:
            # Use provided question object - no database query needed
            if question.is_deleted:
                await callback.answer("❌ Вопрос не найден", show_alert=True)
                return

            if question.is_answered:
                await callback.answer("❌ На этот вопрос уже дан ответ", show_alert=True)
                return

        # Clear any existing state for this admin
        if admin_id in admin_answer_states:
            logger.warning(
                f"Admin {admin_id} already in answer mode, clearing previous state")
            del admin_answer_states[admin_id]

        # Set admin state with timestamp
        # Store only plain primitives; guard against unexpected None text
        q_text = question.text if isinstance(question.text, str) else ""
        admin_answer_states[admin_id] = {
            'question_id': question_id,
            'question_text': q_text,
            'user_id': question.user_id,
            'mode': 'waiting_answer',
            'created_at': datetime.utcnow()
        }

        # Send answer prompt
        answer_text = f"""💬 <b>Режим ответа на вопрос #{question_id}</b>

<b>Вопрос:</b>
<i>{question.text}</i>

📝 <b>Напишите ваш ответ:</b>

<i>⏰ Режим ответа автоматически отключится через 30 минут</i>"""

        from keyboards.inline import get_cancel_answer_keyboard
        keyboard = get_cancel_answer_keyboard(question_id)

        await callback.message.reply(
            text=answer_text,
            reply_markup=keyboard
        )

        await callback.answer("💡 Введите ваш ответ в следующем сообщении")
        logger.info(
            f"Admin {admin_id} started answer mode for question {question_id}")

    except Exception as e:
        # Clean up state on error
        if admin_id in admin_answer_states:
            del admin_answer_states[admin_id]
        await callback.answer("❌ Ошибка при переходе в режим ответа", show_alert=True)
        logger.error(f"Error starting answer mode: {e}")


async def handle_admin_answer(message: Message):
    """
    Process admin's answer in answer mode.

    This function:
    - Validates answer state
    - Saves answer
    - Notifies user
    - Handles errors

    Features:
    - State validation
    - Answer persistence
    - User notification
    - Error handling
    - Activity logging

    Flow:
    1. Validate state
    2. Process answer
    3. Save to database
    4. Notify user
    5. Handle errors

    Args:
        message: Admin's answer message

    Returns:
        bool: True if message was handled as answer
    """
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
    question_id = state.get('question_id')
    user_id = state.get('user_id')
    question_text = state.get('question_text') or ""
    if question_id is None or user_id is None:
        logger.error(f"Corrupted admin answer state: {state}")
        return True

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

            user_message_with_button = (
                USER_ANSWER_RECEIVED.format(
                    question=question_text,
                    answer=answer_text
                ) + "\n\n💬 <b>Хотите задать новый вопрос?</b>"
            )

            await message.bot.send_message(
                chat_id=user_id,
                text=user_message_with_button,
                reply_markup=keyboard
            )

            # Set user state
            await UserStateManager.set_user_state(user_id, UserStateManager.STATE_QUESTION_SENT)

            # Success confirmation
            def _preview(s: str) -> str:
                s = s or ""
                return s if len(s) <= 100 else s[:100] + "..."

            confirmation_text = (
                "✅ <b>Ответ успешно отправлен!</b>\n\n"
                f"<b>Вопрос:</b> {_preview(question_text)}\n"
                f"<b>Ваш ответ:</b> {_preview(answer_text)}\n\n"
                "<i>Ответ доставлен пользователю анонимно</i>"
            )

            await message.answer(confirmation_text)
            logger.info(f"Answer sent successfully for question {question_id}")

        except Exception as e:
            logger.error(f"Failed to send answer to user {user_id}: {e}")

            def _preview(s: str) -> str:
                s = s or ""
                return s if len(s) <= 100 else s[:100] + "..."
            await message.answer(
                "✅ <b>Ответ сохранен!</b>\n\n"
                f"<b>Вопрос:</b> {_preview(question_text)}\n"
                f"<b>Ваш ответ:</b> {_preview(answer_text)}\n\n"
                "⚠️ Не удалось отправить пользователю (возможно, заблокировал бота)."
            )

        return True

    except Exception as e:
        await message.answer("❌ Ошибка при сохранении ответа")
        logger.error(f"Error saving answer: {e}")
        return True


async def cancel_answer_mode(callback: CallbackQuery):
    """
    Cancel admin's answer mode.

    This function:
    - Validates state
    - Cleans up state
    - Notifies admin
    - Logs action

    Features:
    - State cleanup
    - User notification
    - Error handling
    - Activity logging

    Args:
        callback: Telegram callback query
    """
    admin_id = callback.from_user.id

    if admin_id in admin_answer_states:
        question_id = admin_answer_states[admin_id]['question_id']
        del admin_answer_states[admin_id]

        await callback.message.edit_text(
            "❌ Режим ответа отменен",
            reply_markup=None
        )

        await callback.answer("Режим ответа отменен")
        logger.info(
            f"Admin {admin_id} canceled answer mode for question {question_id}")
    else:
        await callback.answer("Режим ответа уже завершен")


# ИСПРАВЛЕНИЕ: Убираем await из этой функции - она НЕ асинхронная
def is_admin_in_answer_mode(admin_id: int) -> bool:
    """Check if admin is currently in answer mode."""
    # Clean up expired states first
    cleanup_expired_states()

    in_mode = admin_id in admin_answer_states and admin_answer_states[
        admin_id]['mode'] == 'waiting_answer'

    if in_mode:
        logger.debug(
            f"Admin {admin_id} is in answer mode for question {admin_answer_states[admin_id]['question_id']}")

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
