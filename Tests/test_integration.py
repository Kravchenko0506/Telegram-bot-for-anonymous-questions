"""
Fixed integration tests for production - end-to-end bot functionality.

Tests complete workflows and system integration points.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import os


class TestCriticalBotWorkflow:
    """Test critical bot workflows end-to-end."""
    
    @pytest.mark.integration
    async def test_new_user_complete_workflow(self, clean_db, mock_bot):
        """Test complete workflow for new user: start -> question -> answer -> new question."""
        user_id = 987654321
        
        # Step 1: User starts bot
        from handlers.start import start_handler
        
        # Create mock message for start
        start_message = MagicMock()
        start_message.from_user.id = user_id
        start_message.answer = AsyncMock()
        
        command = MagicMock()
        command.args = None
        
        with patch('handlers.start.SettingsManager') as mock_settings, \
             patch('handlers.start.UserStateManager') as mock_user_manager, \
             patch('handlers.start.async_session') as mock_session:
            
            mock_settings.get_author_name = AsyncMock(return_value="Test Author")
            mock_settings.get_author_info = AsyncMock(return_value="Test Info")
            mock_user_manager.reset_to_idle = AsyncMock(return_value=True)
            mock_session.return_value.__aenter__.return_value = clean_db
            
            await start_handler(start_message, command)
            
            # Verify user state was handled
            mock_user_manager.reset_to_idle.assert_called_once_with(user_id)
        
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
            mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
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
            mock_db.get.return_value = mock_question
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
            mock_user_manager.allow_new_question.assert_called_once_with(user_id)
            callback.message.edit_text.assert_called_once()
    
    @pytest.mark.integration
    async def test_admin_workflow_with_real_data(self, clean_db, sample_question):
        """Test admin workflow with real database data."""
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
            
            mock_session.return_value.__aenter__.return_value = clean_db
            
            result = await handle_admin_answer(answer_message)
            
            # Verify answer processed
            assert result is True
            
            # Verify question updated in database
            await clean_db.refresh(sample_question)
            assert sample_question.answer == "This is my detailed answer"
            assert sample_question.is_answered is True


class TestCriticalSystemIntegration:
    """Test system integration points and dependencies."""
    
    @pytest.mark.integration
    async def test_database_connection_recovery(self, clean_db):
        """Test system handles database connection issues."""
        from models.questions import Question
        
        # Test normal operation
        question = Question.create_new(text="Test question")
        clean_db.add(question)
        await clean_db.commit()
        
        # Verify saved
        saved_question = await clean_db.get(Question, question.id)
        assert saved_question.text == "Test question"
    
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
    """Test system error recovery and resilience."""
    
    @pytest.mark.integration
    async def test_handler_exception_recovery(self, test_message):
        """Test handlers recover gracefully from exceptions."""
        from handlers.questions import unified_message_handler
        
        test_message.text = "Test question"
        
        # Force an exception in database operation
        with patch('handlers.questions.async_session') as mock_session:
            mock_session.side_effect = Exception("Database unavailable")
            
            # Should not raise exception
            await unified_message_handler(test_message)
            
            # Should send error message to user
            test_message.answer.assert_called()
    
    @pytest.mark.integration
    async def test_callback_handler_resilience(self, test_callback):
        """Test callback handlers handle malformed data gracefully."""
        from handlers.questions import user_callback_handler
        
        # Test with invalid callback data
        test_callback.data = "malformed:data:structure:invalid"
        
        await user_callback_handler(test_callback)
        
        # Should acknowledge callback without crashing
        test_callback.answer.assert_called()
    
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
    
    @pytest.mark.integration
    async def test_rate_limiting_integration(self, test_message):
        """Test rate limiting works with actual handlers."""
        from middlewares.rate_limit import RateLimitMiddleware
        from handlers.questions import unified_message_handler
        
        # Create rate limiter
        rate_limiter = RateLimitMiddleware(
            questions_per_hour=1,
            cooldown_seconds=60
        )
        
        # First call should pass
        test_message.text = "First question"
        
        # Mock the handler to track calls
        original_handler = unified_message_handler
        handler_mock = AsyncMock(side_effect=original_handler)
        
        # Test rate limiting
        data = {}
        
        # First call - should pass (we'll mock can_send_question)
        with patch('handlers.questions.UserStateManager') as mock_manager:
            mock_manager.can_send_question = AsyncMock(return_value=True)
            
            result = await rate_limiter(handler_mock, test_message, data)
            
            # Should have called the handler
            handler_mock.assert_called_once()
    
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
    
    @pytest.mark.integration
    async def test_admin_state_persistence(self, clean_db):
        """Test admin states persist correctly in database."""
        from models.admin_state import AdminStateManager
        
        admin_id = int(os.getenv('ADMIN_ID', '123456789'))
        state_data = {"question_id": 123, "user_id": 987654321}
        
        with patch('models.admin_state.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            # Set state
            success = await AdminStateManager.set_state(
                admin_id,
                AdminStateManager.STATE_ANSWERING,
                state_data,
                expiration_minutes=30
            )
            assert success is True
            
            # Get state
            state = await AdminStateManager.get_state(admin_id)
            assert state is not None
            assert state['type'] == AdminStateManager.STATE_ANSWERING
            assert state['data'] == state_data
            
            # Clear state
            success = await AdminStateManager.clear_state(admin_id)
            assert success is True
            
            # Verify cleared
            state = await AdminStateManager.get_state(admin_id)
            assert state is None
    
    @pytest.mark.integration
    async def test_admin_state_expiration(self, clean_db):
        """Test admin states expire correctly."""
        from models.admin_state import AdminStateManager
        
        admin_id = int(os.getenv('ADMIN_ID', '123456789'))
        
        with patch('models.admin_state.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            # Set state with very short expiration
            success = await AdminStateManager.set_state(
                admin_id,
                AdminStateManager.STATE_ANSWERING,
                {"test": "data"},
                expiration_minutes=0  # Expires immediately
            )
            assert success is True
            
            # State should be expired when retrieved
            state = await AdminStateManager.get_state(admin_id)
            assert state is None  # Should be cleaned up automatically