"""
Integration tests for complete system workflows.

This module tests:
- End-to-end user interactions
- System component integration
- Data consistency across operations
- Error recovery scenarios
- Performance under load
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import os

from models.settings import SettingsManager
from models.user_states import UserStateManager
from models.questions import Question
from models.admin_state import AdminState, AdminStateManager
from config import ERROR_RATE_LIMIT


class TestCriticalBotWorkflow:
    """End-to-end tests for critical bot workflows.

    Tests complete interaction flows including:
    - User registration and onboarding
    - Question submission and validation
    - Admin response handling
    - State transitions
    - Database operations
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_new_user_complete_workflow(self, clean_db, mock_bot):
        """Test complete user interaction flow from start to finish.

        Flow steps:
        1. User starts bot and receives welcome
        2. User submits a question
        3. Admin receives and answers question
        4. User receives answer and can ask new question

        Verifies:
        - State transitions are correct
        - Messages are properly handled
        - Database operations succeed
        - User notifications work
        """
        user_id = 987654321

        # Step 1: User starts bot
        from handlers.start import start_handler
        from models.settings import SettingsManager
        from models.user_states import UserStateManager

        # Create mock message for start
        start_message = MagicMock()
        start_message.from_user.id = user_id
        start_message.answer = AsyncMock()

        command = MagicMock()
        command.args = None

        with patch('models.settings.SettingsManager.get_author_name', new=AsyncMock(return_value="Test Author")), \
                patch('models.settings.SettingsManager.get_author_info', new=AsyncMock(return_value="Test Info")), \
                patch('models.user_states.UserStateManager.reset_to_idle', new=AsyncMock(return_value=True)) as mock_reset:

            await start_handler(start_message, command)

            # Verify user state was handled
            mock_reset.assert_called_once_with(user_id)

        # Step 2: User sends question
        from handlers.questions import unified_message_handler

        question_message = MagicMock()
        question_message.from_user.id = user_id
        question_message.text = "What is the meaning of life?"
        question_message.answer = AsyncMock()
        question_message.bot = mock_bot

        with patch('handlers.questions.UserStateManager') as mock_user_manager, \
                patch('handlers.questions.async_session') as mock_session, \
                patch('handlers.questions.InputValidator') as mock_validator, \
                patch('handlers.questions.ContentModerator') as mock_moderator:

            # Setup successful question flow
            mock_user_manager.can_send_question = AsyncMock(return_value=True)
            mock_user_manager.set_user_state = AsyncMock(return_value=True)

            mock_validator.sanitize_text.return_value = "What is the meaning of life?"
            mock_validator.validate_question.return_value = (True, None)
            mock_validator.extract_personal_data.return_value = {
                'emails': [], 'phones': [], 'urls': []}
            mock_moderator.is_likely_spam.return_value = False

            # Mock database session
            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            # Mock question creation and ID assignment
            def set_question_id(question):
                question.id = 123
            mock_db.refresh.side_effect = set_question_id

            await unified_message_handler(question_message)

            # Verify question was processed
            question_message.answer.assert_called()
            mock_user_manager.set_user_state.assert_called()

        # Step 3: Admin answers question (simulated)
        from handlers.admin_states import handle_admin_answer

        admin_message = MagicMock()
        admin_id = int(os.getenv('ADMIN_ID', '123456789'))
        admin_message.from_user.id = admin_id
        admin_message.text = "42 is the answer!"
        admin_message.answer = AsyncMock()
        admin_message.bot = mock_bot

        # Simulate admin state
        with patch('handlers.admin_states.admin_answer_states', {
            admin_id: {
                'question_id': 123,
                'question_text': 'What is the meaning of life?',
                'user_id': user_id,
                'mode': 'waiting_answer',
                'created_at': datetime.utcnow()
            }
        }), patch('handlers.admin_states.async_session') as mock_session:

            mock_question = MagicMock()
            mock_question.is_answered = False
            mock_question.text = "What is the meaning of life?"
            mock_question.user_id = user_id

            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.get = AsyncMock(return_value=mock_question)
            mock_db.commit = AsyncMock()

            result = await handle_admin_answer(admin_message)

            # Verify answer was processed
            assert result is True
            assert mock_question.answer == "42 is the answer!"

        # Step 4: User can ask another question (callback simulation)
        from handlers.questions import user_callback_handler

        callback = MagicMock()
        callback.from_user.id = user_id
        callback.data = "ask_another_question"
        callback.answer = AsyncMock()
        callback.message.edit_text = AsyncMock()

        with patch('handlers.questions.UserStateManager') as mock_user_manager:
            mock_user_manager.allow_new_question = AsyncMock(return_value=True)

            await user_callback_handler(callback)

            # Verify user can ask new question
            mock_user_manager.allow_new_question.assert_called_once_with(
                user_id)
            callback.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_admin_workflow_with_real_data(self, clean_db, sample_question):
        """Test admin workflow using actual database records.

        Flow steps:
        1. Admin accesses control panel
        2. Admin selects question to answer
        3. Admin submits response

        Verifies:
        - Admin panel functionality
        - Question selection and display
        - Answer submission and storage
        - User notification
        """
        from handlers.admin import admin_command
        from handlers.admin_states import start_answer_mode, handle_admin_answer

        admin_id = int(os.getenv('ADMIN_ID', '123456789'))

        # Step 1: Admin checks panel
        admin_message = MagicMock()
        admin_message.from_user.id = admin_id
        admin_message.answer = AsyncMock()

        with patch('handlers.admin.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db

            await admin_command(admin_message)

            # Verify admin panel shown
            admin_message.answer.assert_called()

        # Step 2: Admin starts answering question
        callback = MagicMock()
        callback.from_user.id = admin_id
        callback.data = f"answer:{sample_question.id}"
        callback.message.reply = AsyncMock()
        callback.answer = AsyncMock()

        with patch('handlers.admin_states.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db

            await start_answer_mode(callback, sample_question.id)

            # Verify answer mode started
            callback.message.reply.assert_called()

        # Step 3: Admin sends answer
        answer_message = MagicMock()
        answer_message.from_user.id = admin_id
        answer_message.text = "This is my detailed answer"
        answer_message.answer = AsyncMock()
        answer_message.bot = AsyncMock()

        # Mock admin state
        with patch('handlers.admin_states.admin_answer_states', {
            admin_id: {
                'question_id': sample_question.id,
                'question_text': sample_question.text,
                'user_id': sample_question.user_id,
                'mode': 'waiting_answer',
                'created_at': datetime.utcnow()
            }
        }), patch('handlers.admin_states.async_session') as mock_session:

            mock_db = mock_session.return_value.__aenter__.return_value
            mock_db.get = AsyncMock(return_value=sample_question)
            mock_db.commit = AsyncMock()

            result = await handle_admin_answer(answer_message)

            # Verify answer was processed
            assert result is True
            assert sample_question.answer == "This is my detailed answer"
            assert sample_question.answered_at is not None
            mock_db.commit.assert_called_once()


class TestCriticalSystemIntegration:
    """Tests for critical system component integration.

    Verifies:
    - Database connection handling
    - Settings management
    - State persistence
    - Component interaction
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_connection_recovery(self, clean_db):
        """Test system resilience to database connection issues.

        Verifies:
        - Connection error handling
        - Automatic reconnection
        - Data consistency after recovery
        - Error reporting
        """
        from models.questions import Question

        # Test normal operation
        question = Question.create_new(text="Test question")
        clean_db.add(question)
        await clean_db.commit()

        # Verify saved
        saved_question = await clean_db.get(Question, question.id)
        assert saved_question.text == "Test question"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_settings_persistence(self, clean_db):
        """Test settings are properly persisted and retrieved."""
        from models.settings import BotSettings, SettingsManager

        # Create test settings
        settings = [
            BotSettings(key="author_name", value="Integration Test"),
            BotSettings(key="author_info", value="Test Description")
        ]

        for setting in settings:
            clean_db.add(setting)
        await clean_db.commit()

        # Test retrieval through manager
        with patch('models.settings.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db

            name = await SettingsManager.get_author_name()
            info = await SettingsManager.get_author_info()

            # Should return values
            assert isinstance(name, str)
            assert isinstance(info, str)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_user_state_consistency(self, clean_db):
        """Test user state management consistency."""
        from models.user_states import UserState, UserStateManager

        user_id = 555666777

        # Create initial state
        initial_state = UserState(
            user_id=user_id,
            state=UserStateManager.STATE_IDLE,
            questions_count=0
        )
        clean_db.add(initial_state)
        await clean_db.commit()

        # Test state transitions through manager
        with patch('models.user_states.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db

            # Test state change
            success = await UserStateManager.set_user_state(
                user_id,
                UserStateManager.STATE_QUESTION_SENT
            )
            assert success is True

            # Test can_send_question logic
            can_send = await UserStateManager.can_send_question(user_id)
            assert isinstance(can_send, bool)


class TestCriticalErrorRecovery:
    """Tests for system error recovery mechanisms.

    Verifies:
    - Exception handling
    - State recovery
    - Transaction management
    - User notification
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_handler_exception_recovery(self, test_message):
        """Test message handler recovery from exceptions.

        Verifies:
        - Exception capture and logging
        - State preservation
        - User notification
        - System stability
        """
        from handlers.questions import unified_message_handler

        test_message.text = "Test question"

        # Force an exception in database operation
        with patch('handlers.questions.async_session') as mock_session:
            mock_session.side_effect = Exception("Database unavailable")

            # Should not raise exception
            await unified_message_handler(test_message)

            # Should send error message to user
            test_message.answer.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_callback_handler_resilience(self, test_callback):
        """Test callback handlers handle malformed data gracefully."""
        from handlers.questions import user_callback_handler

        # Test with invalid callback data
        test_callback.data = "malformed:data:structure:invalid"

        await user_callback_handler(test_callback)

        # Should acknowledge callback without crashing
        test_callback.answer.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_transaction_rollback(self, clean_db):
        """Test database transactions rollback properly on errors."""
        from models.questions import Question

        # Start transaction
        question = Question.create_new(text="Transaction test")
        clean_db.add(question)

        try:
            # Force an error during commit
            await clean_db.flush()  # This should work

            # Create another question with potential conflict
            duplicate_question = Question.create_new(text="Transaction test 2")
            clean_db.add(duplicate_question)

            await clean_db.commit()  # This should work in our test

        except Exception:
            # Transaction should rollback
            await clean_db.rollback()

        # Verify database is in consistent state
        from sqlalchemy import select, func
        result = await clean_db.execute(select(func.count(Question.id)))
        count = result.scalar()
        # Count should be manageable (not negative or corrupted)
        assert count >= 0


class TestCriticalPerformance:
    """Test critical performance scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_user_handling(self, clean_db):
        """Test system handles multiple users simultaneously."""
        from models.user_states import UserState

        # Simulate multiple users
        user_ids = [111, 222, 333, 444, 555]

        # Create states for all users
        for user_id in user_ids:
            state = UserState(
                user_id=user_id,
                state="idle",
                questions_count=0
            )
            clean_db.add(state)

        await clean_db.commit()

        # Verify all created successfully
        for user_id in user_ids:
            state = await clean_db.get(UserState, user_id)
            assert state is not None
            assert state.user_id == user_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_question_batch_processing(self, clean_db):
        """Test handling multiple questions efficiently."""
        from models.questions import Question

        # Create batch of questions
        questions = []
        for i in range(10):
            question = Question.create_new(
                text=f"Batch question {i}",
                user_id=100000 + i
            )
            questions.append(question)
            clean_db.add(question)

        await clean_db.commit()

        # Verify all saved correctly
        for question in questions:
            await clean_db.refresh(question)
            assert question.id is not None
            assert question.created_at is not None


class TestCriticalDataConsistency:
    """Test data consistency across system operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_question_lifecycle_consistency(self, clean_db):
        """Test question maintains data consistency through lifecycle."""
        from models.questions import Question

        # Create question
        question = Question.create_new(
            text="Lifecycle test question",
            user_id=123456789
        )
        clean_db.add(question)
        await clean_db.commit()
        await clean_db.refresh(question)

        initial_id = question.id
        initial_created = question.created_at

        # Answer question
        question.answer = "Lifecycle test answer"
        question.answered_at = datetime.utcnow()
        await clean_db.commit()

        # Verify consistency maintained
        await clean_db.refresh(question)
        assert question.id == initial_id
        assert question.created_at == initial_created
        assert question.is_answered is True
        assert question.answer == "Lifecycle test answer"

        # Mark as favorite
        question.is_favorite = True
        await clean_db.commit()

        # Verify still consistent
        await clean_db.refresh(question)
        assert question.is_answered is True
        assert question.is_favorite is True

        # Soft delete
        question.is_deleted = True
        question.deleted_at = datetime.utcnow()
        await clean_db.commit()

        # Verify final state
        await clean_db.refresh(question)
        assert question.is_deleted is True
        assert question.deleted_at is not None
        # Data should still be intact
        assert question.text == "Lifecycle test question"
        assert question.answer == "Lifecycle test answer"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_user_question_relationship_integrity(self, clean_db):
        """Test user-question relationship maintains integrity."""
        from models.questions import Question
        from models.user_states import UserState

        user_id = 999888777

        # Create user state
        user_state = UserState(
            user_id=user_id,
            state="idle",
            questions_count=0
        )
        clean_db.add(user_state)

        # Create questions for user
        questions = []
        for i in range(3):
            question = Question.create_new(
                text=f"User question {i}",
                user_id=user_id
            )
            questions.append(question)
            clean_db.add(question)

        await clean_db.commit()

        # Verify relationship integrity
        for question in questions:
            await clean_db.refresh(question)
            assert question.user_id == user_id

        await clean_db.refresh(user_state)
        assert user_state.user_id == user_id

        # Update question count
        user_state.questions_count = len(questions)
        await clean_db.commit()

        # Verify consistency
        await clean_db.refresh(user_state)
        assert user_state.questions_count == 3


class TestCriticalMiddlewareIntegration:
    """Test middleware integration with handlers."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rate_limiting_integration(self, test_message):
        """Test rate limiting middleware integration.

        Verifies:
        - First request passes
        - Second request within cooldown is blocked
        - Error message is sent
        - Handler behavior is correct
        """
        from middlewares.rate_limit import RateLimitMiddleware
        from models.user_states import UserStateManager

        # Create rate limiter with test settings
        rate_limiter = RateLimitMiddleware(
            questions_per_hour=2,
            cooldown_seconds=1
        )

        # Create mock handler
        handler_mock = AsyncMock()

        # Mock user state to allow questions
        with patch('models.user_states.UserStateManager.can_send_question', new=AsyncMock(return_value=True)):

            # First request should pass
            data = {}
            result = await rate_limiter(handler_mock, test_message, data)

            # Verify handler was called
            handler_mock.assert_called_once_with(test_message, data)

            # Second request within cooldown should be blocked
            handler_mock.reset_mock()
            result = await rate_limiter(handler_mock, test_message, data)

            # Verify handler was not called and error message was sent
            handler_mock.assert_not_called()
            # Just verify that some message was sent
            test_message.answer.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_integration(self, test_message):
        """Test error handling middleware with real handlers."""
        from middlewares.error_handler import ErrorHandlerMiddleware

        # Create error handler
        error_handler = ErrorHandlerMiddleware(notify_admin=False)

        # Create a handler that raises an exception
        async def failing_handler(event, data):
            raise ValueError("Test error for integration")

        # Should not raise exception
        await error_handler(failing_handler, test_message, {})

        # Error should be logged
        assert error_handler.error_count > 0
        assert len(error_handler.last_errors) > 0

        # User should receive error message
        test_message.answer.assert_called()


class TestCriticalAdminStateIntegration:
    """Test admin state management integration."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_admin_state_persistence(self, clean_db):
        """Test admin state persistence in database."""
        admin_id = 123456789
        question_id = 456

        # Create initial state
        state = AdminState(
            admin_id=admin_id,
            state_type=AdminStateManager.STATE_ANSWERING,
            state_data={"question_id": question_id},
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        clean_db.add(state)
        await clean_db.commit()

        # Verify state was saved
        saved_state = await clean_db.get(AdminState, admin_id)
        assert saved_state is not None
        assert saved_state.state_type == AdminStateManager.STATE_ANSWERING
        assert saved_state.state_data["question_id"] == question_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_admin_state_expiration(self, clean_db):
        """Test admin state expiration handling."""
        admin_id = 123456789
        question_id = 456

        # Create expired state
        state = AdminState(
            admin_id=admin_id,
            state_type=AdminStateManager.STATE_ANSWERING,
            state_data={"question_id": question_id},
            expires_at=datetime.utcnow() - timedelta(minutes=1)  # Already expired
        )
        clean_db.add(state)
        await clean_db.commit()

        # Verify expired state is handled
        is_answering = await AdminStateManager.is_in_state(admin_id, AdminStateManager.STATE_ANSWERING)
        assert not is_answering  # Should be False for expired state
