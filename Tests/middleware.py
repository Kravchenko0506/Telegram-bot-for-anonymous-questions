"""
Tests for middleware: rate limiting and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from aiogram.types import Message, CallbackQuery, User, Chat
from config import ADMIN_ID, RATE_LIMIT_QUESTIONS_PER_HOUR

from middlewares.rate_limit import RateLimitMiddleware, CallbackRateLimitMiddleware
from middlewares.error_handler import ErrorHandlerMiddleware


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""
    
    @pytest.mark.unit
    def test_middleware_initialization(self):
        """Test middleware initialization with default values."""
        middleware = RateLimitMiddleware()
        
        assert middleware.questions_per_hour == RATE_LIMIT_QUESTIONS_PER_HOUR
        assert middleware.cooldown_seconds > 0
        assert isinstance(middleware.user_questions, dict)
        assert isinstance(middleware.user_last_message, dict)
    
    @pytest.mark.unit
    async def test_admin_bypass(self):
        """Test that admin bypasses rate limiting."""
        middleware = RateLimitMiddleware()
        
        # Create admin message
        admin_user = User(id=ADMIN_ID, is_bot=False, first_name="Admin")
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
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
    def test_user_stats(self):
        """Test getting user statistics."""
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


class TestCallbackRateLimitMiddleware:
    """Tests for CallbackRateLimitMiddleware."""
    
    @pytest.mark.unit
    def test_middleware_initialization(self):
        """Test callback rate limit middleware initialization."""
        middleware = CallbackRateLimitMiddleware(cooldown_seconds=2)
        
        assert middleware.cooldown_seconds == 2
        assert isinstance(middleware.user_last_callback, dict)
        assert len(middleware.exempt_patterns) > 0
    
    @pytest.mark.unit
    async def test_admin_bypass(self):
        """Test admin bypass for callback rate limiting."""
        middleware = CallbackRateLimitMiddleware()
        
        admin_user = User(id=ADMIN_ID, is_bot=False, first_name="Admin")
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


class TestErrorHandlerMiddleware:
    """Tests for ErrorHandlerMiddleware."""
    
    @pytest.mark.unit
    def test_middleware_initialization(self):
        """Test error handler middleware initialization."""
        middleware = ErrorHandlerMiddleware(notify_admin=True)
        
        assert middleware.notify_admin is True
        assert middleware.error_count == 0
        assert isinstance(middleware.last_errors, list)
    
    @pytest.mark.unit
    async def test_successful_handler_execution(self):
        """Test that successful handlers execute normally."""
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
    def test_error_stats(self):
        """Test error statistics collection."""
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


if __name__ == "__main__":
    pytest.main([
        "-v",
        "--tb=short",
        __file__
    ])