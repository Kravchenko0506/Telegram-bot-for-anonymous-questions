"""
Critical handler tests for production - bot workflow and user interaction.

Tests essential user flows: start -> question -> admin response -> user receives answer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from aiogram.types import Message, CallbackQuery
from config import ADMIN_ID, MAX_QUESTION_LENGTH

# Import handlers
from handlers import start, admin, questions, admin_states


class TestCriticalStartFlow:
    """Test critical start command functionality."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_regular_user(self, test_message):
        """Test /start command for regular user - entry point to bot."""
        # Mock command object
        command = MagicMock()
        command.args = None
        
        # Mock settings and user state
        with patch('handlers.start.SettingsManager') as mock_settings, \
             patch('handlers.start.UserStateManager') as mock_user_state:
            
            mock_settings.get_author_name.return_value = "Test Author"
            mock_settings.get_author_info.return_value = "Test Info"
            mock_user_state.reset_to_idle.return_value = True
            
            # Call handler
            await start.start_handler(test_message, command)
            
            # Verify welcome message sent
            test_message.answer.assert_called_once()
            call_args = test_message.answer.call_args[0][0]
            assert "Test Author" in call_args
            assert str(MAX_QUESTION_LENGTH) in call_args
            
            # Verify user state reset
            mock_user_state.reset_to_idle.assert_called_once()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_admin_user(self, admin_message):
        """Test /start command for admin - should show admin panel."""
        command = MagicMock()
        command.args = None
        
        await start.start_handler(admin_message, command)
        
        # Verify admin panel shown
        admin_message.answer.assert_called_once()
        call_args = admin_message.answer.call_args[0][0]
        assert "Админ-панель" in call_args
        assert "/stats" in call_args


class TestCriticalQuestionFlow:
    """Test critical question handling - core bot functionality."""
    
    @pytest.mark.handlers
    @pytest.mark.integration
    async def test_user_sends_valid_question(self, test_message, mock_bot):
        """Test complete question submission flow."""
        test_message.text = "How does this bot work?"
        
        with patch('handlers.questions.UserStateManager') as mock_user_state, \
             patch('handlers.questions.async_session') as mock_session, \
             patch('handlers.questions.InputValidator') as mock_validator, \
             patch('handlers.questions.ContentModerator') as mock_moderator:
            
            # Setup mocks for successful flow
            mock_user_state.can_send_question.return_value = True
            mock_user_state.set_user_state.return_value = True
            mock_validator.sanitize_text.return_value = "How does this bot work?"
            mock_validator.validate_question.return_value = (True, None)
            mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
            mock_moderator.is_likely_spam.return_value = False
            
            # Mock database session
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            await questions.unified_message_handler(test_message)
            
            # Verify question processed successfully
            test_message.answer.assert_called()
            call_args = test_message.answer.call_args[0][0]
            assert "отправлен" in call_args.lower()
            
            # Verify admin notification sent
            mock_bot.send_message.assert_called()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_blocked_after_question(self, test_message):
        """Test user blocked from sending text after question."""
        test_message.text = "Another message"
        
        with patch('handlers.questions.UserStateManager') as mock_user_state:
            # User can't send question (already sent one)
            mock_user_state.can_send_question.return_value = False
            
            await questions.unified_message_handler(test_message)
            
            # Should receive blocked message
            test_message.answer.assert_called_once()
            call_args = test_message.answer.call_args[0][0]
            assert "предыдущий вопрос" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_invalid_question_rejected(self, test_message):
        """Test invalid question is rejected with proper error."""
        test_message.text = ""  # Empty question
        
        with patch('handlers.questions.UserStateManager') as mock_user_state, \
             patch('handlers.questions.InputValidator') as mock_validator:
            
            mock_user_state.can_send_question.return_value = True
            mock_validator.sanitize_text.return_value = ""
            mock_validator.validate_question.return_value = (False, "Вопрос не может быть пустым")
            
            await questions.unified_message_handler(test_message)
            
            # Should receive error message
            test_message.answer.assert_called_once()
            call_args = test_message.answer.call_args[0][0]
            assert "пустым" in call_args.lower()


class TestCriticalAdminFlow:
    """Test critical admin functionality - question management."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_access_control(self, test_message):
        """Test that non-admin cannot access admin commands."""
        await admin.admin_command(test_message)
        
        # Should receive access denied message
        test_message.answer.assert_called_once()
        call_args = test_message.answer.call_args[0][0]
        assert "администратору" in call_args.lower()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_command_success(self, admin_message):
        """Test admin command shows admin panel."""
        with patch('handlers.admin.async_session') as mock_session:
            # Mock database response
            mock_session.return_value.__aenter__.return_value.scalar.return_value = 5
            
            await admin.admin_command(admin_message)
            
            admin_message.answer.assert_called_once()
            call_args = admin_message.answer.call_args[0][0]
            assert "Админ-панель" in call_args
    
    @pytest.mark.handlers
    @pytest.mark.integration
    async def test_admin_answer_question_flow(self, admin_message, test_callback):
        """Test admin answering question - complete flow."""
        # Step 1: Admin starts answer mode
        test_callback.data = "answer:123"
        test_callback.message.reply = AsyncMock()
        
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
            
            await admin_states.start_answer_mode(test_callback, 123)
            
            # Verify admin state was set
            assert ADMIN_ID in mock_states
            test_callback.message.reply.assert_called_once()
        
        # Step 2: Admin sends answer
        admin_message.text = "This is my answer"
        
        # Set admin state
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
            
            mock_question = MagicMock()
            mock_question.is_answered = False
            
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.get.return_value = mock_question
            mock_db.commit = AsyncMock()
            
            result = await admin_states.handle_admin_answer(admin_message)
            
            # Verify answer was processed
            assert result is True
            assert mock_question.answer == "This is my answer"
            assert ADMIN_ID not in mock_states  # State cleared
            
            admin_message.answer.assert_called()


class TestCriticalCallbackFlow:
    """Test critical callback query handling."""
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_ask_another_question(self, test_callback):
        """Test user clicking 'ask another question' button."""
        test_callback.data = "ask_another_question"
        test_callback.message.edit_text = AsyncMock()
        
        with patch('handlers.questions.UserStateManager') as mock_user_state:
            mock_user_state.allow_new_question.return_value = True
            
            await questions.user_callback_handler(test_callback)
            
            mock_user_state.allow_new_question.assert_called_once()
            test_callback.message.edit_text.assert_called_once()
            test_callback.answer.assert_called_once()
    
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_question_favorite_toggle(self, test_callback):
        """Test admin toggling question favorite status."""
        test_callback.from_user.id = ADMIN_ID
        test_callback.data = "favorite:123"
        test_callback.message.edit_reply_markup = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_question = MagicMock()
            mock_question.is_deleted = False
            mock_question.is_favorite = False
            
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.get.return_value = mock_question
            mock_db.commit = AsyncMock()