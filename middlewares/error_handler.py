"""Error handling middleware for the bot."""

from typing import Callable, Dict, Any, Awaitable, Union
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramUnauthorizedError,
    TelegramAPIError
)
from sqlalchemy.exc import DatabaseError, IntegrityError, OperationalError

from config import ADMIN_ID, ERROR_DATABASE, SENTRY_DSN
from utils.logging_setup import get_logger

logger = get_logger(__name__)

# Sentry integration
SENTRY_ENABLED = False
if SENTRY_DSN:
    try:
        import sentry_sdk
        SENTRY_ENABLED = True
    except ImportError:
        logger.warning("Sentry SDK not installed")


class ErrorHandlerMiddleware(BaseMiddleware):
    """Centralized error handling with user/admin notifications."""

    def __init__(self, notify_admin: bool = True):
        self.notify_admin = notify_admin

    async def __call__(
        self,
        handler: Callable[[Union[Update, Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Update, Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """Execute handler with error catching."""
        try:
            return await handler(event, data)
        except Exception as error:
            await self._handle_error(event, error, data)

    async def _handle_error(
        self,
        event: Union[Update, Message, CallbackQuery],
        error: Exception,
        data: Dict[str, Any]
    ):
        """Process error: log, notify user, alert admin if critical."""
        context = self._extract_context(event)

        if isinstance(error, TelegramBadRequest) and "query is too old" in str(error):
            logger.warning(f"Expired callback: {error}")
            return

        logger.error(f"{type(error).__name__}: {error}",
                     extra=context, exc_info=True)

        if SENTRY_ENABLED:
            self._send_to_sentry(error, context)

        user_message = self._get_user_message(error)
        await self._notify_user(event, user_message)

        if self. notify_admin and self._is_critical(error):
            await self._notify_admin(error, context, data. get('bot'))

    def _extract_context(self, event: Union[Update, Message, CallbackQuery]) -> Dict[str, Any]:
        """Extract user/message info from event."""
        context = {'timestamp': datetime.now(). isoformat()}

        user = None
        if isinstance(event, Message):
            user = event. from_user
            context['chat_id'] = event.chat.id
        elif isinstance(event, CallbackQuery):
            user = event. from_user
            context['callback_data'] = event.data
        elif hasattr(event, 'message') and event.message:
            user = event.message.from_user
            context['chat_id'] = event. message.chat.id
        elif hasattr(event, 'callback_query') and event.callback_query:
            user = event.callback_query. from_user
            context['callback_data'] = event. callback_query.data

        if user:
            context['user_id'] = user.id
            context['username'] = user.username

        return context

    def _get_user_message(self, error: Exception) -> str:
        """Get user-friendly error message based on error type."""
        if isinstance(error, (DatabaseError, OperationalError)):
            return ERROR_DATABASE
        if isinstance(error, IntegrityError):
            return "❌ Ошибка при сохранении данных.  Попробуйте еще раз."
        if isinstance(error, TelegramForbiddenError):
            return ""  # User blocked bot
        if isinstance(error, TelegramBadRequest):
            return "❌ Ошибка при отправке сообщения. Попробуйте позже."
        if isinstance(error, TelegramNotFound):
            return "❌ Сообщение не найдено или удалено."
        if isinstance(error, TelegramUnauthorizedError):
            return "❌ Критическая ошибка бота. Обратитесь к администратору."
        if isinstance(error, TelegramAPIError):
            return "❌ Ошибка Telegram API. Попробуйте позже."
        if isinstance(error, ValueError):
            return f"❌ Ошибка валидации: {str(error)}"
        return "❌ Произошла ошибка.  Попробуйте позже."

    def _is_critical(self, error: Exception) -> bool:
        """Check if error requires admin notification."""
        return isinstance(error, (DatabaseError, OperationalError, TelegramUnauthorizedError))

    def _send_to_sentry(self, error: Exception, context: Dict[str, Any]):
        """Send error to Sentry."""
        try:
            import sentry_sdk
            if context.get('user_id'):
                sentry_sdk. set_user(
                    {"id": context['user_id'], "username": context. get('username')})
            sentry_sdk.set_context("telegram", context)
            sentry_sdk.capture_exception(error)
        except Exception as e:
            logger. error(f"Sentry error: {e}")

    async def _notify_user(self, event: Union[Update, Message, CallbackQuery], message: str):
        """Send error message to user."""
        if not message:
            return

        # Находим message для ответа
        msg = None
        if isinstance(event, Message):
            msg = event
        elif isinstance(event, CallbackQuery):
            msg = event.message
        elif hasattr(event, 'message'):
            msg = event.message
        elif hasattr(event, 'callback_query') and event.callback_query:
            msg = event.callback_query.message

        if msg:
            try:
                await msg.answer(message)
            except Exception as e:
                logger.warning(f"Failed to notify user: {e}")

    async def _notify_admin(self, error: Exception, context: Dict[str, Any], bot):
        """Send critical error notification to admin."""
        if not bot:
            return

        try:
            text = (
                f"🚨 <b>Критическая ошибка! </b>\n\n"
                f"<b>Тип:</b> <code>{type(error).__name__}</code>\n"
                f"<b>Сообщение:</b> <code>{str(error)[:200]}</code>\n"
                f"<b>Пользователь:</b> {context.get('user_id', 'Unknown')}\n"
                f"<b>Время:</b> {context['timestamp']}"
            )
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")