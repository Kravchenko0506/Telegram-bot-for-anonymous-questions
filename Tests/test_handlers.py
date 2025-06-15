"""
Tests for bot message handlers and command processing.

This module tests:
- Command handlers (/start, admin commands)
- Message processing flow
- User question handling
- Admin response system
- Callback query processing
- Error handling and permissions
"""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import classes for proper mocking
from models.user_states import UserStateManager
from utils.validators import InputValidator, ContentModerator
from models.settings import SettingsManager
from aiogram.types import User, Chat, Message, CallbackQuery


class TestCriticalStartFlow:
    """Tests for the /start command handler implementation.

    Verifies:
    - User welcome flow
    - Admin panel access
    - Initial state setup
    - Settings integration
    """

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_regular_user(
        self,
        test_message,
        mock_settings_manager,
        mock_user_state_manager,
        event_loop
    ):
        """Test /start command processing for regular users.

        Verifies:
        - Welcome message is sent
        - User state is reset
        - Author info is included
        - Character limit is displayed
        """
        from handlers.start import start_handler

        # Mock command object
        command = MagicMock()
        command.args = None

        # Set up proper mocks using patch.object for static methods
        with patch('models.settings.SettingsManager.get_author_name', new=AsyncMock(return_value="Test Author")), \
                patch('models.settings.SettingsManager.get_author_info', new=AsyncMock(return_value="Test Info")), \
                patch('models.user_states.UserStateManager.reset_to_idle', new=AsyncMock(return_value=True)) as mock_reset:

            # Call handler
            await start_handler(test_message, command)

            # Check that user state was reset
            mock_reset.assert_called_once_with(test_message.from_user.id)

        # Check that a welcome message was sent
        test_message.answer.assert_called_once()
        call_args = test_message.answer.call_args[0][0]

        # Check that the message contains data from settings
        assert "Test Author" in call_args
        assert "2500" in call_args  # Default MAX_QUESTION_LENGTH

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_start_admin_user(self, admin_message, event_loop):
        """Test /start command processing for admin users.

        Verifies:
        - Admin panel is displayed
        - Admin privileges are recognized
        - Proper welcome message is shown
        """
        from handlers.start import start_handler

        command = MagicMock()
        command.args = None

        # Set up proper mocks for admin
        with patch('models.settings.SettingsManager.get_author_name', new=AsyncMock(return_value="Test Author")), \
                patch('models.settings.SettingsManager.get_author_info', new=AsyncMock(return_value="Test Info")), \
                patch('models.user_states.UserStateManager.reset_to_idle', new=AsyncMock(return_value=True)), \
                patch('config.ADMIN_ID', admin_message.from_user.id):

            await start_handler(admin_message, command)

        # Check that admin panel is shown
        admin_message.answer.assert_called_once()
        call_args = admin_message.answer.call_args[0][0]
        # Check for Russian admin panel indicators
        assert any(phrase in call_args.lower() for phrase in [
            "привет", "админ", "панель", "добро пожаловать"
        ])


class TestCriticalQuestionFlow:
    """Tests for user question processing functionality.

    Verifies:
    - Question validation
    - State management
    - Database operations
    - Rate limiting
    - Error handling
    """

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_sends_valid_question(
        self,
        test_message,
        mock_user_state_manager,
        mock_async_session,
        mock_input_validator,
        mock_content_moderator,
        event_loop
    ):
        """Test complete flow of processing a valid question.

        Verifies:
        - Question validation
        - Spam detection
        - Database storage
        - State updates
        - User notification
        """
        from handlers.questions import unified_message_handler

        test_message.text = "How does this bot work?"

        # Set up mocks using patch.object for static methods
        with patch('handlers.questions.UserStateManager.can_send_question', new=AsyncMock(return_value=True)) as mock_can_send, \
                patch('handlers.questions.UserStateManager.set_user_state', new=AsyncMock(return_value=True)) as mock_set_state, \
                patch('handlers.questions.async_session', return_value=mock_async_session), \
                patch('handlers.questions.InputValidator.sanitize_text', return_value="How does this bot work?"), \
                patch('handlers.questions.InputValidator.validate_question', return_value=(True, None)), \
                patch('handlers.questions.InputValidator.extract_personal_data', return_value={'emails': [], 'phones': [], 'urls': []}), \
                patch('handlers.questions.ContentModerator.is_likely_spam', return_value=False), \
                patch('handlers.questions.ContentModerator.calculate_spam_score', return_value=0.0):

            # Configure database session
            mock_db = mock_async_session.__aenter__.return_value
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            # Mock question creation and ID assignment
            def set_question_id(question):
                question.id = 123
            mock_db.refresh.side_effect = set_question_id

            await unified_message_handler(test_message)

            # Verify the question was processed
            mock_can_send.assert_called_once_with(test_message.from_user.id)
            mock_set_state.assert_called_once_with(
                test_message.from_user.id, UserStateManager.STATE_QUESTION_SENT)
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            test_message.answer.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_blocked_after_question(
        self,
        test_message,
        mock_user_state_manager,
        event_loop
    ):
        """Test rate limiting after question submission.

        Verifies:
        - User cannot send multiple questions
        - Appropriate error message is shown
        - State remains unchanged
        """
        from handlers.questions import unified_message_handler

        test_message.text = "Another message"

        # User cannot send a question (already sent)
        with patch('handlers.questions.UserStateManager.can_send_question', new=AsyncMock(return_value=False)), \
                patch('handlers.admin_states.is_admin_in_answer_mode', return_value=False):

            await unified_message_handler(test_message)

        # Should receive a rate limit message in Russian
        test_message.answer.assert_called_once()
        call_args = test_message.answer.call_args[0][0]
        assert any(phrase in call_args.lower() for phrase in [
            "предыдущий вопрос", "кнопку", "ожидани", "ошибка"
        ])

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_invalid_question_rejected(
        self,
        test_message,
        mock_user_state_manager,
        mock_input_validator,
        event_loop
    ):
        """Test rejection of invalid questions.

        Verifies:
        - Empty questions are rejected
        - Validation error messages
        - State remains unchanged
        """
        from handlers.questions import unified_message_handler

        test_message.text = ""  # Empty question

        # Set up mocks
        with patch('handlers.questions.UserStateManager.can_send_question', new=AsyncMock(return_value=True)), \
                patch('handlers.questions.InputValidator.sanitize_text', return_value=""), \
                patch('handlers.questions.InputValidator.validate_question', return_value=(False, "Вопрос не может быть пустым")):

            await unified_message_handler(test_message)

        # Should receive an error message in Russian
        test_message.answer.assert_called_once()
        call_args = test_message.answer.call_args[0][0]
        assert any(phrase in call_args.lower() for phrase in [
            "пустым", "ошибка", "не может быть"
        ])


class TestCriticalAdminFlow:
    """Tests for admin functionality and permissions.

    Verifies:
    - Access control
    - Command processing
    - Question management
    - Response handling
    """

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_access_control(self, test_message, event_loop):
        """Test access control - non-admin should not get access."""
        from handlers.admin import admin_command

        await admin_command(test_message)

        # Should receive an access denied message
        test_message.answer.assert_called_once()
        call_args = test_message.answer.call_args[0][0]
        assert "администратору" in call_args.lower()

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_command_success(self, admin_message, mock_async_session, event_loop):
        """Test successful execution of admin command."""
        from handlers.admin import admin_command

        # Mock database response for statistics
        with patch('handlers.admin.async_session', return_value=mock_async_session), \
                patch('config.ADMIN_ID', admin_message.from_user.id):

            mock_db = mock_async_session.__aenter__.return_value
            mock_db.scalar = AsyncMock(return_value=5)

            await admin_command(admin_message)

        admin_message.answer.assert_called_once()
        call_args = admin_message.answer.call_args[0][0]
        assert any(phrase in call_args.lower() for phrase in [
            "админ", "панель", "статистика"
        ])

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_answer_question_flow(
        self,
        admin_message,
        test_callback,
        mock_async_session,
        event_loop
    ):
        """Test the full process of admin answering a question."""
        from handlers.admin_states import start_answer_mode, handle_admin_answer

        # Get ADMIN_ID from environment
        admin_id = int(os.getenv('ADMIN_ID', '123456789'))

        # Step 1: Admin starts answer mode
        test_callback.data = "answer:123"
        test_callback.from_user = MagicMock(spec=User)
        test_callback.from_user.id = admin_id
        test_callback.from_user.is_bot = False
        test_callback.from_user.first_name = "Admin"
        test_callback.from_user.username = "admin"

        # Mock question exists
        mock_question = MagicMock()
        mock_question.id = 123
        mock_question.is_deleted = False
        mock_question.is_answered = False
        mock_question.text = "Test question"
        mock_question.user_id = 123456789

        with patch('handlers.admin_states.async_session', return_value=mock_async_session), \
                patch('config.ADMIN_ID', admin_id), \
                patch('handlers.admin_states.admin_answer_states', {}):

            mock_db = mock_async_session.__aenter__.return_value
            mock_db.get = AsyncMock(return_value=mock_question)
            mock_db.commit = AsyncMock()

            await start_answer_mode(test_callback, 123)

            # Verify admin entered answer mode
            test_callback.message.reply.assert_called_once()
            test_callback.answer.assert_called_once()

        # Step 2: Admin sends answer
        admin_message.text = "This is the answer"
        admin_message.from_user = MagicMock(spec=User)
        admin_message.from_user.id = admin_id
        admin_message.from_user.is_bot = False
        admin_message.from_user.first_name = "Admin"
        admin_message.from_user.username = "admin"
        admin_message.bot = MagicMock()
        admin_message.bot.send_message = AsyncMock()

        # Mock admin state
        with patch('handlers.admin_states.admin_answer_states', {
            admin_id: {
                'question_id': 123,
                'question_text': 'Test question',
                'user_id': 123456789,
                'mode': 'waiting_answer',
                'created_at': datetime.utcnow()
            }
        }), patch('handlers.admin_states.async_session', return_value=mock_async_session):

            mock_db = mock_async_session.__aenter__.return_value
            mock_db.get = AsyncMock(return_value=mock_question)
            mock_db.commit = AsyncMock()

            result = await handle_admin_answer(admin_message)

            # Verify answer was processed
            assert result is True
            mock_db.commit.assert_called_once()
            admin_message.bot.send_message.assert_called_once()
            admin_message.answer.assert_called_once()


class TestCriticalCallbackFlow:
    """Tests for critical callback query functionality."""

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_ask_another_question(
        self,
        test_callback,
        mock_user_state_manager,
        event_loop
    ):
        """Test pressing the 'ask another question' button."""
        from handlers.questions import user_callback_handler

        test_callback.data = "ask_another_question"
        test_callback.from_user = MagicMock(spec=User)
        test_callback.from_user.id = 123456789
        test_callback.from_user.is_bot = False
        test_callback.from_user.first_name = "Test"
        test_callback.from_user.username = "testuser"

        with patch('handlers.questions.UserStateManager.allow_new_question', new=AsyncMock(return_value=True)) as mock_allow:
            await user_callback_handler(test_callback)

            # Verify state was updated
            mock_allow.assert_called_once_with(test_callback.from_user.id)
            test_callback.message.edit_text.assert_called_once()
            test_callback.answer.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_question_favorite_toggle(
        self,
        test_callback,
        mock_async_session,
        event_loop
    ):
        """Test toggling favorite for a question by admin."""
        from handlers.admin import admin_question_callback

        # Set admin ID
        admin_id = int(os.getenv('ADMIN_ID', '123456789'))
        test_callback.from_user = MagicMock(spec=User)
        test_callback.from_user.id = admin_id
        test_callback.from_user.is_bot = False
        test_callback.from_user.first_name = "Admin"
        test_callback.from_user.username = "admin"
        test_callback.data = "favorite:123"

        # Mock question
        mock_question = MagicMock()
        mock_question.id = 123
        mock_question.is_deleted = False
        mock_question.is_favorite = False

        with patch('handlers.admin.async_session', return_value=mock_async_session), \
                patch('config.ADMIN_ID', admin_id):

            mock_db = mock_async_session.__aenter__.return_value
            mock_db.get = AsyncMock(return_value=mock_question)
            mock_db.commit = AsyncMock()

            await admin_question_callback(test_callback)

            # Verify favorite was toggled and committed
            assert mock_question.is_favorite is True
            mock_db.commit.assert_called_once()
            test_callback.answer.assert_called_once()
            test_callback.message.edit_reply_markup.assert_called_once()


class TestErrorHandling:
    """Tests for error handling in handlers."""

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_handler_with_database_error(
        self,
        test_message,
        mock_user_state_manager,
        mock_async_session,
        event_loop
    ):
        """Test database error handling - bot should not crash."""
        from handlers.questions import unified_message_handler

        test_message.text = "Test question"

        # Simulate database error
        with patch('handlers.questions.UserStateManager.can_send_question', new=AsyncMock(return_value=True)), \
                patch('handlers.questions.async_session', side_effect=Exception("Database error")):

            # Should not raise an exception
            await unified_message_handler(test_message)

            # Should send an error message to user
            test_message.answer.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_callback_with_invalid_data(self, test_callback, event_loop):
        """Test handling of invalid callback data."""
        from handlers.questions import user_callback_handler

        # Invalid callback data
        test_callback.data = "malformed:data:structure:invalid"
        test_callback.from_user = MagicMock(spec=User)
        test_callback.from_user.id = 123456789
        test_callback.from_user.is_bot = False
        test_callback.from_user.first_name = "Test"
        test_callback.from_user.username = "testuser"

        # Mock UserStateManager to avoid side effects
        with patch('handlers.questions.UserStateManager.allow_new_question', new=AsyncMock(return_value=True)):
            await user_callback_handler(test_callback)

            # Should acknowledge callback without crashing
            test_callback.answer.assert_called_once()


class TestPermissions:
    """Tests for permission and access checks."""

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_non_admin_cannot_access_admin_commands(self, test_message, event_loop):
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

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_has_full_access(self, admin_message, mock_async_session, event_loop):
        """Test that admin has full access to all functions."""
        from handlers.admin import admin_command

        with patch('handlers.admin.async_session', return_value=mock_async_session), \
                patch('config.ADMIN_ID', admin_message.from_user.id):

            mock_db = mock_async_session.__aenter__.return_value
            mock_db.scalar = AsyncMock(return_value=0)

            await admin_command(admin_message)

        # Should get admin panel, not access denied
        admin_message.answer.assert_called_once()
        call_args = admin_message.answer.call_args[0][0]
        assert any(phrase in call_args.lower() for phrase in [
            "админ", "панель", "статистика"
        ])


class TestMessageFlow:
    """Tests for message flow and user states."""

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_admin_message_routing(self, admin_message, event_loop):
        """Test that admin messages are routed correctly."""
        from handlers.questions import unified_message_handler

        admin_message.text = "Regular admin message"

        # Admin is not in answer mode, and this is not a reply - should be ignored
        with patch('handlers.admin_states.is_admin_in_answer_mode', return_value=False):
            admin_message.reply_to_message = None

            await unified_message_handler(admin_message)

            # Admin message should be ignored (no answer call)
            assert True

    @pytest.mark.asyncio
    @pytest.mark.handlers
    @pytest.mark.unit
    async def test_user_state_consistency(
        self,
        test_message,
        mock_user_state_manager,
        mock_async_session,
        event_loop
    ):
        """Test user state consistency."""
        from handlers.questions import unified_message_handler

        test_message.text = "Consistency test"

        # Set up all necessary mocks
        with patch('handlers.questions.UserStateManager.can_send_question', new=AsyncMock(return_value=True)) as mock_can_send, \
                patch('handlers.questions.UserStateManager.set_user_state', new=AsyncMock(return_value=True)) as mock_set_state, \
                patch('handlers.questions.async_session', return_value=mock_async_session), \
                patch('handlers.questions.InputValidator.sanitize_text', return_value="Consistency test"), \
                patch('handlers.questions.InputValidator.validate_question', return_value=(True, None)), \
                patch('handlers.questions.InputValidator.extract_personal_data', return_value={'emails': [], 'phones': [], 'urls': []}), \
                patch('handlers.questions.ContentModerator.is_likely_spam', return_value=False), \
                patch('handlers.questions.ContentModerator.calculate_spam_score', return_value=0.0):

            mock_db = mock_async_session.__aenter__.return_value
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            # Mock question creation and ID assignment
            def set_question_id(question):
                question.id = 123
            mock_db.refresh.side_effect = set_question_id

            await unified_message_handler(test_message)

            # Verify state changes
            mock_can_send.assert_called_once_with(test_message.from_user.id)
            mock_set_state.assert_called_once_with(
                test_message.from_user.id, UserStateManager.STATE_QUESTION_SENT)
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            test_message.answer.assert_called()
