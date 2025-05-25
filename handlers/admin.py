from aiogram import Router
from aiogram.types import CallbackQuery
from utils.logger import admin_logger

router = Router()

@router.callback_query()
async def admin_question_callback(callback: CallbackQuery):
    """
    Обрабатывает нажатия на inline-кнопки под вопросом у админа.

    Возможные действия:
    - answer: инициировать процесс ответа на вопрос
    - favorite: добавить вопрос в избранное (пока только уведомление)
    - delete: удалить вопрос (пока только уведомление)

    Параметры:
    - callback: объект CallbackQuery, содержит информацию о запросе и данных кнопки
    """
    # Разбиваем callback_data типа "answer:12345"
    try:
        action, question_id = callback.data.split(":")
    except Exception as e:
        admin_logger.error(f"Некорректный callback_data: {callback.data} ({e})")
        await callback.answer("Некорректные данные кнопки.")
        return

    admin_logger.info(f"Admin action: {action} on question {question_id}")

    # В зависимости от типа действия
    if action == "answer":
        # Пока просто уведомляем (позже реализуем диалог ответа)
        await callback.answer("Функция 'ответить' ещё в разработке.")
    elif action == "favorite":
        # Здесь будет добавление в избранное (заглушка)
        await callback.answer("Добавлено в избранное (ещё не реализовано).")
    elif action == "delete":
        # Здесь будет удаление вопроса (заглушка)
        await callback.answer("Вопрос удалён (ещё не реализовано).")
    else:
        await callback.answer("Неизвестное действие.")

