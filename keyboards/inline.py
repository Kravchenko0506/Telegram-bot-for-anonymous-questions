"""
Inline Keyboards for Anonymous Questions Bot

Contains all inline keyboard layouts for admin question management with pagination.
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


def get_user_question_sent_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for user after question is sent."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❓ Задать еще вопрос",
                    callback_data="ask_another_question"
                )
            ]
        ]
    )

    return keyboard


def get_user_blocked_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for user when they try to send text but are blocked."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❓ Задать новый вопрос",
                    callback_data="ask_another_question"
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
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Убрать из избранного",
                    callback_data=f"remove_favorite:{question_id}"
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


def get_answered_question_keyboard(question_id: int, is_favorite: bool) -> InlineKeyboardMarkup:
    """Keyboard for answered questions (no reply button)."""
    fav_text = "⭐ Убрать из избранного" if is_favorite else "⭐ В избранное"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=fav_text,
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
                InlineKeyboardButton(text="⏳ Неотвеченные",
                                     callback_data="admin:pending"),
                InlineKeyboardButton(text="⭐ Избранные",
                                     callback_data="admin:favorites")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика",
                                     callback_data="admin:stats"),
                InlineKeyboardButton(text="⚙️ Настройки",
                                     callback_data="admin:settings")
            ]
        ]
    )

    return keyboard


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """
    Create pagination keyboard for question lists.

    Args:
        current_page: Current page number (0-based)
        total_pages: Total number of pages
        callback_prefix: Prefix for callback data (e.g., "pending_page", "favorites_page")

    Returns:
        InlineKeyboardMarkup: Pagination keyboard
    """
    buttons = []

    # Previous page button
    if current_page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"{callback_prefix}:{current_page - 1}"
            )
        )

    # Page indicator (show current/total)
    buttons.append(
        InlineKeyboardButton(
            text=f"📄 {current_page + 1}/{total_pages}",
            callback_data="noop"  # Non-functional button for display only
        )
    )

    # Next page button
    if current_page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"{callback_prefix}:{current_page + 1}"
            )
        )

    # If only one button (page indicator), still show it
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


def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for statistics with clear option."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑️ Очистить все вопросы",
                    callback_data="clear_all_questions"
                )
            ]
        ]
    )

    return keyboard


def get_clear_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Create confirmation keyboard for clearing all questions."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚠️ Да, удалить ВСЕ вопросы",
                    callback_data="confirm_clear_all"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_clear"
                )
            ]
        ]
    )

    return keyboard


def get_advanced_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
    show_first_last: bool = True
) -> InlineKeyboardMarkup:
    """
    Create advanced pagination keyboard with first/last page buttons.

    Args:
        current_page: Current page number (0-based)
        total_pages: Total number of pages
        callback_prefix: Prefix for callback data
        show_first_last: Whether to show first/last page buttons

    Returns:
        InlineKeyboardMarkup: Advanced pagination keyboard
    """
    if total_pages <= 1:
        return None

    buttons = []

    # First row: First, Previous, Page indicator, Next, Last
    first_row = []

    # First page button (only if not on first page and more than 3 pages)
    if show_first_last and current_page > 1 and total_pages > 3:
        first_row.append(
            InlineKeyboardButton(
                text="⏮️ Первая",
                callback_data=f"{callback_prefix}:0"
            )
        )

    # Previous page button
    if current_page > 0:
        first_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"{callback_prefix}:{current_page - 1}"
            )
        )

    # Current page indicator
    first_row.append(
        InlineKeyboardButton(
            text=f"📄 {current_page + 1}/{total_pages}",
            callback_data="noop"
        )
    )

    # Next page button
    if current_page < total_pages - 1:
        first_row.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"{callback_prefix}:{current_page + 1}"
            )
        )

    # Last page button (only if not on last page and more than 3 pages)
    if show_first_last and current_page < total_pages - 2 and total_pages > 3:
        first_row.append(
            InlineKeyboardButton(
                text="⏭️ Последняя",
                callback_data=f"{callback_prefix}:{total_pages - 1}"
            )
        )

    buttons.append(first_row)

    # Second row: Quick jump buttons for nearby pages (optional)
    if total_pages > 5:
        second_row = []
        start_page = max(0, current_page - 2)
        end_page = min(total_pages - 1, current_page + 2)

        for page in range(start_page, end_page + 1):
            if page != current_page:  # Don't show current page button
                second_row.append(
                    InlineKeyboardButton(
                        text=str(page + 1),
                        callback_data=f"{callback_prefix}:{page}"
                    )
                )

        if len(second_row) > 0:
            buttons.append(second_row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
