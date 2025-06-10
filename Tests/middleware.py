"""
Fixed tests for middleware: rate limiting and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import os

from aiogram.types import Message, CallbackQuery, User, Chat
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""
    
    @pytest.mark.unit
    def test_middleware_initialization(self):
        """Test middleware initialization with default values."""
        from middlewares.rate_limit import RateLimitMiddleware
        
        # Get rate limit from environment
        rate_limit = int(os.getenv('RATE_LIMIT_QUESTIONS_PER_HOUR', '5'))
        cooldown = int(os.getenv('RATE_LIMIT_COOLDOWN_SECONDS', '30'))
        
        middleware = RateLimitMiddleware()
        
        assert middleware.questions_per_hour == rate_limit
        assert middleware.cooldown_seconds == cooldown
        assert isinstance(middleware.user_questions, dict)
        assert isinstance(middleware.user_last_message, dict)
    
    @pytest.mark.unit
    async def test_admin_bypass(self):
        """Test that admin bypasses rate limiting."""
        from middlewares.rate_limit import RateLimitMiddleware
        
        middleware = RateLimitMiddleware()
        
        # Create admin message
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
    
    @pytest.mark.unit
    async def test_command_bypass(self):
        """Test that commands bypass rate limiting."""
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
    
    @pytest.mark.unit 
    async def test_first_question_no_cooldown(self):
        """Test that first question from user has no cooldown."""
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
    
    @pytest.mark.unit
    async def test_cooldown_enforcement(self):
        """Test cooldown is enforced for subsequent questions."""
        from middlewares.rate_limit import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(cooldown_seconds=30)
        user_id = 123456789
        
        # Set user as having sent first question
        middleware.user_has_sent_first_question.add(user_id)
        
        # Set last question time to now (within cooldown)
        middleware.user_last_question[user_id] = datetime.now()
        
        user = User(id=user_id, is_bot=False, first_name="User")
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=user_id, type="private"),
            from_user=user,
            text="Second question",
            bot=AsyncMock()
        )
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
    
    @pytest.mark.unit
    async def test_hourly_limit_enforcement(self):
        """Test hourly question limit is enforced."""
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
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=user_id, type="private"),
            from_user=user,
            text="Too many questions",
            bot=AsyncMock()
        )
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
    """Tests for CallbackRateLimitMiddleware."""
    
    @pytest.mark.unit
    def test_middleware_initialization(self):
        """Test callback rate limit middleware initialization."""
        from middlewares.rate_limit import CallbackRateLimitMiddleware
        
        middleware = CallbackRateLimitMiddleware(cooldown_seconds=2)
        
        assert middleware.cooldown_seconds == 2
        assert isinstance(middleware.user_last_callback, dict)
        assert len(middleware.exempt_patterns) > 0
    
    @pytest.mark.unit
    async def test_admin_bypass(self):
        """Test admin bypass for callback rate limiting."""
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
    
    @pytest.mark.unit
    async def test_cooldown_enforcement(self):
        """Test cooldown enforcement for callbacks."""
        from middlewares.rate_limit import CallbackRateLimitMiddleware
        
        middleware = CallbackRateLimitMiddleware(cooldown_seconds=2)
        user_id = 123456789
        
        # Set last callback time to now
        middleware.user_last_callback[user_id] = datetime.now()
        
        user = User(id=user_id, is_bot=False, first_name="User")
        callback = CallbackQuery(
            id="test_callback",
            from_user=user,
            chat_instance="test",
            data="some_action",
            bot=AsyncMock()
        )
        callback.answer = AsyncMock()
        
        handler = AsyncMock(return_value="success")
        data = {}
        
        result = await middleware(handler, callback, data)
        
        # Should be blocked by cooldown
        assert result is None
        callback.answer.assert_called_once()
        handler.assert_not_called()


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
            text="Test message",
            bot=AsyncMock()
        )
        
        handler = AsyncMock(return_value="success")
        data = {}
        
        result = await middleware(handler, message, data)
        
        assert result == "success"
        handler.assert_called_once_with(message, data)
        assert middleware.error_count == 0
    
    @pytest.mark.unit
    async def test_error_handling_and_logging(self):
        """Test that errors are caught and logged."""
        from middlewares.error_handler import ErrorHandlerMiddleware
        
        middleware = ErrorHandlerMiddleware(notify_admin=False)  # Disable admin notifications
        
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            from_user=User(id=123456789, is_bot=False, first_name="User"),
            text="Test message",
            bot=AsyncMock()
        )
        message.answer = AsyncMock()
        
        # Handler that raises an exception
        async def failing_handler(event, data):
            raise ValueError("Test error")
        
        # Should not raise exception
        await middleware(failing_handler, message, {})
        
        # Error should be logged
        assert middleware.error_count == 1
        assert len(middleware.last_errors) == 1
        
        # User should receive error message
        message.answer.assert_called_once()
    
    @pytest.mark.unit
    async def test_telegram_api_error_handling(self):
        """Test handling of Telegram API errors."""
        from middlewares.error_handler import ErrorHandlerMiddleware
        
        middleware = ErrorHandlerMiddleware(notify_admin=False)
        
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            from_user=User(id=123456789, is_bot=False, first_name="User"),
            text="Test message",
            bot=AsyncMock()
        )
        message.answer = AsyncMock()
        
        # Handler that raises Telegram API error
        async def telegram_error_handler(event, data):
            raise TelegramBadRequest(method="sendMessage", message="Bad request")
        
        await middleware(telegram_error_handler, message, {})
        
        # Error should be logged
        assert middleware.error_count == 1
        
        # User should receive appropriate error message
        message.answer.assert_called_once()
    
    @pytest.mark.unit
    async def test_telegram_forbidden_error_handling(self):
        """Test handling of TelegramForbiddenError (user blocked bot)."""
        from middlewares.error_handler import ErrorHandlerMiddleware
        
        middleware = ErrorHandlerMiddleware(notify_admin=False)
        
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            from_user=User(id=123456789, is_bot=False, first_name="User"),
            text="Test message",
            bot=AsyncMock()
        )
        
        # Handler that raises TelegramForbiddenError
        async def forbidden_handler(event, data):
            raise TelegramForbiddenError(method="sendMessage", message="Forbidden: bot was blocked by the user")
        
        await middleware(forbidden_handler, message, {})
        
        # Error should be logged but no user message sent (user blocked bot)
        assert middleware.error_count == 1
    
    @pytest.mark.unit
    def test_error_stats(self):
        """Test error statistics collection."""
        from middlewares.error_handler import ErrorHandlerMiddleware
        
        middleware = ErrorHandlerMiddleware()
        
        # Simulate some errors
        test_error = {
            'type': 'ValueError',
            'message': 'Test error',
            'context': {'user_id': 123},
            'timestamp': datetime.now()
        }
        
        middleware.last_errors.append(test_error)
        middleware.error_count = 1
        
        stats = middleware.get_error_stats()
        
        assert stats['total_errors'] == 1
        assert 'error_types' in stats
        assert 'last_error' in stats
        assert stats['last_error'] == test_error
    
    @pytest.mark.unit
    def test_context_extraction(self):
        """Test context extraction from different event types."""
        from middlewares.error_handler import ErrorHandlerMiddleware
        
        middleware = ErrorHandlerMiddleware()
        
        # Test with Message
        user = User(id=123456789, is_bot=False, first_name="User")
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            from_user=user,
            text="Test message",
            bot=AsyncMock()
        )
        
        context = middleware._extract_context(message, {})
        
        assert 'user_id' in context
        assert 'message_text' in context
        assert 'event_type' in context
        assert context['user_id'] == 123456789
        assert context['message_text'] == "Test message"
        
        # Test with CallbackQuery
        callback = CallbackQuery(
            id="test_callback",
            from_user=user,
            chat_instance="test",
            data="test_action",
            bot=AsyncMock()
        )
        
        context = middleware._extract_context(callback, {})
        
        assert 'user_id' in context
        assert 'callback_data' in context
        assert 'event_type' in context
        assert context['user_id'] == 123456789
        assert context['callback_data'] == "test_action"
    
    @pytest.mark.unit
    def test_critical_error_detection(self):
        """Test detection of critical errors that should notify admin."""
        from middlewares.error_handler import ErrorHandlerMiddleware
        from sqlalchemy.exc import DatabaseError
        
        middleware = ErrorHandlerMiddleware()
        
        # Test critical errors
        critical_errors = [
            DatabaseError("statement", "params", "orig"),
            TelegramForbiddenError("method", "Bot token is invalid")
        ]
        
        for error in critical_errors:
            assert middleware._is_critical_error(error) is True
        
        # Test non-critical errors
        non_critical_errors = [
            ValueError("Simple validation error"),
            KeyError("Missing key")
        ]
        
        for error in non_critical_errors:
            assert middleware._is_critical_error(error) is False


class TestMiddlewareIntegration:
    """Test middleware working together."""
    
    @pytest.mark.unit
    async def test_middleware_chain(self):
        """Test multiple middleware working in chain."""
        from middlewares.rate_limit import RateLimitMiddleware
        from middlewares.error_handler import ErrorHandlerMiddleware
        
        # Create middleware chain
        rate_limiter = RateLimitMiddleware()
        error_handler = ErrorHandlerMiddleware(notify_admin=False)
        
        # Create test message
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
    
    @pytest.mark.unit
    async def test_middleware_with_handler_error(self):
        """Test middleware chain when handler raises error."""
        from middlewares.rate_limit import RateLimitMiddleware
        from middlewares.error_handler import ErrorHandlerMiddleware
        
        rate_limiter = RateLimitMiddleware()
        error_handler = ErrorHandlerMiddleware(notify_admin=False)
        
        user = User(id=123456789, is_bot=False, first_name="User")
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            from_user=user,
            text="Test message",
            bot=AsyncMock()
        )
        message.answer = AsyncMock()
        
        # Handler that raises error
        async def failing_handler(event, data):
            raise ValueError("Handler failed")
        
        # Create middleware chain
        async def rate_limited_handler(event, data):
            return await rate_limiter(failing_handler, event, data)
        
        # Should not raise exception due to error handler
        await error_handler(rate_limited_handler, message, {})
        
        # Error should be caught and user notified
        assert error_handler.error_count == 1
        message.answer.assert_called_once()


if __name__ == "__main__":
    pytest.main([
        "-v",
        "--tb=short",
        __file__
    ])