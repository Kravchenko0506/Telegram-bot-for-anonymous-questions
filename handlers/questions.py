"""Question management handlers.

User question submission flow with strict length validation (DB-configured
limit takes precedence), state transitions, admin notifications, and legacy
admin reply handling. Sanitization occurs after validation to avoid silently
truncating user input.
"""

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from datetime import datetime
import re

from config import (
    ADMIN_ID,
    ERROR_MESSAGE_EMPTY,
    ERROR_DATABASE,
    USER_ANSWER_RECEIVED
)
from models.database import async_session
from models.questions import Question
from models.user_states import UserStateManager
from models.settings import SettingsManager
from utils.validators import InputValidator, ContentModerator
from keyboards.inline import (
    get_admin_question_keyboard,
    get_user_question_sent_keyboard,
    get_user_blocked_keyboard
)
from utils.logging_setup import get_logger
from utils.time_helper import format_admin_time

router = Router()
logger = get_logger(__name__)


@router.callback_query()
async def user_callback_handler(callback: CallbackQuery):
    """Handle user-only callback queries; ignore admin callbacks."""
    user_id = callback.from_user.id

    if user_id == ADMIN_ID:
        return

    logger.info(f"User {user_id} callback: {callback.data}")

    if callback.data == "ask_another_question":
        await _handle_new_question_request(callback)
    else:
        await _handle_invalid_callback(callback)


async def _handle_new_question_request(callback: CallbackQuery):
    """Allow user to ask a new question and update state."""
    user_id = callback.from_user.id

    try:
        success = await UserStateManager.allow_new_question(user_id)

        if success:
            max_length = await SettingsManager.get_max_question_length()
            await callback.message.edit_text(
                "✍️ <b>Напишите ваш новый вопрос:</b>\n\n"
                f"<i>Максимальная длина: {max_length} символов</i>",
                reply_markup=None
            )
            await callback.answer("Теперь можете написать новый вопрос")
            logger.info(f"User {user_id} started new question")
        else:
            await callback.answer("❌ Ошибка при изменении состояния", show_alert=True)
            logger.error(f"State change failed for user {user_id}")
    except Exception as e:
        logger.error(f"Callback error for user {user_id}: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте еще раз.", show_alert=True)


async def _handle_invalid_callback(callback: CallbackQuery):
    """Reply to unsupported/invalid callback data."""
    user_id = callback.from_user.id
    logger.warning(f"Invalid callback from user {user_id}: {callback.data}")
    await callback.answer("❌ Неверный формат данных", show_alert=True)


@router.message()
async def unified_message_handler(message: Message):
    """Route messages by role: admin vs regular user."""
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        await _handle_admin_message(message)
        return

    await _handle_user_message(message)


async def _handle_admin_message(message: Message):
    """Process admin messages: answer mode, reply-based legacy flow."""
    from handlers.admin_states import handle_admin_answer, is_admin_in_answer_mode

    if is_admin_in_answer_mode(message.from_user.id):
        await handle_admin_answer(message)
        return

    if message.reply_to_message:
        await _handle_admin_reply(message)
        return

    logger.info(f"Admin {message.from_user.id} sent regular message, ignoring")


async def _handle_user_message(message: Message):
    """Process regular user messages with state enforcement."""
    user_id = message.from_user.id

    if await UserStateManager.can_send_question(user_id):
        await _process_user_question(message)
    else:
        await _notify_user_blocked(message)


async def _notify_user_blocked(message: Message):
    """Inform user they must use the button to send the next question."""
    blocked_message = """
💬 <b>Ваш предыдущий вопрос отправлен!</b>

📨 Если хотите задать еще один вопрос, нажмите кнопку ниже.

<i>Это сделано для предотвращения случайной отправки команд как вопросов.</i>
"""
    keyboard = get_user_blocked_keyboard()
    await message.answer(blocked_message, reply_markup=keyboard)
    logger.info(f"User {message.from_user.id} blocked, must use button")


async def _process_user_question(message: Message):
    """Validate, sanitize, persist question, notify admin, confirm to user."""
    user_id = message.from_user.id

    if not message.text:
        await message.answer(ERROR_MESSAGE_EMPTY)
        logger.warning(f"Empty question from user {user_id}")
        return

    max_length = await SettingsManager.get_max_question_length()
    is_valid, error_message = InputValidator.validate_question(
        message.text, max_length)

    if not is_valid:
        await message.answer(f"❌ {error_message}")
        logger.warning(
            f"Invalid question from user {user_id}: {error_message}")
        return

    question_text = InputValidator.sanitize_text(message.text, max_length)

    # Проверка на спам
    if ContentModerator.is_likely_spam(question_text):
        await message.answer("❌ Ваш вопрос похож на спам. Пожалуйста, задайте настоящий вопрос.")
        logger.warning(f"Spam detected from user {user_id}")
        return

    _log_personal_data(question_text, user_id)

    question_id = await _save_question_to_db(question_text, user_id)
    if question_id is None:
        await message.answer(ERROR_DATABASE)
        return

    await _notify_admin_about_question(question_id, question_text, message.bot)

    await _confirm_question_to_user(message, question_id)


def _log_personal_data(question_text: str, user_id: int):
    """Log detected personal data fields for awareness without leaking content."""
    personal_data = InputValidator.extract_personal_data(question_text)
    if any(personal_data.values()):
        detected_fields = [k for k, v in personal_data.items() if v]
        logger.warning(f"Personal data from user {user_id}: {detected_fields}")


async def _save_question_to_db(question_text: str, user_id: int):
    """Persist question and set user state to "question sent"."""
    try:
        async with async_session() as session:
            question = Question.create_new(
                text=question_text,
                user_id=user_id,
                unique_id=None
            )
            session.add(question)
            await session.commit()
            await session.refresh(question)

            await UserStateManager.set_user_state(user_id, UserStateManager.STATE_QUESTION_SENT)

            logger.info(f"Question saved: ID={question.id}")
            return question.id
    except Exception as e:
        logger.error(f"Database error for user {user_id}: {e}")
    return None


async def _notify_admin_about_question(question_id: int, question_text: str, bot):
    """Notify admin about a newly submitted question."""
    try:
        sent_at = format_admin_time(datetime.utcnow())
        admin_message = f"""
❓ <b>Новый анонимный вопрос #{question_id}:</b>

{question_text}

<i>Отправлено: {sent_at}</i>
"""
        spam_score = ContentModerator.calculate_spam_score(question_text)
        if spam_score > 0.3:
            admin_message += f"\n<i>⚠️ Спам-рейтинг: {spam_score:.1%}</i>"

        keyboard = get_admin_question_keyboard(question_id)
        await bot.send_message(ADMIN_ID, admin_message, reply_markup=keyboard)
        logger.info(f"Admin notified about question {question_id}")
    except Exception as e:
        logger.error(
            f"Admin notification failed for question {question_id}: {e}")


async def _confirm_question_to_user(message: Message, question_id: int):
    """Confirm to user that the question was submitted and offer next action."""
    success_message = f"""
✅ <b>Ваш вопрос отправлен автору анонимно!</b>

📩 Ответ придет в этот же чат, если автор решит ответить.

💬 Хотите задать еще один вопрос?
"""
    keyboard = get_user_question_sent_keyboard()
    await message.answer(success_message, reply_markup=keyboard)
    logger.info(f"Question {question_id} processed successfully")


async def _handle_admin_reply(message: Message):
    """Legacy handler: process admin reply-to-message answers."""
    reply_text = message.reply_to_message.text or ""

    question_id = _extract_question_id(reply_text)
    if not question_id:
        logger.info("Admin reply not recognized as question reply")
        return

    answer_text = InputValidator.sanitize_text(message.text.strip())

    is_valid, error_message = InputValidator.validate_answer(answer_text)

    if not is_valid:
        await message.answer(f"❌ {error_message}")
        return

    await _process_admin_answer(question_id, answer_text, message)


def _extract_question_id(text: str) -> int:
    """Extract question ID from admin notification text."""
    match = re.search(r"вопрос #(\d+):", text)
    return int(match.group(1)) if match else 0


async def _process_admin_answer(question_id: int, answer_text: str, message: Message):
    """Save admin answer, deliver to user, acknowledge to admin."""
    try:
        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question or question.is_deleted:
                await message.answer("❌ Вопрос не найден.")
                return

            question.answer = answer_text
            question.answered_at = datetime.utcnow()
            await session.commit()

            success = await _send_answer_to_user(question, answer_text, message.bot)

            if success:
                await message.answer(
                    "✅ Ответ отправлен пользователю анонимно!\n\n"
                    f"<b>Вопрос:</b> {question.text[:100]}...\n"
                    f"<b>Ваш ответ:</b> {answer_text[:100]}..."
                )
            else:
                await message.answer("✅ Ответ сохранен, но не удалось отправить пользователю.")

            logger.info(f"Answer processed for question {question_id}")

    except Exception as e:
        await message.answer("❌ Ошибка при обработке ответа.")
        logger.error(f"Admin reply error: {e}")


async def _send_answer_to_user(question: Question, answer_text: str, bot) -> bool:
    """Deliver answer to the user; return True on success, False otherwise."""
    try:
        user_message = USER_ANSWER_RECEIVED.format(
            question=question.text,
            answer=answer_text
        ) + "\n\n💬 <b>Хотите задать новый вопрос?</b>"

        keyboard = get_user_question_sent_keyboard()
        await bot.send_message(
            chat_id=question.user_id,
            text=user_message,
            reply_markup=keyboard
        )

        await UserStateManager.set_user_state(question.user_id, UserStateManager.STATE_QUESTION_SENT)
        return True

    except Exception as e:
        logger.error(f"Failed to send answer to user {question.user_id}: {e}")
    return False
