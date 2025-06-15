"""
Error Management System

A comprehensive error handling system for the Anonymous Questions Bot that provides
centralized error processing, logging, and notification capabilities.

Features:
- Error categorization and handling
- User-friendly error messages
- Admin notifications
- Sentry integration
- Error statistics
- Context tracking
- Database error handling
- API error handling

Technical Features:
- Middleware architecture
- Error type classification
- Context extraction
- Sentry integration
- Admin notifications
- Error statistics
- Logging integration
"""

from typing import Callable, Dict, Any, Awaitable, Union
import traceback
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import Update, ErrorEvent, Message, CallbackQuery
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramUnauthorizedError,
    TelegramAPIError
)
from sqlalchemy.exc import (
    DatabaseError,
    IntegrityError,
    OperationalError,
    DataError
)

from config import ADMIN_ID, ERROR_DATABASE, SENTRY_DSN
from utils.logger import get_bot_logger

logger = get_bot_logger()

# Import Sentry if configured
if SENTRY_DSN:
    try:
        import sentry_sdk
        SENTRY_ENABLED = True
    except ImportError:
        SENTRY_ENABLED = False
        logger.warning("Sentry SDK not installed, error tracking disabled")
else:
    SENTRY_ENABLED = False


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Comprehensive error handling middleware for bot operations.

    This middleware provides:
    - Centralized error handling
    - Error categorization
    - User notifications
    - Admin alerts
    - Error tracking
    - Statistics collection

    Features:
    - Error type detection
    - Context extraction
    - User messaging
    - Admin notifications
    - Sentry integration
    - Error statistics
    - Database error handling
    - API error handling

    Technical Features:
    - Middleware architecture
    - Async operation support
    - Context management
    - Error classification
    - Message formatting
    - Statistics tracking
    """

    def __init__(self, notify_admin: bool = True):
        """
        Initialize error handler with configuration.

        Args:
            notify_admin: Whether to send critical error notifications to admin
        """
        self.notify_admin = notify_admin
        self.error_count = 0
        self.last_errors: list[Dict[str, Any]] = []

    async def __call__(
        self,
        handler: Callable[[Union[Update, Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Update, Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """
        Process update with comprehensive error handling.

        This method:
        - Executes the handler
        - Catches any exceptions
        - Processes errors
        - Notifies users/admin
        - Tracks statistics

        Args:
            handler: Update handler to execute
            event: Telegram update event
            data: Additional context data

        Returns:
            Any: Handler result if successful
        """
        try:
            return await handler(event, data)
        except Exception as error:
            await self.handle_error(event, error, data)

    async def handle_error(self, event: Union[Update, Message, CallbackQuery], error: Exception, data: Dict[str, Any]):
        """
        Process and handle errors with full context.

        This method:
        - Extracts error context
        - Logs error details
        - Tracks statistics
        - Sends notifications
        - Updates error history

        Args:
            event: Telegram event where error occurred
            error: Exception that was raised
            data: Additional context data
        """
        self.error_count += 1

        # Extract context
        context = self._extract_context(event, data)

        # Log error with context
        logger.error(
            f"Error #{self.error_count}: {type(error).__name__}: {error}",
            extra=context,
            exc_info=True
        )

        # Store error for admin review
        self._store_error(error, context)

        # Send to Sentry if configured
        if SENTRY_ENABLED:
            self._send_to_sentry(error, context)

        # Handle specific error types
        user_message = await self._handle_specific_error(error, event, context)

        # Send user notification
        await self._notify_user(event, user_message)

        # Notify admin of critical errors
        if self.notify_admin and self._is_critical_error(error):
            await self._notify_admin(error, context)

    def _extract_context(self, event: Union[Update, Message, CallbackQuery], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract comprehensive context from event.

        This method gathers:
        - Event metadata
        - User information
        - Message details
        - Handler context
        - Timestamp data

        Args:
            event: Telegram event to analyze
            data: Additional context data

        Returns:
            Dict[str, Any]: Extracted context information
        """
        context = {
            'timestamp': datetime.now().isoformat(),
            'handler': data.get('handler', 'unknown')
        }

        # Extract update_id correctly
        if hasattr(event, 'update_id'):
            context['update_id'] = event.update_id
        elif hasattr(event, 'message') and hasattr(event.message, 'message_id'):
            # Use message_id for Message objects
            context['message_id'] = event.message.message_id

        # Extract user info based on event type
        if hasattr(event, 'message') and event.message:
            # This is an Update object with message
            message = event.message
            user = message.from_user
            context.update({
                'event_type': 'message',
                'user_id': user.id if user else None,
                'username': user.username if user else None,
                'chat_id': message.chat.id,
                'message_text': message.text[:100] if message.text else None,
                'message_id': message.message_id
            })
        elif hasattr(event, 'callback_query') and event.callback_query:
            # This is an Update object with callback_query
            callback = event.callback_query
            user = callback.from_user
            context.update({
                'event_type': 'callback_query',
                'user_id': user.id,
                'username': user.username,
                'callback_data': callback.data,
                'message_id': callback.message.message_id if callback.message else None
            })
        elif hasattr(event, 'from_user'):
            # This is a Message object directly
            user = event.from_user
            context.update({
                'event_type': 'direct_message',
                'user_id': user.id if user else None,
                'username': user.username if user else None,
                'chat_id': event.chat.id if hasattr(event, 'chat') else None,
                'message_text': event.text[:100] if hasattr(event, 'text') and event.text else None,
                'message_id': event.message_id if hasattr(event, 'message_id') else None
            })

        return context

    async def _handle_specific_error(
        self,
        error: Exception,
        event: Update,
        context: Dict[str, Any]
    ) -> str:
        """
        Process specific error types with appropriate responses.

        This method handles:
        - Database errors
        - API errors
        - Validation errors
        - Permission errors
        - Network errors

        Args:
            error: Exception to handle
            event: Related Telegram event
            context: Error context data

        Returns:
            str: User-friendly error message
        """

        # Database errors
        if isinstance(error, (DatabaseError, OperationalError)):
            logger.critical(f"Database error: {error}", extra=context)
            return ERROR_DATABASE

        elif isinstance(error, IntegrityError):
            logger.error(f"Database integrity error: {error}", extra=context)
            return "❌ Ошибка при сохранении данных. Попробуйте еще раз."

        elif isinstance(error, DataError):
            logger.error(f"Database data error: {error}", extra=context)
            return "❌ Некорректные данные. Проверьте ввод и попробуйте снова."

        # Telegram API errors
        elif isinstance(error, TelegramForbiddenError):
            logger.warning(f"Bot blocked by user: {context.get('user_id')}")
            return ""  # User blocked bot, can't send message

        elif isinstance(error, TelegramBadRequest):
            logger.error(f"Bad request to Telegram: {error}", extra=context)
            return "❌ Ошибка при отправке сообщения. Попробуйте позже."

        elif isinstance(error, TelegramNotFound):
            logger.error(f"Telegram entity not found: {error}", extra=context)
            return "❌ Сообщение не найдено или удалено."

        elif isinstance(error, TelegramUnauthorizedError):
            logger.critical(f"Bot unauthorized: {error}")
            return "❌ Критическая ошибка бота. Обратитесь к администратору."

        elif isinstance(error, TelegramAPIError):
            logger.error(f"Telegram API error: {error}", extra=context)
            return "❌ Ошибка Telegram API. Попробуйте позже."

        # Validation errors
        elif isinstance(error, ValueError):
            logger.warning(f"Validation error: {error}", extra=context)
            return f"❌ Ошибка валидации: {str(error)}"

        # Generic errors
        else:
            logger.error(
                f"Unhandled error type {type(error).__name__}: {error}", extra=context)
            return "❌ Произошла непредвиденная ошибка. Попробуйте позже."

    def _store_error(self, error: Exception, context: Dict[str, Any]):
        """Store error for admin review."""
        error_info = {
            'type': type(error).__name__,
            'message': str(error),
            'context': context,
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now()
        }

        self.last_errors.append(error_info)

        # Keep only last 50 errors
        if len(self.last_errors) > 50:
            self.last_errors.pop(0)

    def _send_to_sentry(self, error: Exception, context: Dict[str, Any]):
        """Send error to Sentry if configured."""
        if not SENTRY_ENABLED:
            return

        try:
            import sentry_sdk

            # Set user context
            if 'user_id' in context:
                sentry_sdk.set_user({
                    "id": context['user_id'],
                    "username": context.get('username')
                })

            # Set additional context
            sentry_sdk.set_context("telegram_update", context)

            # Capture exception
            sentry_sdk.capture_exception(error)

        except Exception as e:
            logger.error(f"Failed to send error to Sentry: {e}")

    def _is_critical_error(self, error: Exception) -> bool:
        """Check if error is critical and should notify admin."""
        critical_types = (
            DatabaseError,
            OperationalError,
            TelegramUnauthorizedError,
        )
        return isinstance(error, critical_types)

    async def _notify_user(self, event: Union[Update, Message, CallbackQuery], message: str):
        """Send error message to user."""
        if not message:
            return

        try:
            # Handle different event types
            if isinstance(event, Message):
                await event.answer(message)
            elif isinstance(event, CallbackQuery):
                await event.answer(message, show_alert=True)
            elif isinstance(event, Update):
                if event.message:
                    await event.message.answer(message)
                elif event.callback_query:
                    await event.callback_query.answer(message, show_alert=True)
        except Exception as e:
            logger.error(f"Failed to notify user about error: {e}")

    async def _notify_admin(self, error: Exception, context: Dict[str, Any]):
        """Notify admin about critical error."""
        try:
            from aiogram import Bot
            bot: Bot = context.get('bot')

            if not bot:
                return

            admin_message = f"""
🚨 <b>Критическая ошибка в боте!</b>

<b>Тип:</b> <code>{type(error).__name__}</code>
<b>Сообщение:</b> <code>{str(error)[:200]}</code>
<b>Пользователь:</b> {context.get('user_id', 'Unknown')}
<b>Время:</b> {context['timestamp']}

<b>Контекст:</b>
<pre>{self._format_context(context)}</pre>

<i>Проверьте логи для подробностей.</i>
"""

            await bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode="HTML"
            )

        except Exception as e:
            logger.error(f"Failed to notify admin about critical error: {e}")

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for admin message."""
        # Remove sensitive data
        safe_context = {
            k: v for k, v in context.items()
            if k not in ['bot', 'handler', 'traceback']
        }

        # Format as readable text
        lines = []
        for key, value in safe_context.items():
            if value is not None:
                lines.append(f"{key}: {value}")

        return "\n".join(lines)[:500]  # Limit length

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        error_types = {}
        for error in self.last_errors:
            error_type = error['type']
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            'total_errors': self.error_count,
            'error_types': error_types,
            'last_error': self.last_errors[-1] if self.last_errors else None,
            'errors_last_hour': len([
                e for e in self.last_errors
                if (datetime.now() - e['timestamp']).seconds < 3600
            ])
        }
