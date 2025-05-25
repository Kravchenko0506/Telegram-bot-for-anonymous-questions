"""
Простой debug-бот для проверки получения сообщений
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Импорт токена
from config import TOKEN, ADMIN_ID

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Создаем роутер
router = Router()

@router.message()
async def catch_everything(message: Message):
    """Ловим ВСЕ сообщения."""
    user_id = message.from_user.id
    text = message.text or "NO TEXT"
    
    print(f"🔍 ПОЛУЧЕНО: {text} от пользователя {user_id}")
    
    try:
        await message.answer(f"🤖 Получил: '{text}'\nВаш ID: {user_id}\nАдмин ID: {ADMIN_ID}")
        print(f"✅ ОТВЕТИЛ пользователю {user_id}")
    except Exception as e:
        print(f"❌ ОШИБКА ответа: {e}")

async def main():
    """Запуск простого бота."""
    print(f"🚀 Запуск debug-бота...")
    print(f"📋 Токен: {TOKEN[:10]}...")
    print(f"👤 Админ ID: {ADMIN_ID}")
    
    # Создаем бота
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Создаем диспетчер
    dp = Dispatcher()
    dp.include_router(router)
    
    # Получаем информацию о боте
    try:
        bot_info = await bot.get_me()
        print(f"🤖 Бот: @{bot_info.username}")
        print(f"📧 Отправьте любое сообщение боту @{bot_info.username}")
    except Exception as e:
        print(f"❌ Ошибка получения информации о боте: {e}")
        return
    
    try:
        print("🔄 Запуск polling...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка polling: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")