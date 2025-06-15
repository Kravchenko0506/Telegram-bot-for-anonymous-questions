"""
Tests for Aiogram middleware components.

This test suite covers:
1. Rate Limiting:
   - Per-user question rate limiting
   - Cooldown periods
   - Admin and command bypasses
   - Usage statistics

2. Callback Rate Limiting:
   - Per-user callback cooldowns
   - Pattern-based bypasses
   - Admin exemptions

3. Error Handling:
   - Error capture and logging
   - User notifications
   - Error statistics
   - Context preservation

4. Integration:
   - Middleware chain behavior
   - Error propagation
   - State management

Dependencies:
- pytest and pytest-asyncio
- unittest.mock
- aiogram types and exceptions
- datetime and os modules
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, create_autospec
from datetime import datetime, timedelta
import os

from aiogram.types import Message, CallbackQuery, User, Chat
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramUnauthorizedError


class TestRateLimitMiddleware:
    """Tests for the rate limiting middleware implementation.

    Verifies:
    - Initialization with configuration
    - Admin and command bypasses
    - Cooldown enforcement
    - Question limits
    - Data cleanup
    """

    @pytest.mark.unit
    def test_middleware_initialization(self):
        """Test middleware initialization and configuration.

        Verifies:
        - Default values are loaded
        - Environment variables are respected
        - Data structures are initialized
        - Configuration is valid
        """
        from middlewares.rate_limit import RateLimitMiddleware

        # Get rate limit from environment
        rate_limit = int(os.getenv('RATE_LIMIT_QUESTIONS_PER_HOUR', '5'))
        cooldown = int(os.getenv('RATE_LIMIT_COOLDOWN_SECONDS', '30'))

        middleware = RateLimitMiddleware()

        assert middleware.questions_per_hour == rate_limit
        assert middleware.cooldown_seconds == cooldown
        assert isinstance(middleware.user_questions, dict)
        assert isinstance(middleware.user_last_message, dict)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_admin_bypass(self):
        """Test admin user exemption from rate limiting.

        Verifies:
        - Admin ID recognition
        - Complete bypass of limits
        - Handler execution
        - No cooldown applied
        """
        from middlewares.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware()

        # Create admin          message
        admin_id = int(os.getenv('ADMIN_ID', '123456789'))
        admin_user = User(id=admin_id, is_bot=False, first_name="Admin")
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=admin_id, type="private"),
            from_user=admin_user,
            text="Admin message",
            bot=AsyncMock()
        )

        # Mock handler
        handler = AsyncMock(return_value="success")
        data = {}

        # Should bypass rate limiting
        result = await middleware(handler, message, data)

        assert result == "success"
        handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_command_bypass(self):
        """Test command message exemption from rate limiting.

        Verifies:
        - Command recognition
        - Bypass of limits
        - Handler execution
        - No restrictions applied
        """
        from middlewares.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware()

        # Create user with command
        user = User(id=123456789, is_bot=False, first_name="User")
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            from_user=user,
            text="/start",
            bot=AsyncMock()
        )

        handler = AsyncMock(return_value="success")
        data = {}

        result = await middleware(handler, message, data)

        assert result == "success"
        handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_first_question_no_cooldown(self):
        """Test first question handling without cooldown.

        Verifies:
        - New user recognition
        - No cooldown applied
        - Question processing
        - State tracking
        """
        from middlewares.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(cooldown_seconds=30)

        user = User(id=123456789, is_bot=False, first_name="User")
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            from_user=user,
            text="First question",
            bot=AsyncMock()
        )

        handler = AsyncMock(return_value="success")
        data = {}

        # Mock that user is sending a question
        with patch.object(middleware, '_is_sending_question', return_value=True):
            result = await middleware(handler, message, data)

        assert result == "success"
        handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cooldown_enforcement(self):
        """Test cooldown period enforcement for subsequent questions.

        Verifies:
        - Cooldown timing
        - Message blocking
        - User notification
        - State preservation
        """
        from middlewares.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(cooldown_seconds=30)
        user_id = 123456789

        # Set user as having sent first question
        middleware.user_has_sent_first_question.add(user_id)

        # Set last question time to now (within cooldown)
        middleware.user_last_question[user_id] = datetime.now()

        user = User(id=user_id, is_bot=False, first_name="User")
        message = MagicMock(spec=Message)
        message.message_id = 1
        message.date = datetime.now()
        message.chat = MagicMock(spec=Chat)
        message.chat.id = user_id
        message.from_user = MagicMock(spec=User)
        message.from_user.id = user_id
        message.text = "Second question"
        message.bot = AsyncMock()
        message.answer = AsyncMock()

        handler = AsyncMock(return_value="success")
        data = {}

        # Mock that user is sending a question
        with patch.object(middleware, '_is_sending_question', return_value=True):
            result = await middleware(handler, message, data)

        # Should be blocked by cooldown
        assert result is None
        message.answer.assert_called_once()
        handler.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hourly_limit_enforcement(self):
        """Test enforcement of hourly question limits.

        Verifies:
        - Question counting
        - Time window tracking
        - Limit enforcement
        - User notification
        """
        from middlewares.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(
            questions_per_hour=2,
            cooldown_seconds=0  # Disable cooldown for this test
        )
        user_id = 123456789

        # Fill up user's hourly quota
        now = datetime.now()
        middleware.user_questions[user_id] = [now, now - timedelta(minutes=30)]

        user = User(id=user_id, is_bot=False, first_name="User")
        message = MagicMock(spec=Message)
        message.message_id = 1
        message.date = datetime.now()
        message.chat = MagicMock(spec=Chat)
        message.chat.id = user_id
        message.from_user = MagicMock(spec=User)
        message.from_user.id = user_id
        message.text = "Second question"
        message.bot = AsyncMock()
        message.answer = AsyncMock()

        handler = AsyncMock(return_value="success")
        data = {}

        # Mock that user is sending a question
        with patch.object(middleware, '_is_sending_question', return_value=True):
            result = await middleware(handler, message, data)

        # Should be blocked by hourly limit
        assert result is None
        message.answer.assert_called_once()
        handler.assert_not_called()

    @pytest.mark.unit
    def test_user_stats(self):
        """Test getting user statistics."""
        from middlewares.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware()
        user_id = 123456789

        # Add some test data
        now = datetime.now()
        middleware.user_questions[user_id] = [now, now - timedelta(minutes=30)]
        middleware.user_last_question[user_id] = now - timedelta(seconds=10)
        middleware.user_has_sent_first_question.add(user_id)

        stats = middleware.get_user_stats(user_id)

        assert isinstance(stats, dict)
        assert 'questions_last_hour' in stats
        assert 'cooldown_remaining' in stats
        assert 'has_sent_first_question' in stats
        assert stats['has_sent_first_question'] is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cleanup_old_data(self):
        """Test cleanup of old tracking data."""
        from middlewares.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware()
        user_id = 123456789

        # Add old data
        old_time = datetime.now() - timedelta(hours=2)
        middleware.user_questions[user_id] = [old_time]
        middleware.user_last_message[user_id] = old_time
        middleware.user_last_question[user_id] = old_time

        await middleware.cleanup_old_data()

        # Old data should be cleaned up
        assert user_id not in middleware.user_questions
        assert user_id not in middleware.user_last_message
        assert user_id not in middleware.user_last_question


class TestCallbackRateLimitMiddleware:
    """Tests for the callback rate limiting middleware implementation.

    Verifies:
    - Initialization with configuration
    - Admin bypasses
    - Cooldown enforcement
    - Pattern-based exemptions
    """

    @pytest.mark.unit
    def test_middleware_initialization(self):
        """Test callback rate limit middleware initialization.

        Verifies:
        - Default values are loaded
        - Data structures are initialized
        - Configuration is valid
        """
        from middlewares.rate_limit import CallbackRateLimitMiddleware

        middleware = CallbackRateLimitMiddleware(cooldown_seconds=2)

        # Check basic configuration
        assert middleware.cooldown_seconds == 2
        assert isinstance(middleware.user_last_callback, dict)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_admin_bypass(self):
        """Test admin user exemption from callback rate limiting.

        Verifies:
        - Admin ID recognition
        - Complete bypass of limits
        - Handler execution
        - No cooldown applied
        """
        from middlewares.rate_limit import CallbackRateLimitMiddleware

        middleware = CallbackRateLimitMiddleware()

        admin_id = int(os.getenv('ADMIN_ID', '123456789'))
        admin_user = User(id=admin_id, is_bot=False, first_name="Admin")
        callback = CallbackQuery(
            id="test_callback",
            from_user=admin_user,
            chat_instance="test",
            data="test_action",
            bot=AsyncMock()
        )

        handler = AsyncMock(return_value="success")
        data = {}

        result = await middleware(handler, callback, data)

        assert result == "success"
        handler.assert_called_once_with(callback, data)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_exempt_patterns(self):
        """Test that exempt patterns bypass rate limiting."""
        from middlewares.rate_limit import CallbackRateLimitMiddleware

        middleware = CallbackRateLimitMiddleware()

        user = User(id=123456789, is_bot=False, first_name="User")
        callback = CallbackQuery(
            id="test_callback",
            from_user=user,
            chat_instance="test",
            data="ask_another_question",  # This should be exempt
            bot=AsyncMock()
        )

        handler = AsyncMock(return_value="success")
        data = {}

        result = await middleware(handler, callback, data)

        assert result == "success"
        handler.assert_called_once_with(callback, data)

    @pytest.mark.asyncio
    @pytest.mark.middleware
    async def test_cooldown_enforcement(self):
        """Test cooldown enforcement for callbacks."""
        from middlewares.rate_limit import CallbackRateLimitMiddleware
        from datetime import datetime
        from aiogram.types import CallbackQuery, User, Chat
        from unittest.mock import create_autospec

        # Create middleware with test settings
        middleware = CallbackRateLimitMiddleware(cooldown_seconds=1)

        # Create mock callback using create_autospec
        callback = create_autospec(CallbackQuery, instance=True)
        callback.from_user = create_autospec(User, instance=True)
        callback.from_user.id = 123456789
        callback.from_user.is_bot = False
        callback.from_user.first_name = "Test"
        callback.data = "test_action"
        callback.answer = AsyncMock()

        # Create mock handler
        handler = AsyncMock()

        # Set last callback time
        middleware.user_last_callback[callback.from_user.id] = datetime.now()

        # Try to send callback within cooldown
        await middleware(handler, callback, {})

        # Should be blocked by cooldown
        handler.assert_not_called()
        callback.answer.assert_called_once_with(
            "⏳ Слишком быстро! Подождите секунду.",
            show_alert=False
        )


class TestErrorHandlerMiddleware:
    """Tests for ErrorHandlerMiddleware."""

    @pytest.mark.unit
    def test_middleware_initialization(self):
        """Test error handler middleware initialization."""
        from middlewares.error_handler import ErrorHandlerMiddleware

        middleware = ErrorHandlerMiddleware(notify_admin=True)

        assert middleware.notify_admin is True
        assert middleware.error_count == 0
        assert isinstance(middleware.last_errors, list)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_handler_execution(self):
        """Test that successful handlers execute normally."""
        from middlewares.error_handler import ErrorHandlerMiddleware

        middleware = ErrorHandlerMiddleware()

        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            from_user=User(id=123456789, is_bot=False, first_name="User"),
            text="Test          message",
            bot=AsyncMock()
        )

        handler = AsyncMock(return_value="success")
        data = {}

        result = await middleware(handler, message, data)

        assert result == "success"
        handler.assert_called_once_with(message, data)
        assert middleware.error_count == 0

    @pytest.mark.asyncio
    @pytest.mark.middleware
    async def test_error_handling_and_logging(self):
        """Test error handling and logging."""
        from middlewares.error_handler import ErrorHandlerMiddleware
        from aiogram.types import Message, User, Chat
        from unittest.mock import create_autospec

        middleware = ErrorHandlerMiddleware()

        # Create mock message with proper structure using create_autospec
        message = create_autospec(Message, instance=True)
        message.from_user = create_autospec(User, instance=True)
        message.from_user.id = 123456789
        message.from_user.username = "test_user"
        message.from_user.first_name = "Test"
        message.from_user.is_bot = False
        message.chat = create_autospec(Chat, instance=True)
        message.chat.id = 123456789
        message.chat.type = "private"
        message.text = "Test message"
        message.answer = AsyncMock()

        # Create failing handler
        async def failing_handler(event, data):
            raise ValueError("Test error")

        # Test error handling
        await middleware(failing_handler, message, {})

        # Should send error message to user
        message.answer.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.middleware
    async def test_telegram_api_error_handling(self):
        """Test handling of Telegram API errors."""
        from middlewares.error_handler import ErrorHandlerMiddleware
        from aiogram.exceptions import TelegramBadRequest
        from aiogram.types import Message, User, Chat
        from unittest.mock import create_autospec

        middleware = ErrorHandlerMiddleware()

        # Create mock message with proper structure using create_autospec
        message = create_autospec(Message, instance=True)
        message.from_user = create_autospec(User, instance=True)
        message.from_user.id = 123456789
        message.from_user.username = "test_user"
        message.from_user.first_name = "Test"
        message.from_user.is_bot = False
        message.chat = create_autospec(Chat, instance=True)
        message.chat.id = 123456789
        message.chat.type = "private"
        message.text = "Test message"
        message.answer = AsyncMock()

        # Create handler that raises TelegramBadRequest
        async def telegram_error_handler(event, data):
            raise TelegramBadRequest(message="Bad request")

        # Test error handling
        await middleware(telegram_error_handler, message, {})

        # Should send error message to user
        message.answer.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.middleware
    async def test_context_extraction(self):
        """Test error context extraction."""
        from middlewares.error_handler import ErrorHandlerMiddleware
        from aiogram.types import Message, User, Chat
        from unittest.mock import create_autospec

        middleware = ErrorHandlerMiddleware()

        # Create mock message with proper structure using create_autospec
        message = create_autospec(Message, instance=True)
        message.from_user = create_autospec(User, instance=True)
        message.from_user.id = 123456789
        message.from_user.username = "test_user"
        message.from_user.first_name = "Test"
        message.from_user.is_bot = False
        message.chat = create_autospec(Chat, instance=True)
        message.chat.id = 123456789
        message.chat.type = "private"
        message.text = "Test message"
        message.answer = AsyncMock()

        # Extract context
        context = middleware._extract_context(message, {})

        # Verify context
        assert context['user_id'] == 123456789
        assert context['username'] == "test_user"
        assert context['message_text'] == "Test message"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_middleware_with_handler_error(self):
        """Test middleware chain when handler raises error."""
        from middlewares.rate_limit import RateLimitMiddleware
        from middlewares.error_handler import ErrorHandlerMiddleware
        from aiogram.types import Message, User, Chat
        from unittest.mock import create_autospec

        rate_limiter = RateLimitMiddleware()
        error_handler = ErrorHandlerMiddleware(notify_admin=False)

        # Create mock message with proper structure using create_autospec
        message = create_autospec(Message, instance=True)
        message.from_user = create_autospec(User, instance=True)
        message.from_user.id = 123456789
        message.from_user.username = "test_user"
        message.from_user.first_name = "Test"
        message.from_user.is_bot = False
        message.chat = create_autospec(Chat, instance=True)
        message.chat.id = 123456789
        message.chat.type = "private"
        message.text = "Test message"
        message.answer = AsyncMock()

        # Handler that raises error
        async def failing_handler(event, data):
            raise ValueError("Handler failed")

        # Create middleware chain
        async def rate_limited_handler(event, data):
            try:
                return await rate_limiter(failing_handler, event, data)
            except ValueError as e:
                # Re-raise the error to be caught by error handler
                raise e

        # Test middleware chain
        try:
            await error_handler(rate_limited_handler, message, {})
        except Exception:
            pass  # We expect an error to be raised

        # Should send error message to user
        message.answer.assert_called_once()

        # Verify that error was logged
        assert error_handler.error_count == 1
        assert len(error_handler.last_errors) == 1
        assert error_handler.last_errors[0]['type'] == 'ValueError'
        assert error_handler.last_errors[0]['message'] == 'Handler failed'


class TestMiddlewareIntegration:
    """Test middleware working together."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_middleware_chain(self):
        """Test multiple middleware working in chain."""
        from middlewares.rate_limit import RateLimitMiddleware
        from middlewares.error_handler import ErrorHandlerMiddleware

        # Create middleware chain
        rate_limiter = RateLimitMiddleware()
        error_handler = ErrorHandlerMiddleware(notify_admin=False)

        # Create test           message
        user = User(id=123456789, is_bot=False, first_name="User")
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            from_user=user,
            text="Test message",
            bot=AsyncMock()
        )

        # Final handler
        final_handler = AsyncMock(return_value="success")

        # Create middleware chain
        async def rate_limited_handler(event, data):
            return await rate_limiter(final_handler, event, data)

        # Execute through error handler (outer middleware)
        result = await error_handler(rate_limited_handler, message, {})

        # Should execute successfully
        assert result == "success"
        final_handler.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_middleware_with_handler_error(self):
        """Test middleware chain when handler raises error."""
        from middlewares.rate_limit import RateLimitMiddleware
        from middlewares.error_handler import ErrorHandlerMiddleware
        from aiogram.types import Message, User, Chat
        from unittest.mock import create_autospec

        rate_limiter = RateLimitMiddleware()
        error_handler = ErrorHandlerMiddleware(notify_admin=False)

        # Create mock message with proper structure using create_autospec
        message = create_autospec(Message, instance=True)
        message.from_user = create_autospec(User, instance=True)
        message.from_user.id = 123456789
        message.from_user.username = "test_user"
        message.from_user.first_name = "Test"
        message.from_user.is_bot = False
        message.chat = create_autospec(Chat, instance=True)
        message.chat.id = 123456789
        message.chat.type = "private"
        message.text = "Test message"
        message.answer = AsyncMock()

        # Handler that raises error
        async def failing_handler(event, data):
            raise ValueError("Handler failed")

        # Create middleware chain
        async def rate_limited_handler(event, data):
            try:
                return await rate_limiter(failing_handler, event, data)
            except ValueError as e:
                # Re-raise the error to be caught by error handler
                raise e

        # Test middleware chain
        try:
            await error_handler(rate_limited_handler, message, {})
        except Exception:
            pass  # We expect an error to be raised

        # Should send error message to user
        message.answer.assert_called_once()

        # Verify that error was logged
        assert error_handler.error_count == 1
        assert len(error_handler.last_errors) == 1
        assert error_handler.last_errors[0]['type'] == 'ValueError'
        assert error_handler.last_errors[0]['message'] == 'Handler failed'


if __name__ == "__main__":
    pytest.main([
        "-v",
        "--tb=short",
        __file__
    ])
