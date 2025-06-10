"""
Testing critical bot functionality:
- /start command for users and admin
- User question handling
- Admin functions
- Callback queries
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestCriticalStartFlow:
    """Tests for critical /start command functionality."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_regular_user(
        self, 
        test_message, 
        mock_settings_manager,
        mock_user_state_manager
    ):
        """Test /start command for a regular user - entry point to the bot."""
        # Import handler here to avoid circular imports
        from handlers.start import start_handler
        
        # Mock command object
        command = MagicMock()
        command.args = None
        
        # Call handler
        await start_handler(test_message, command)
        
        # Check that a welcome message was sent
        test_message.answer.assert_called_once()
        call_args = test_message.answer.call_args[0][0]
        
        # Check that the message contains data from settings
        assert "Test Author" in call_args
        assert "2500" in call_args  # Default MAX_QUESTION_LENGTH
        
        # Check that user state was reset to idle
        mock_user_state_manager.reset_to_idle.assert_called_once()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_admin_user(self, admin_message):
        """Test /start command for admin - should show admin panel."""
        from handlers.start import start_handler
        
        command = MagicMock()
        command.args = None
        
        await start_handler(admin_message, command)
        
        # Check that admin panel is shown
        admin_message.answer.assert_called_once()
        call_args = admin_message.answer.call_args[0][0]
        assert "Админ-панель" in call_args
        assert "/stats" in call_args or "статистика" in call_args.lower()


class TestCriticalQuestionFlow:
    """Tests for critical question handling functionality - bot core."""
    
    @pytest.mark.handlers
    @pytest.mark.integration
    async def test_user_sends_valid_question(
        self, 
        test_message,
        mock_user_state_manager,
        mock_async_session,
        mock_input_validator,
        mock_content_moderator
    ):
        """Test the full process of sending a valid question."""
        from handlers.questions import unified_message_handler
        
        test_message.text = "How does this bot work?"
        
        # Set up mocks for a successful scenario
        mock_user_state_manager.can_send_question.return_value = True
        
        # Mock database session
        mock_db = mock_async_session.return_value.__aenter__.return_value
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock question creation - add ID after commit
        def set_question_id(question):
            question.id = 123
        mock_db.refresh.side_effect = set_question_id
        
        await unified_message_handler(test_message)
        
        # Check that the question was processed successfully
        test_message.answer.assert_called()
        call_args = test_message.answer.call_args[0][0]
        assert "отправлен" in call_args.lower() or "успешно" in call_args.lower()
        
        # Check that user state was updated
        mock_user_state_manager.set_user_state.assert_called()
    
    @pytest.mark.handlers  
    @pytest.mark.unit
    async def test_user_blocked_after_question(
        self,
        test_message,
        mock_user_state_manager
    ):
        """Test user is blocked after sending a question."""
        from handlers.questions import unified_message_handler
        
        test_message.text = "Another message"
        
        # User cannot send a question (already sent)
        mock_user_state_manager.can_send_question.return_value = False
        
        await unified_message_handler(test_message)
        
        # Should receive a blocking message
        test_message.answer.assert_called_once()
        call_args = test_message.answer.call_args[0][0]
        assert "предыдущий вопрос" in call_args.lower() or "кнопку" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_invalid_question_rejected(
        self,
        test_message,
        mock_user_state_manager,
        mock_input_validator
    ):
        """Test rejection of an invalid question with appropriate message."""
        from handlers.questions import unified_message_handler
        
        test_message.text = ""  # Empty question
        
        # Set up mocks
        mock_user_state_manager.can_send_question.return_value = True
        mock_input_validator.sanitize_text.return_value = ""
        mock_input_validator.validate_question.return_value = (False, "Вопрос не может быть пустым")
        
        await unified_message_handler(test_message)
        
        # Should receive an error message
        test_message.answer.assert_called_once()
        call_args = test_message.answer.call_args[0][0]
        assert "пустым" in call_args.lower()


class TestCriticalAdminFlow:
    """Tests for critical admin functionality."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_access_control(self, test_message):
        """Test access control - non-admin should not get access."""
        from handlers.admin import admin_command
        
        await admin_command(test_message)
        
        # Should receive an access denied message
        test_message.answer.assert_called_once()
        call_args = test_message.answer.call_args[0][0]
        assert "администратору" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit  
    async def test_admin_command_success(self, admin_message, mock_async_session):
        """Test successful execution of admin command."""
        from handlers.admin import admin_command
        
        # Mock database response for statistics
        mock_db = mock_async_session.return_value.__aenter__.return_value
        mock_db.scalar.return_value = 5
        
        await admin_command(admin_message)
        
        admin_message.answer.assert_called_once()
        call_args = admin_message.answer.call_args[0][0]
        assert "Админ-панель" in call_args or "админ" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.integration
    async def test_admin_answer_question_flow(
        self,
        admin_message, 
        test_callback,
        mock_async_session
    ):
        """Test the full process of admin answering a question."""
        from handlers.admin_states import start_answer_mode, handle_admin_answer
        
        # Get ADMIN_ID from environment
        admin_id = int(os.getenv('ADMIN_ID', '123456789'))
        
        # Step 1: Admin starts answer mode
        test_callback.data = "answer:123"
        test_callback.from_user.id = admin_id
        
        # Mock question
        mock_question = MagicMock()
        mock_question.is_deleted = False
        mock_question.is_answered = False
        mock_question.text = "Test question"
        mock_question.user_id = 123456789
        
        mock_db = mock_async_session.return_value.__aenter__.return_value
        mock_db.get.return_value = mock_question
        
        await start_answer_mode(test_callback, 123)
        
        # Check that answer mode started
        test_callback.message.reply.assert_called_once()
        
        # Step 2: Admin sends answer
        admin_message.text = "This is my answer"
        admin_message.from_user.id = admin_id
        
        # Simulate admin state via patch
        with patch('handlers.admin_states.admin_answer_states', {
            admin_id: {
                'question_id': 123,
                'question_text': 'Test question',
                'user_id': 123456789,
                'mode': 'waiting_answer',
                'created_at': datetime.utcnow()
            }
        }):
            mock_question.is_answered = False
            mock_db.get.return_value = mock_question
            mock_db.commit = AsyncMock()
            
            result = await handle_admin_answer(admin_message)
            
            # Check that the answer was processed
            assert result is True
            assert mock_question.answer == "This is my answer"
            
            admin_message.answer.assert_called()


class TestCriticalCallbackFlow:
    """Tests for critical callback query functionality."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_ask_another_question(
        self, 
        test_callback,
        mock_user_state_manager
    ):
        """Test pressing the 'ask another question' button."""
        from handlers.questions import user_callback_handler
        
        test_callback.data = "ask_another_question"
        test_callback.message.edit_text = AsyncMock()
        
        mock_user_state_manager.allow_new_question.return_value = True
        
        await user_callback_handler(test_callback)
        
        mock_user_state_manager.allow_new_question.assert_called_once()
        test_callback.message.edit_text.assert_called_once()
        test_callback.answer.assert_called_once()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_question_favorite_toggle(
        self,
        test_callback,
        mock_async_session
    ):
        """Test toggling favorite for a question by admin."""
        from handlers.admin import admin_question_callback
        
        # Set admin ID
        admin_id = int(os.getenv('ADMIN_ID', '123456789'))
        test_callback.from_user.id = admin_id
        test_callback.data = "favorite:123"
        test_callback.message.edit_reply_markup = AsyncMock()
        
        mock_question = MagicMock()
        mock_question.is_deleted = False
        mock_question.is_favorite = False
        
        mock_db = mock_async_session.return_value.__aenter__.return_value
        mock_db.get.return_value = mock_question
        mock_db.commit = AsyncMock()
        
        await admin_question_callback(test_callback)
        
        # Check that favorite was toggled
        assert mock_question.is_favorite is True
        test_callback.answer.assert_called()


class TestErrorHandling:
    """Tests for error handling in handlers."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_handler_with_database_error(
        self,
        test_message,
        mock_user_state_manager,
        mock_async_session
    ):
        """Test database error handling - bot should not crash."""
        from handlers.questions import unified_message_handler
        
        test_message.text = "Test question"
        mock_user_state_manager.can_send_question.return_value = True
        
        # Simulate database error
        mock_async_session.side_effect = Exception("Database error")
        
        # Should not raise an exception
        await unified_message_handler(test_message)
        
        # Should send an error message to user
        test_message.answer.assert_called()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_callback_with_invalid_data(self, test_callback):
        """Test handling of invalid callback data."""
        from handlers.questions import user_callback_handler
        
        # Invalid callback data
        test_callback.data = "malformed:data:structure:invalid"
        
        await user_callback_handler(test_callback)
        
        # Should acknowledge callback without crashing
        test_callback.answer.assert_called()


class TestPermissions:
    """Tests for permission and access checks."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_non_admin_cannot_access_admin_commands(self, test_message):
        """Test that non-admin cannot use admin commands."""
        from handlers.admin import admin_command, stats_command, pending_command
        
        # Test different admin commands
        admin_commands = [admin_command, stats_command, pending_command]
        
        for command_func in admin_commands:
            test_message.answer.reset_mock()
            await command_func(test_message)
            
            test_message.answer.assert_called_once()
            call_args = test_message.answer.call_args[0][0]
            assert "администратору" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_has_full_access(self, admin_message, mock_async_session):
        """Test that admin has full access to all functions."""
        from handlers.admin import admin_command
        
        mock_db = mock_async_session.return_value.__aenter__.return_value
        mock_db.scalar.return_value = 0
        
        await admin_command(admin_message)
        
        # Should get admin panel, not access denied
        admin_message.answer.assert_called_once()
        call_args = admin_message.answer.call_args[0][0]
        assert "администратору" not in call_args.lower()
        assert "админ" in call_args.lower() or "панель" in call_args.lower()


class TestMessageFlow:
    """Tests for message flow and user states."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_message_routing(self, admin_message):
        """Test that admin messages are routed correctly."""
        from handlers.questions import unified_message_handler
        
        admin_message.text = "Regular admin message"
        
        # Admin is not in answer mode, and this is not a reply - should be ignored
        with patch('handlers.admin_states.is_admin_in_answer_mode', return_value=False):
            admin_message.reply_to_message = None
            
            await unified_message_handler(admin_message)
            
            # Admin message should be ignored
            admin_message.answer.assert_not_called()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_state_consistency(
        self,
        test_message,
        mock_user_state_manager
    ):
        """Test user state consistency."""
        from handlers.questions import unified_message_handler
        
        test_message.text = "Consistency test"
        
        # User can send a question
        mock_user_state_manager.can_send_question.return_value = True
        
        # Patch other dependencies
        with patch('handlers.questions.async_session') as mock_session, \
             patch('handlers.questions.InputValidator') as mock_validator, \
             patch('handlers.questions.ContentModerator') as mock_moderator:
            
            mock_validator.sanitize_text.return_value = "Consistency test"
            mock_validator.validate_question.return_value = (True, None)
            mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
            mock_moderator.is_likely_spam.return_value = False
            
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            await unified_message_handler(test_message)
            
            # Check that state changed to "question_sent"
            mock_user_state_manager.set_user_state.assert_called_with(
                test_message.from_user.id, 
                mock_user_state_manager.STATE_QUESTION_SENT
            )