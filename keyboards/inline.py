"""
Inline Keyboards for Anonymous Questions Bot

Contains all inline keyboard layouts for admin question management.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_question_keyboard(question_id: int, is_favorite: bool = False) -> InlineKeyboardMarkup:
    """Create inline keyboard for admin question management."""
    favorite_text = "⭐ Убрать из избранного" if is_favorite else "⭐ Добавить в избранное"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✉️ Ответить", 
                    callback_data=f"answer:{question_id}"
                ),
                InlineKeyboardButton(
                    text=favorite_text, 
                    callback_data=f"favorite:{question_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить", 
                    callback_data=f"delete:{question_id}"
                )
            ]
        ]
    )
    
    return keyboard


def get_cancel_answer_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Create keyboard for canceling answer mode."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить ответ", 
                    callback_data=f"cancel_answer:{question_id}"
                )
            ]
        ]
    )
    return keyboard


def get_favorite_question_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Create keyboard for favorite questions with delete option."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✉️ Ответить", 
                    callback_data=f"answer:{question_id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ Удалить из избранного", 
                    callback_data=f"remove_favorite:{question_id}"
                )
            ]
        ]
    )
    return keyboard


def get_answer_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """
    Create keyboard for answer mode.
    
    Args:
        question_id: ID of question being answered
        
    Returns:
        InlineKeyboardMarkup: Keyboard with cancel option
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить ответ", 
                    callback_data=f"cancel_answer:{question_id}"
                )
            ]
        ]
    )
    
    return keyboard


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Create main admin panel keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏳ Неотвеченные", callback_data="admin:pending"),
                InlineKeyboardButton(text="⭐ Избранные", callback_data="admin:favorites")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin:settings")
            ]
        ]
    )
    
    return keyboard


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """Create pagination keyboard for question lists."""
    buttons = []
    
    # Previous page button
    if current_page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"{callback_prefix}:page:{current_page - 1}"
            )
        )
    
    # Page indicator
    buttons.append(
        InlineKeyboardButton(
            text=f"{current_page + 1}/{total_pages}",
            callback_data="noop"
        )
    )
    
    # Next page button
    if current_page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"{callback_prefix}:page:{current_page + 1}"
            )
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    return keyboard


def get_confirmation_keyboard(action: str, question_id: int) -> InlineKeyboardMarkup:
    """Create confirmation keyboard for destructive actions."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, подтвердить",
                    callback_data=f"confirm:{action}:{question_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel"
                )
            ]
        ]
    )
    
    return keyboard