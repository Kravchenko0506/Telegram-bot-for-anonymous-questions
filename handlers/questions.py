"""
Question Management System

A comprehensive system for handling question submission, validation,
and processing in the Anonymous Questions Bot. This system ensures
proper question flow and maintains data integrity.

Features:
- Question submission
- Input validation
- State management
- Admin notifications
- User feedback
- Spam prevention
- Privacy protection

Technical Features:
- Database integration
- State tracking
- Input sanitization
- Content moderation
- Error handling
- Logging system
"""

from email.mime import message
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from datetime import datetime
import re

from config import (
    ADMIN_ID,
    MAX_QUESTION_LENGTH,
    ERROR_MESSAGE_EMPTY,
    ERROR_DATABASE,
    USER_ANSWER_RECEIVED
)
from models.database import async_session
from models.questions import Question
from models.user_states import UserStateManager
from utils.validators import InputValidator, ContentModerator
from keyboards.inline import (
    get_admin_question_keyboard,
    get_user_question_sent_keyboard,
    get_user_blocked_keyboard
)
from utils.logging_setup import get_logger
from sqlalchemy import select
from models.settings import SettingsManager

router = Router()
logger = get_logger(__name__)


@router.callback_query()
async def user_callback_handler(callback: CallbackQuery):
    """
    Process user callback queries for question flow.

    """
    user_id = callback.from_user.id

    # Skip admin callbacks
    if user_id == ADMIN_ID:
        return

    logger.info(f"User {user_id} clicked callback: {callback.data}")

    if callback.data == "ask_another_question":
        try:
            # Allow user to ask another question
            success = await UserStateManager.allow_new_question(user_id)

            if success:
                max_length = await SettingsManager.get_max_question_length()
                await callback.message.edit_text(
                    "✍️ <b>Напишите ваш новый вопрос:</b>\n\n"
                    f"<i>Максимальная длина: {max_length} символов</i>",
                    reply_markup=None
                )
                await callback.answer("Теперь можете написать новый вопрос")
                logger.info(f"User {user_id} started asking new question")
            else:
                await callback.answer("❌ Произошла ошибка при изменении состояния", show_alert=True)
                logger.error(f"Failed to change state for user {user_id}")
        except Exception as e:
            logger.error(f"Error handling callback for user {user_id}: {e}")
            await callback.answer("❌ Произошла ошибка. Попробуйте еще раз.", show_alert=True)
    else:
        # Handle invalid callback data
        logger.warning(
            f"Invalid callback data from user {user_id}: {callback.data}")
        await callback.answer("❌ Неверный формат данных", show_alert=True)


@router.message()
async def unified_message_handler(message: Message):
    """
    Unified message processing system with role-based routing.

    """
    user_id = message.from_user.id

    # Check if admin is in answer mode first
    if user_id == ADMIN_ID:
        # Import here to avoid circular imports
        from handlers.admin_states import handle_admin_answer, is_admin_in_answer_mode

        in_answer_mode = is_admin_in_answer_mode(user_id)

        if in_answer_mode:
            await handle_admin_answer(message)
            return

        # Check if admin is replying to a question
        if message.reply_to_message:
            await handle_admin_reply(message)
            return

        # If admin sends a regular message (not in answer mode, not reply), ignore it
        logger.info(f"Admin {user_id} sent regular message, ignoring")
        return

    # Handle regular user messages with state management
    await handle_user_message(message)


async def handle_user_message(message: Message):
    """
    Process user messages with state validation.

    """
    user_id = message.from_user.id

    # Check if user can send a question
    can_send = await UserStateManager.can_send_question(user_id)

    if not can_send:
        # User already sent a question and must use inline button
        blocked_message = """
💬 <b>Ваш предыдущий вопрос отправлен!</b>

📨 Если хотите задать еще один вопрос, нажмите кнопку ниже.

<i>Это сделано для предотвращения случайной отправки команд как вопросов.</i>
"""

        keyboard = get_user_blocked_keyboard()
        await message.answer(blocked_message, reply_markup=keyboard)
        logger.info(
            f"User {user_id} blocked from sending text, must use button")
        return

    # User can send question - process it
    await handle_user_question(message)


async def handle_user_question(message: Message):
    """
    Process and validate user questions.

    """
    user_id = message.from_user.id

    # Validate message content
    if not message.text:
        await message.answer(ERROR_MESSAGE_EMPTY)
        logger.warning(f"Empty question attempt from user {user_id}")
        return

    # Validate question
    
    max_length = await SettingsManager.get_max_question_length()
    is_valid, error_message = InputValidator.validate_question(message.text, max_length)

    # Sanitize input

    if not is_valid:
        await message.answer(f"❌ {error_message}")
        logger.warning(
            f"Invalid question from user {user_id}: {error_message}")
        return
    
    question_text = InputValidator.sanitize_text(message.text, max_length)
    
    # Check for spam
    if ContentModerator.is_likely_spam(question_text):
        await message.answer(
            "❌ Ваш вопрос похож на спам. Пожалуйста, задайте настоящий вопрос."
        )
        logger.warning(
            f"Spam detected from user {user_id}: score={ContentModerator.calculate_spam_score(question_text)}")
        return

    # Log if personal data detected
    personal_data = InputValidator.extract_personal_data(question_text)
    if any(personal_data.values()):
        logger.warning(
            f"Personal data in question from user {user_id}: {list(personal_data.keys())}")

    try:
        # Save question to database
        async with async_session() as session:
            question = Question.create_new(
                text=question_text,
                user_id=user_id,
                unique_id=None
            )
            session.add(question)
            await session.commit()
            await session.refresh(question)

            question_id = question.id

        # Update user state to "question_sent"
        await UserStateManager.set_user_state(user_id, UserStateManager.STATE_QUESTION_SENT)

        logger.info(f"Question saved: ID={question_id}, user state updated")

        # Send notification to admin (with error handling)
        from utils.time_helper import format_admin_time
        sent_at = format_admin_time(datetime.utcnow())
        admin_message = f"""
❓ <b>Новый анонимный вопрос #{question_id}:</b>

{question_text}

<i>Отправлено: {sent_at}</i>
"""

        # Add spam score if suspicious
        spam_score = ContentModerator.calculate_spam_score(question_text)
        if spam_score > 0.3:
            admin_message += f"\n<i>⚠️ Спам-рейтинг: {spam_score:.1%}</i>"

        keyboard = get_admin_question_keyboard(question_id)

        try:
            await message.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                reply_markup=keyboard
            )
            logger.info(f"Admin notification sent for question {question_id}")
        except Exception as admin_error:
            logger.error(f"Failed to send admin notification: {admin_error}")
            # Don't fail the whole process if admin notification fails

        # Confirm to user with inline button for next question
        success_message = f"""
✅ <b>Ваш вопрос отправлен автору анонимно!</b>

📩 Ответ придет в этот же чат, если автор решит ответить.

💬 Хотите задать еще один вопрос?
"""

        keyboard = get_user_question_sent_keyboard()
        await message.answer(success_message, reply_markup=keyboard)

        logger.info(
            f"Question {question_id} processed successfully with validation")

    except Exception as e:
        await message.answer(ERROR_DATABASE)
        logger.error(f"Error processing question from user {user_id}: {e}")


async def handle_admin_reply(message: Message):
    """Handle admin replies to questions (legacy reply method)."""
    reply_text = message.reply_to_message.text or ""
    if not reply_text.startswith("❓") or "вопрос #" not in reply_text:
        logger.info("Admin reply not recognized as question reply")
        return

    try:
        # Extract question ID
        match = re.search(r"вопрос #(\d+):", reply_text)
        if not match:
            logger.warning("Could not extract question ID from reply")
            return

        question_id = int(match.group(1))
        answer_text = message.text.strip()

        # Validate answer
        answer_text = InputValidator.sanitize_text(answer_text)
        is_valid, error_message = InputValidator.validate_answer(answer_text)

        if not is_valid:
            await message.answer(f"❌ {error_message}")
            return

        # Get question and save answer
        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question or question.is_deleted:
                await message.answer("❌ Вопрос не найден.")
                return

            # Save answer
            question.answer = answer_text
            question.answered_at = datetime.utcnow()
            await session.commit()

            # Send answer to user
            user_message = USER_ANSWER_RECEIVED.format(
                question=question.text,
                answer=answer_text
            )

            try:
                # Add inline button for user to ask another question
                from keyboards.inline import get_user_question_sent_keyboard
                keyboard = get_user_question_sent_keyboard()

                # Combine answer with button in one message
                user_message_with_button = USER_ANSWER_RECEIVED.format(
                    question=question.text,
                    answer=answer_text
                ) + "\n\n💬 <b>Хотите задать новый вопрос?</b>"

                await message.bot.send_message(
                    chat_id=question.user_id,
                    text=user_message_with_button,
                    reply_markup=keyboard
                )

                # Set user state to "question_sent" so they must use button for next question
                await UserStateManager.set_user_state(question.user_id, UserStateManager.STATE_QUESTION_SENT)

                # Success message WITHOUT user ID
                await message.answer(
                    "✅ Ответ отправлен пользователю анонимно!\n\n"
                    f"<b>Вопрос:</b> {question.text[:100]}...\n"
                    f"<b>Ваш ответ:</b> {answer_text[:100]}..."
                )
                logger.info(
                    f"Answer sent for question {question_id} via reply")

            except Exception as e:
                await message.answer("✅ Ответ сохранен, но не удалось отправить пользователю.")
                logger.error(f"Failed to send answer to user: {e}")

    except Exception as e:
        await message.answer("❌ Ошибка при обработке ответа.")
        logger.error(f"Error processing admin reply: {e}")
