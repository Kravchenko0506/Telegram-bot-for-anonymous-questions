"""Admin state management for question answering mode."""

from datetime import datetime
from typing import Optional, Union

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from config import USER_ANSWER_RECEIVED
from keyboards.inline import get_cancel_answer_keyboard, get_user_question_sent_keyboard
from models.admin_state import AdminStateManager
from models.database import async_session
from models.questions import Question
from models.user_states import UserStateManager
from utils.logging_setup import get_logger

router = Router()
logger = get_logger(__name__)


def _preview_text(text: str, max_len: int = 100) -> str:
    """Truncate text for preview display."""
    return text if len(text) <= max_len else text[:max_len] + "..."


async def is_admin_in_answer_mode(admin_id: int) -> bool:
    """Check if admin is currently in answer mode."""
    return await AdminStateManager.is_in_state(
        admin_id, AdminStateManager.STATE_ANSWERING
    )


async def start_answer_mode(
    callback: CallbackQuery, question_id: int, question: Optional[Question] = None
) -> None:
    """Start answer mode for a question."""
    admin_id = callback.from_user.id

    try:
        await callback.answer("💡 Введите ответ в следующем сообщении")
    except TelegramBadRequest:
        pass

    try:
        if question is None:
            async with async_session() as session:
                question = await session.get(Question, question_id)

        if not question or question.is_deleted:
            await callback.message.answer("❌ Вопрос не найден")
            return

        if question.is_answered:
            await callback.message.answer("❌ Уже отвечен")
            return

        state_data = {
            "question_id": question_id,
            "question_text": question.text or "",
            "user_id": question.user_id,
        }

        await AdminStateManager.set_state(
            admin_id=admin_id,
            state_type=AdminStateManager.STATE_ANSWERING,
            state_data=state_data,
            expiration_minutes=30,
        )

        safe_question_text = question.text or "(пустой вопрос)"
        await callback.message.reply(
            f"💬 <b>Ответ на вопрос #{question_id}</b>\n\n"
            f"<b>Вопрос:</b>\n<i>{safe_question_text}</i>\n\n"
            "📝 <b>Напишите ответ:</b>\n"
            "<i>⏰ Режим ответа отключится через 30 минут</i>",
            reply_markup=get_cancel_answer_keyboard(question_id),
        )

    except Exception as e:
        await AdminStateManager.clear_state(admin_id)
        logger.error(f"Error starting answer mode: {e}")
        try:
            await callback.message.answer("❌ Ошибка входа в режим ответа")
        except Exception:
            pass


async def handle_admin_answer(message: Message) -> bool:
    """Process admin's answer to a question."""
    admin_id = message.from_user.id

    state = await AdminStateManager.get_state(admin_id)
    if not state or state.get("type") != AdminStateManager.STATE_ANSWERING:
        return False

    answer_text = message.text.strip()
    if not answer_text:
        await message.answer("❌ Ответ не может быть пустым")
        return True

    data = state["data"]
    question_id = data["question_id"]
    user_id = data["user_id"]
    question_text = data["question_text"]

    await AdminStateManager.clear_state(admin_id)

    try:
        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question or question.is_answered:
                await message.answer("❌ Вопрос недоступен")
                return True

            question.answer = answer_text
            question.answered_at = datetime.utcnow()
            await session.commit()

        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=USER_ANSWER_RECEIVED.format(
                    question=question_text, answer=answer_text
                )
                + "\n\n💬 <b>Хотите задать новый вопрос?</b>",
                reply_markup=get_user_question_sent_keyboard(),
            )
            await UserStateManager.set_user_state(
                user_id, UserStateManager.STATE_QUESTION_SENT
            )
            user_notified = True
        except Exception:
            user_notified = False

        preview_q = _preview_text(question_text)
        preview_a = _preview_text(answer_text)

        if user_notified:
            await message.answer(
                f"✅ <b>Ответ отправлен! </b>\n\n"
                f"<b>Вопрос:</b> {preview_q}\n"
                f"<b>Ответ:</b> {preview_a}\n\n"
                f"<i>Доставлено анонимно</i>"
            )
        else:
            await message.answer(
                f"✅ <b>Ответ сохранен!</b>\n\n"
                f"<b>Вопрос:</b> {preview_q}\n"
                f"<b>Ответ:</b> {preview_a}\n\n"
                f"⚠️ Не удалось отправить пользователю"
            )

        return True

    except Exception as e:
        await message.answer("❌ Ошибка сохранения")
        logger.error(f"Error saving answer: {e}")
        return True


async def cancel_answer_mode(source: Union[CallbackQuery, Message]) -> None:
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
        return

    if callback:
        try:
            await callback.answer("Отменено")
        except TelegramBadRequest:
            pass

    was_active = await AdminStateManager.get_state(admin_id)
    await AdminStateManager.clear_state(admin_id)

    if was_active:
        try:
            await message.edit_text("❌ Режим ответа отменен", reply_markup=None)
        except Exception:
            await message.answer("❌ Режим ответа отменен")
    elif not callback:
        await message.answer("Режим ответа не активен")
