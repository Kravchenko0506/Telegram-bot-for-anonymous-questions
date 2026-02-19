from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_admin_question_keyboard(
    question_id: int, is_favorite: bool = False
) -> InlineKeyboardMarkup:
    """Keyboard for admin question management."""
    favorite_text = (
        "⭐ Убрать из избранного" if is_favorite else "⭐ Добавить в избранное"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✉️ Ответить", callback_data=f"answer:{question_id}"
                ),
                InlineKeyboardButton(
                    text=favorite_text, callback_data=f"favorite:{question_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить", callback_data=f"delete:{question_id}"
                )
            ],
        ]
    )

    return keyboard


def get_user_question_sent_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for user after question is sent."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❓ Задать еще вопрос", callback_data="ask_another_question"
                )
            ]
        ]
    )

    return keyboard


def get_user_blocked_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for user when they try to send text but are blocked."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❓ Задать новый вопрос", callback_data="ask_another_question"
                )
            ]
        ]
    )

    return keyboard


def get_cancel_answer_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Keyboard for canceling answer mode."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить ответ",
                    callback_data=f"cancel_answer:{question_id}",
                )
            ]
        ]
    )
    return keyboard


def get_favorite_question_keyboard(
    question_id: int, is_answered: bool = False
) -> InlineKeyboardMarkup:
    """Keyboard for favorite questions with delete option."""
    buttons = []

    if not is_answered:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✉️ Ответить", callback_data=f"answer:{question_id}"
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="⭐ Убрать из избранного",
                    callback_data=f"remove_favorite:{question_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить", callback_data=f"delete:{question_id}"
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_answered_question_keyboard(
    question_id: int, is_favorite: bool
) -> InlineKeyboardMarkup:
    """Keyboard for answered questions."""
    fav_text = "⭐ Убрать из избранного" if is_favorite else "⭐ В избранное"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=fav_text, callback_data=f"favorite:{question_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить", callback_data=f"delete:{question_id}"
                )
            ],
        ]
    )
    return keyboard


def get_pagination_keyboard(
    current_page: int, total_pages: int, callback_prefix: str
) -> InlineKeyboardMarkup:
    """Keyboard for pagination in question lists."""
    buttons = []

    # Previous page button
    if current_page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"{callback_prefix}:{current_page - 1}"
            )
        )

    # Page indicator (show current/total)
    buttons.append(
        InlineKeyboardButton(
            text=f"📄 {current_page + 1}/{total_pages}", callback_data="noop"
        )
    )

    if current_page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️", callback_data=f"{callback_prefix}:{current_page + 1}"
            )
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    return keyboard


def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for statistics with clear option."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑️ Очистить все вопросы", callback_data="clear_all_questions"
                )
            ]
        ]
    )

    return keyboard


def get_clear_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for clearing all questions."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚠️ Да, удалить ВСЕ вопросы", callback_data="confirm_clear_all"
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_clear")],
        ]
    )

    return keyboard
