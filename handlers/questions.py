from aiogram import Router
from aiogram.types import Message
from aiogram import Router, Bot
import os

from utils.logger import question_logger
from keyboards.inline import get_admin_question_keyboard

router = Router()

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", 0))

# Пока просто храним статус в памяти. Потом заменим на БД/Redis.
user_states = {}

@router.message()
async def question_handler(message: Message ,bot: Bot):
    if message.from_user.id == ADMIN_USER_ID:
        return  # Админ не отправляет вопросы себе
    # Ждём вопрос сразу после старта
    if message.text:
        question_text = message.text.strip()
        question_logger.info(f"Получен анонимный вопрос от {message.from_user.id}: {question_text}")
        # Здесь сохраняем вопрос в БД и получаем question_id. Пока имитируем:
        question_id = id(message)  # или uuid.uuid4().int
        # Отправляем админу с кнопками
        
        await bot.send_message(
            ADMIN_USER_ID,
            f"❓ Новый анонимный вопрос:\n\n{question_text}",
            reply_markup=get_admin_question_keyboard(question_id)
        )
        await message.answer("Спасибо! Вопрос отправлен автору.")
