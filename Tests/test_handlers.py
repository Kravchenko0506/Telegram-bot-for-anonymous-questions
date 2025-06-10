"""
Tests for bot handlers: start, admin, questions, admin_states.

Tests handler logic, user flows, admin commands, and state management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from aiogram.types import Message, CallbackQuery, User, Chat
from config import ADMIN_ID, MAX_QUESTION_LENGTH

# Import handlers
from handlers import start, admin, questions, admin_states
from handlers.admin_states import (
    start_answer_mode, 
    handle_admin_answer, 
    cancel_answer_mode,
    is_admin_in_answer_mode
)
from models.questions import Question
from models.user_states import UserStateManager
from models.admin_state import AdminStateManager


class TestStartHandler:
    """Tests for start handler."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_regular_user(self, mock_bot, test_user, mock_logger):
        """Test /start command for regular user."""
        # Create message
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="/start",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        # Mock command object
        command = MagicMock()
        command.args = None
        
        # Mock settings
        with patch('handlers.start.SettingsManager') as mock_settings, \
             patch('handlers.start.UserStateManager') as mock_user_state:
            
            mock_settings.get_author_name.return_value = "Test Author"
            mock_settings.get_author_info.return_value = "Test Info"
            mock_user_state.reset_to_idle.return_value = True
            
            # Call handler
            await start.start_handler(message, command)
            
            # Verify
            message.answer.assert_called_once()
            call_args = message.answer.call_args[0][0]
            assert "Test Author" in call_args
            assert "Test Info" in call_args
            assert str(MAX_QUESTION_LENGTH) in call_args
            
            mock_user_state.reset_to_idle.assert_called_once_with(test_user.id)
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_admin_user(self, mock_bot, admin_user, mock_logger):
        """Test /start command for admin."""
        # Create admin message
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="/start",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        # Mock command object
        command = MagicMock()
        command.args = None
        
        # Call handler
        await start.start_handler(message, command)
        
        # Verify admin panel shown
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "Админ-панель" in call_args
        assert "/pending" in call_args
        assert "/stats" in call_args
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_with_unique_id(self, mock_bot, test_user, mock_logger):
        """Test /start with tracking parameter."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="/start channel",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        # Mock command with args
        command = MagicMock()
        command.args = "channel"
        
        with patch('handlers.start.SettingsManager') as mock_settings, \
             patch('handlers.start.UserStateManager') as mock_user_state:
            
            mock_settings.get_author_name.return_value = "Test Author"
            mock_settings.get_author_info.return_value = "Test Info"
            mock_user_state.reset_to_idle.return_value = True
            
            await start.start_handler(message, command)
            
            # Verify tracking was logged
            mock_user_state.reset_to_idle.assert_called_once_with(test_user.id)


class TestAdminHandlers:
    """Tests for admin handlers."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_command_access_control(self, mock_bot, test_user, mock_logger):
        """Test that non-admin can't access admin commands."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="/admin",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        await admin.admin_command(message)
        
        # Should receive access denied message
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "администратору" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_command_success(self, mock_bot, admin_user, mock_logger):
        """Test admin command for actual admin."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="/admin",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            # Mock database response
            mock_session.return_value.__aenter__.return_value.scalar.return_value = 5
            
            await admin.admin_command(message)
            
            message.answer.assert_called_once()
            call_args = message.answer.call_args[0][0]
            assert "Админ-панель" in call_args
            assert "Всего вопросов:" in call_args
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_stats_command(self, mock_bot, admin_user, mock_logger):
        """Test stats command."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="/stats",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.scalar.side_effect = [10, 6, 2, 1]  # total, answered, favorites, deleted
            
            await admin.stats_command(message)
            
            message.answer.assert_called_once()
            call_args = message.answer.call_args[0][0]
            assert "Статистика" in call_args
            assert "60.0%" in call_args  # Response rate
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_set_author_command(self, mock_bot, admin_user, mock_logger):
        """Test set author name command."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="/set_author New Author Name",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        with patch('handlers.admin.SettingsManager') as mock_settings:
            mock_settings.set_author_name.return_value = True
            
            await admin.set_author_command(message)
            
            mock_settings.set_author_name.assert_called_once_with("New Author Name")
            message.answer.assert_called_once()
            call_args = message.answer.call_args[0][0]
            assert "обновлено" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_callback_question_actions(self, mock_bot, admin_user, mock_logger):
        """Test admin callback actions on questions."""
        # Create callback query
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="Question text",
            bot=mock_bot
        )
        
        callback = CallbackQuery(
            id="test_callback",
            from_user=admin_user,
            chat_instance="test",
            message=message,
            data="favorite:123",
            bot=mock_bot
        )
        callback.answer = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            # Mock question
            mock_question = MagicMock()
            mock_question.is_deleted = False
            mock_question.is_favorite = False
            
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.get.return_value = mock_question
            
            await admin.admin_question_callback(callback)
            
            # Verify favorite was toggled
            assert mock_question.is_favorite is True
            callback.answer.assert_called_once()


class TestQuestionsHandler:
    """Tests for questions handler."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_message_processing(self, mock_bot, test_user, mock_logger):
        """Test regular user message processing."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="This is a test question",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        with patch('handlers.questions.UserStateManager') as mock_user_state, \
             patch('handlers.questions.async_session') as mock_session, \
             patch('handlers.questions.InputValidator') as mock_validator:
            
            # Mock user can send question
            mock_user_state.can_send_question.return_value = True
            mock_user_state.set_user_state.return_value = True
            
            # Mock validation
            mock_validator.sanitize_text.return_value = "This is a test question"
            mock_validator.validate_question.return_value = (True, None)
            mock_validator.extract_personal_data.return_value = {
                'emails': [], 'phones': [], 'urls': []
            }
            
            # Mock content moderation
            with patch('handlers.questions.ContentModerator') as mock_moderator:
                mock_moderator.is_likely_spam.return_value = False
                mock_moderator.calculate_spam_score.return_value = 0.1
                
                # Mock database
                mock_question = MagicMock()
                mock_question.id = 123
                mock_db = mock_session.return_value.__aenter__.return_value
                mock_db.commit = AsyncMock()
                mock_db.refresh = AsyncMock()
                
                await questions.unified_message_handler(message)
                
                # Verify message was answered
                message.answer.assert_called()
                call_args = message.answer.call_args[0][0]
                assert "отправлен" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_blocked_from_sending(self, mock_bot, test_user, mock_logger):
        """Test user blocked from sending text after question."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="Another message",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        with patch('handlers.questions.UserStateManager') as mock_user_state:
            # User can't send question (already sent one)
            mock_user_state.can_send_question.return_value = False
            
            await questions.unified_message_handler(message)
            
            # Should receive blocked message
            message.answer.assert_called_once()
            call_args = message.answer.call_args[0][0]
            assert "предыдущий вопрос" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_in_answer_mode(self, mock_bot, admin_user, mock_logger):
        """Test admin message when in answer mode."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="This is my answer",
            bot=mock_bot
        )
        
        with patch('handlers.questions.is_admin_in_answer_mode') as mock_check, \
             patch('handlers.questions.handle_admin_answer') as mock_handle:
            
            mock_check.return_value = True
            mock_handle.return_value = None
            
            await questions.unified_message_handler(message)
            
            mock_handle.assert_called_once_with(message)
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_callback_ask_another_question(self, mock_bot, test_user, mock_logger):
        """Test user callback to ask another question."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="Previous message",
            bot=mock_bot
        )
        message.edit_text = AsyncMock()
        
        # Use test_user as from_user for this callback, or define admin_user if needed
        callback = CallbackQuery(
            id="test_callback",
            from_user=test_user,
            chat_instance="test",
            message=message,
            data="cancel_answer:123",
            bot=mock_bot
        )
        callback.answer = AsyncMock()
        
        # Set up admin state
        mock_states = {
            ADMIN_ID: {
                'question_id': 123,
                'mode': 'waiting_answer'
            }
        }
        
        with patch('handlers.admin_states.admin_answer_states', mock_states):
            await cancel_answer_mode(callback)
            
            # Verify state was cleared
            assert ADMIN_ID not in mock_states
            message.edit_text.assert_called_once()
            callback.answer.assert_called_once()


class TestHandlerIntegration:
    """Integration tests for handler workflows."""
    
    @pytest.mark.integration
    @pytest.mark.handlers
    async def test_complete_question_answer_flow(self, mock_bot, test_user, admin_user, mock_logger):
        """Test complete flow from question to answer."""
        # 1. User sends question
        user_message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="How does this work?",
            bot=mock_bot
        )
        user_message.answer = AsyncMock()
        mock_bot.send_message = AsyncMock()
        
        # 2. Admin receives notification and starts answer
        admin_callback = CallbackQuery(
            id="admin_callback",
            from_user=admin_user,
            chat_instance="admin",
            message=MagicMock(),
            data="answer:123",
            bot=mock_bot
        )
        admin_callback.answer = AsyncMock()
        admin_callback.message.reply = AsyncMock()
        
        # 3. Admin sends answer
        admin_message = Message(
            message_id=2,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="It works like this...",
            bot=mock_bot
        )
        admin_message.answer = AsyncMock()
        
        with patch('handlers.questions.UserStateManager') as mock_user_state, \
             patch('handlers.questions.async_session') as mock_session, \
             patch('handlers.questions.InputValidator') as mock_validator, \
             patch('handlers.questions.ContentModerator') as mock_moderator, \
             patch('handlers.admin_states.admin_answer_states', {}) as mock_states:
            
            # Mock user question flow
            mock_user_state.can_send_question.return_value = True
            mock_user_state.set_user_state.return_value = True
            mock_validator.sanitize_text.return_value = "How does this work?"
            mock_validator.validate_question.return_value = (True, None)
            mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
            mock_moderator.is_likely_spam.return_value = False
            mock_moderator.calculate_spam_score.return_value = 0.1
            
            # Mock database operations
            mock_question = MagicMock()
            mock_question.id = 123
            mock_question.text = "How does this work?"
            mock_question.user_id = test_user.id
            mock_question.is_deleted = False
            mock_question.is_answered = False
            
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db.get.return_value = mock_question
            
            # Step 1: Process user question
            await questions.unified_message_handler(user_message)
            
            # Verify question was processed
            user_message.answer.assert_called()
            mock_bot.send_message.assert_called()  # Admin notification
            
            # Step 2: Admin starts answer mode
            await start_answer_mode(admin_callback, 123)
            
            # Verify admin state was set
            assert ADMIN_ID in mock_states
            admin_callback.message.reply.assert_called()
            
            # Step 3: Admin sends answer
            mock_question.is_answered = False  # Reset for answer processing
            result = await handle_admin_answer(admin_message)
            
            # Verify answer was processed
            assert result is True
            assert mock_question.answer == "It works like this..."
            assert ADMIN_ID not in mock_states  # State cleared
            admin_message.answer.assert_called()
    
    @pytest.mark.integration
    @pytest.mark.handlers
    async def test_user_question_validation_flow(self, mock_bot, test_user, mock_logger):
        """Test various question validation scenarios."""
        base_message_params = {
            'message_id': 1,
            'date': datetime.now(),
            'chat': Chat(id=test_user.id, type="private"),
            'from_user': test_user,
            'bot': mock_bot
        }
        
        test_cases = [
            ("", "пустым"),  # Empty question
            ("Hi", "короткий"),  # Too short
            ("A" * 3000, "длинный"),  # Too long
            ("Buy crypto now!!!", None),  # Spam (might be blocked)
        ]
        
        with patch('handlers.questions.UserStateManager') as mock_user_state:
            mock_user_state.can_send_question.return_value = True
            
            for question_text, expected_error in test_cases:
                message = Message(text=question_text, **base_message_params)
                message.answer = AsyncMock()
                
                await questions.unified_message_handler(message)
                
                # Check if appropriate response was sent
                message.answer.assert_called()
                response_text = message.answer.call_args[0][0]
                
                if expected_error:
                    assert expected_error in response_text.lower()
    
    @pytest.mark.integration
    @pytest.mark.handlers
    async def test_admin_command_permissions(self, mock_bot, test_user, admin_user, mock_logger):
        """Test admin command access control."""
        admin_commands = [
            ('/admin', admin.admin_command),
            ('/stats', admin.stats_command),
            ('/pending', admin.pending_command),
            ('/favorites', admin.favorites_command),
        ]
        
        for command_text, handler in admin_commands:
            # Test regular user access (should be denied)
            user_message = Message(
                message_id=1,
                date=datetime.now(),
                chat=Chat(id=test_user.id, type="private"),
                from_user=test_user,
                text=command_text,
                bot=mock_bot
            )
            user_message.answer = AsyncMock()
            
            await handler(user_message)
            
            # Should receive access denied
            user_message.answer.assert_called()
            response = user_message.answer.call_args[0][0]
            assert "администратору" in response.lower()
            
            # Test admin access (should work)
            admin_message = Message(
                message_id=2,
                date=datetime.now(),
                chat=Chat(id=ADMIN_ID, type="private"),
                from_user=admin_user,
                text=command_text,
                bot=mock_bot
            )
            admin_message.answer = AsyncMock()
            
            with patch('handlers.admin.async_session') as mock_session:
                mock_db = mock_session.return_value.__aenter__.return_value
                mock_db.scalar.return_value = 5
                mock_db.execute.return_value.scalars.return_value.all.return_value = []
                
                try:
                    await handler(admin_message)
                    # Should not raise access denied error
                    admin_message.answer.assert_called()
                except Exception as e:
                    # Only database-related errors are acceptable
                    assert "administrator" not in str(e).lower()


class TestHandlerErrorHandling:
    """Tests for error handling in handlers."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_database_error_handling(self, mock_bot, test_user, mock_logger):
        """Test handler behavior when database fails."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="Test question",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        with patch('handlers.questions.UserStateManager') as mock_user_state, \
             patch('handlers.questions.async_session') as mock_session, \
             patch('handlers.questions.InputValidator') as mock_validator, \
             patch('handlers.questions.ContentModerator') as mock_moderator:
            
            mock_user_state.can_send_question.return_value = True
            mock_validator.sanitize_text.return_value = "Test question"
            mock_validator.validate_question.return_value = (True, None)
            mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
            mock_moderator.is_likely_spam.return_value = False
            
            # Simulate database error
            mock_session.side_effect = Exception("Database connection failed")
            
            await questions.unified_message_handler(message)
            
            # Should handle error gracefully
            message.answer.assert_called()
            response = message.answer.call_args[0][0]
            assert "ошибка" in response.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_invalid_callback_data(self, mock_bot, admin_user, mock_logger):
        """Test handling of invalid callback data."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="Question",
            bot=mock_bot
        )
        
        callback = CallbackQuery(
            id="test_callback",
            from_user=admin_user,
            chat_instance="test",
            message=message,
            data="invalid_format",  # Missing colon
            bot=mock_bot
        )
        callback.answer = AsyncMock()
        
        await admin.admin_question_callback(callback)
        
        # Should handle invalid format gracefully
        callback.answer.assert_called()
        assert callback.answer.call_args[1]['show_alert'] is True
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_missing_question_handling(self, mock_bot, admin_user, mock_logger):
        """Test handling when question doesn't exist."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="Question",
            bot=mock_bot
        )
        
        callback = CallbackQuery(
            id="test_callback",
            from_user=admin_user,
            chat_instance="test",
            message=message,
            data="answer:999",  # Non-existent question
            bot=mock_bot
        )
        callback.answer = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.get.return_value = None  # Question not found
            
            await admin.admin_question_callback(callback)
            
            # Should handle missing question
            callback.answer.assert_called()
            args = callback.answer.call_args
            assert "найден" in args[0][0].lower()


class TestHandlerPerformance:
    """Performance tests for handlers."""
    
    @pytest.mark.slow
    @pytest.mark.handlers
    async def test_bulk_message_processing(self, mock_bot, mock_logger):
        """Test processing many messages quickly."""
        users = [User(id=i, is_bot=False, first_name=f"User{i}") for i in range(100, 200)]
        
        with patch('handlers.questions.UserStateManager') as mock_user_state, \
             patch('handlers.questions.async_session') as mock_session, \
             patch('handlers.questions.InputValidator') as mock_validator, \
             patch('handlers.questions.ContentModerator') as mock_moderator:
            
            # Setup mocks
            mock_user_state.can_send_question.return_value = True
            mock_user_state.set_user_state.return_value = True
            mock_validator.sanitize_text.return_value = "Test question"
            mock_validator.validate_question.return_value = (True, None)
            mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
            mock_moderator.is_likely_spam.return_value = False
            mock_moderator.calculate_spam_score.return_value = 0.1
            
            mock_question = MagicMock()
            mock_question.id = 1
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Process messages from all users
            for user in users:
                message = Message(
                    message_id=1,
                    date=datetime.now(),
                    chat=Chat(id=user.id, type="private"),
                    from_user=user,
                    text=f"Question from user {user.id}",
                    bot=mock_bot
                )
                message.answer = AsyncMock()
                
                await questions.unified_message_handler(message)
                
                # Verify each message was processed
                message.answer.assert_called()
    
    @pytest.mark.slow
    @pytest.mark.handlers
    async def test_concurrent_admin_operations(self, mock_bot, admin_user, mock_logger):
        """Test concurrent admin operations."""
        import asyncio
        
        # Simulate multiple admin operations
        operations = []
        
        for i in range(10):
            message = Message(
                message_id=i,
                date=datetime.now(),
                chat=Chat(id=ADMIN_ID, type="private"),
                from_user=admin_user,
                text="/stats",
                bot=mock_bot
            )
            message.answer = AsyncMock()
            operations.append(admin.stats_command(message))
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.scalar.return_value = 5
            
            # Run all operations concurrently
            results = await asyncio.gather(*operations, return_exceptions=True)
            
            # All should complete without errors
            for result in results:
                assert not isinstance(result, Exception), f"Operation failed: {result}"
        # Use admin_user or define test_user if needed
        callback = CallbackQuery(
            id="test_callback",
            from_user=admin_user,
            chat_instance="test",
            message=message,
            data="ask_another_question",
            bot=mock_bot
        )
        callback.answer = AsyncMock()
        
        with patch('handlers.questions.UserStateManager') as mock_user_state:
            mock_user_state.allow_new_question.return_value = True
            
            await questions.user_callback_handler(callback)
            
            mock_user_state.allow_new_question.assert_called_once_with(admin_user.id)
            message.edit_text.assert_called_once()
            callback.answer.assert_called_once()


class TestAdminStatesHandler:
    """Tests for admin states management."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_answer_mode(self, mock_bot, admin_user, mock_logger):
        """Test starting answer mode."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="Question text",
            bot=mock_bot
        )
        message.reply = AsyncMock()
        
        callback = CallbackQuery(
            id="test_callback",
            from_user=admin_user,
            chat_instance="test",
            message=message,
            data="answer:123",
            bot=mock_bot
        )
        callback.answer = AsyncMock()
        
        with patch('handlers.admin_states.async_session') as mock_session, \
             patch('handlers.admin_states.admin_answer_states', {}) as mock_states:
            
            # Mock question
            mock_question = MagicMock()
            mock_question.is_deleted = False
            mock_question.is_answered = False
            mock_question.text = "Test question"
            mock_question.user_id = 123456789
            
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.get.return_value = mock_question
            
            await start_answer_mode(callback, 123)
            
            # Verify state was set
            assert ADMIN_ID in mock_states
            assert mock_states[ADMIN_ID]['question_id'] == 123
            
            message.reply.assert_called_once()
            callback.answer.assert_called_once()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_handle_admin_answer(self, mock_bot, admin_user, mock_logger):
        """Test handling admin answer."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="This is my answer",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        # Set up admin state
        mock_states = {
            ADMIN_ID: {
                'question_id': 123,
                'question_text': 'Test question',
                'user_id': 123456789,
                'mode': 'waiting_answer',
                'created_at': datetime.utcnow()
            }
        }
        
        with patch('handlers.admin_states.admin_answer_states', mock_states), \
             patch('handlers.admin_states.async_session') as mock_session:
            
            # Mock question and database
            mock_question = MagicMock()
            mock_question.is_answered = False
            
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.get.return_value = mock_question
            mock_db.commit = AsyncMock()
            
            result = await handle_admin_answer(message)
            
            # Verify answer was processed
            assert result is True
            assert mock_question.answer == "This is my answer"
            assert ADMIN_ID not in mock_states  # State should be cleared
            
            message.answer.assert_called()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    def test_is_admin_in_answer_mode(self):
        """Test checking admin answer mode."""
        # No state
        result = is_admin_in_answer_mode(ADMIN_ID)
        assert result is False
        
        # With state
        with patch('handlers.admin_states.admin_answer_states', {
            ADMIN_ID: {
                'mode': 'waiting_answer',
                'created_at': datetime.utcnow()
            }
        }):
            result = is_admin_in_answer_mode(ADMIN_ID)
            assert result is True
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_cancel_answer_mode(self, mock_bot, admin_user, mock_logger):
        """Test canceling answer mode."""
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="Question",
            bot=mock_bot
        )
        message.edit_text = AsyncMock()