# keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_question_keyboard(question_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✉️ Ответить", callback_data=f"answer:{question_id}"),
                InlineKeyboardButton(text="⭐ Избранное", callback_data=f"favorite:{question_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete:{question_id}")
            ]
        ]
    )
