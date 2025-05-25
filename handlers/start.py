from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import os

from utils.logger import bot_logger

router = Router()

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", 0))

@router.message(Command("start"))
async def start_handler(message: Message):
    bot_logger.info(f"/start from user {message.from_user.id}")
    if message.from_user.id != ADMIN_USER_ID:
        author_info = (
            "👋 Привет! Ты можешь анонимно задать свой вопрос автору.\n"
            "ℹ️ Автор: [Имя или ник автора]\n"
            "✍️ Просто напиши свой вопрос в ответном сообщении."
        )
        await message.answer(author_info)
    else:
        await message.answer("Привет, админ! Бот готов к работе.")
