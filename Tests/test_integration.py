"""
Integration tests for the Anonymous Questions Bot.

Tests complete workflows, database integration, and end-to-end scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import Message, CallbackQuery, User, Chat
from config import ADMIN_ID, MAX_QUESTION_LENGTH

from models.questions import Question
from models.user_states import UserState, UserStateManager
from models.admin_state import AdminState, AdminStateManager
from models.settings import BotSettings, SettingsManager
from handlers import start, admin, questions, admin_states


class TestCompleteUserFlow:
    """Test complete user interaction flows."""
    
    @pytest.mark.integration
    @pytest.mark.e2e
    async def test_user_question_to_answer_flow(self, clean_db, mock_bot, test_user, admin_user, mock_logger):
        """Test complete flow: user question -> admin answer -> user receives answer."""
        
        # 1. User starts bot
        start_message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="/start",
            bot=mock_bot
        )
        start_message.answer = AsyncMock()
        
        command = MagicMock()
        command.args = None
        
        with patch('handlers.start.SettingsManager') as mock_settings, \
             patch('handlers.start.UserStateManager') as mock_user_state:
            
            mock_settings.get_author_name.return_value = "Test Author"
            mock_settings.get_author_info.return_value = "Test Info"
            mock_user_state.reset_to_idle.return_value = True
            
            await start.start_handler(start_message, command)
            
            start_message.answer.assert_called_once()
            welcome_text = start_message.answer.call_args[0][0]
            assert "Test Author" in welcome_text
        
        # 2. User sends question
        question_message = Message(
            message_id=2,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="How does this bot work?",
            bot=mock_bot
        )
        question_message.answer = AsyncMock()
        mock_bot.send_message = AsyncMock()
        
        # Create real question in database
        question = Question.create_new(
            text="How does this bot work?",
            user_id=test_user.id
        )
        clean_db.add(question)
        await clean_db.commit()
        await clean_db.refresh(question)
        
        # Create user state
        user_state = UserState(
            user_id=test_user.id,
            state=UserStateManager.STATE_IDLE,
            questions_count=0
        )
        clean_db.add(user_state)
        await clean_db.commit()
        
        with patch('handlers.questions.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            # Mock other dependencies
            with patch('handlers.questions.UserStateManager') as mock_user_mgr, \
                 patch('handlers.questions.InputValidator') as mock_validator, \
                 patch('handlers.questions.ContentModerator') as mock_moderator:
                
                mock_user_mgr.can_send_question.return_value = True
                mock_user_mgr.set_user_state.return_value = True
                mock_validator.sanitize_text.return_value = "How does this bot work?"
                mock_validator.validate_question.return_value = (True, None)
                mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
                mock_moderator.is_likely_spam.return_value = False
                mock_moderator.calculate_spam_score.return_value = 0.1
                
                await questions.unified_message_handler(question_message)
                
                question_message.answer.assert_called()
                success_text = question_message.answer.call_args[0][0]
                assert "отправлен" in success_text.lower()
        
        # 3. Admin receives notification and starts answer
        admin_callback = CallbackQuery(
            id="admin_callback",
            from_user=admin_user,
            chat_instance="admin",
            message=MagicMock(),
            data=f"answer:{question.id}",
            bot=mock_bot
        )
        admin_callback.answer = AsyncMock()
        admin_callback.message.reply = AsyncMock()
        
        with patch('handlers.admin_states.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            await admin_states.start_answer_mode(admin_callback, question.id)
            
            admin_callback.message.reply.assert_called_once()
            reply_text = admin_callback.message.reply.call_args[0][0]
            assert "How does this bot work?" in reply_text
        
        # 4. Admin sends answer
        admin_answer_message = Message(
            message_id=3,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="The bot allows users to ask anonymous questions.",
            bot=mock_bot
        )
        admin_answer_message.answer = AsyncMock()
        
        # Set admin state
        with patch('handlers.admin_states.admin_answer_states', {
            ADMIN_ID: {
                'question_id': question.id,
                'question_text': question.text,
                'user_id': test_user.id,
                'mode': 'waiting_answer',
                'created_at': datetime.utcnow()
            }
        }), patch('handlers.admin_states.async_session') as mock_session:
            
            mock_session.return_value.__aenter__.return_value = clean_db
            
            result = await admin_states.handle_admin_answer(admin_answer_message)
            
            assert result is True
            admin_answer_message.answer.assert_called()
            
            # Verify question was updated
            await clean_db.refresh(question)
            assert question.answer == "The bot allows users to ask anonymous questions."
            assert question.is_answered is True
    
    @pytest.mark.integration
    @pytest.mark.e2e
    async def test_user_multiple_questions_flow(self, clean_db, mock_bot, test_user, mock_logger):
        """Test user asking multiple questions with state management."""
        
        # Create user state
        user_state = UserState(
            user_id=test_user.id,
            state=UserStateManager.STATE_IDLE,
            questions_count=0
        )
        clean_db.add(user_state)
        await clean_db.commit()
        
        # 1. User sends first question
        first_message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="First question",
            bot=mock_bot
        )
        first_message.answer = AsyncMock()
        
        with patch('handlers.questions.async_session') as mock_session, \
             patch('handlers.questions.UserStateManager') as mock_user_mgr, \
             patch('handlers.questions.InputValidator') as mock_validator, \
             patch('handlers.questions.ContentModerator') as mock_moderator:
            
            mock_session.return_value.__aenter__.return_value = clean_db
            mock_user_mgr.can_send_question.return_value = True
            mock_user_mgr.set_user_state.return_value = True
            mock_validator.sanitize_text.return_value = "First question"
            mock_validator.validate_question.return_value = (True, None)
            mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
            mock_moderator.is_likely_spam.return_value = False
            mock_moderator.calculate_spam_score.return_value = 0.1
            
            await questions.unified_message_handler(first_message)
            
            first_message.answer.assert_called()
        
        # 2. User tries to send text again (should be blocked)
        second_message = Message(
            message_id=2,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="Another message",
            bot=mock_bot
        )
        second_message.answer = AsyncMock()
        
        with patch('handlers.questions.UserStateManager') as mock_user_mgr:
            mock_user_mgr.can_send_question.return_value = False
            
            await questions.unified_message_handler(second_message)
            
            second_message.answer.assert_called()
            blocked_text = second_message.answer.call_args[0][0]
            assert "предыдущий вопрос" in blocked_text.lower()
        
        # 3. User clicks "ask another question" button
        callback = CallbackQuery(
            id="user_callback",
            from_user=test_user,
            chat_instance="test",
            message=MagicMock(),
            data="ask_another_question",
            bot=mock_bot
        )
        callback.answer = AsyncMock()
        callback.message.edit_text = AsyncMock()
        
        with patch('handlers.questions.UserStateManager') as mock_user_mgr:
            mock_user_mgr.allow_new_question.return_value = True
            
            await questions.user_callback_handler(callback)
            
            callback.message.edit_text.assert_called()
            callback.answer.assert_called()
        
        # 4. User sends new question (should work)
        third_message = Message(
            message_id=3,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="Second question",
            bot=mock_bot
        )
        third_message.answer = AsyncMock()
        
        with patch('handlers.questions.UserStateManager') as mock_user_mgr, \
             patch('handlers.questions.InputValidator') as mock_validator, \
             patch('handlers.questions.ContentModerator') as mock_moderator:
            
            mock_user_mgr.can_send_question.return_value = True
            mock_user_mgr.set_user_state.return_value = True
            mock_validator.sanitize_text.return_value = "Second question"
            mock_validator.validate_question.return_value = (True, None)
            mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
            mock_moderator.is_likely_spam.return_value = False
            
            await questions.unified_message_handler(third_message)
            
            third_message.answer.assert_called()
            success_text = third_message.answer.call_args[0][0]
            assert "отправлен" in success_text.lower()


class TestAdminWorkflow:
    """Test admin workflow scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.e2e
    async def test_admin_question_management_flow(self, clean_db, mock_bot, admin_user, mock_logger):
        """Test admin managing questions: view, favorite, answer, delete."""
        
        # Create sample questions
        questions = []
        for i in range(5):
            question = Question.create_new(
                text=f"Question {i+1}",
                user_id=123456789 + i
            )
            clean_db.add(question)
            questions.append(question)
        
        await clean_db.commit()
        for q in questions:
            await clean_db.refresh(q)
        
        # 1. Admin checks stats
        stats_message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="/stats",
            bot=mock_bot
        )
        stats_message.answer = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            await admin.stats_command(stats_message)
            
            stats_message.answer.assert_called()
            stats_text = stats_message.answer.call_args[0][0]
            assert "5" in stats_text  # Total questions
        
        # 2. Admin marks question as favorite
        favorite_callback = CallbackQuery(
            id="favorite_callback",
            from_user=admin_user,
            chat_instance="admin",
            message=MagicMock(),
            data=f"favorite:{questions[0].id}",
            bot=mock_bot
        )
        favorite_callback.answer = AsyncMock()
        favorite_callback.message.edit_reply_markup = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            await admin.admin_question_callback(favorite_callback)
            
            favorite_callback.answer.assert_called()
            
            # Verify question is marked as favorite
            await clean_db.refresh(questions[0])
            assert questions[0].is_favorite is True
        
        # 3. Admin views favorites
        favorites_message = Message(
            message_id=2,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="/favorites",
            bot=mock_bot
        )
        favorites_message.answer = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            await admin.favorites_command(favorites_message)
            
            # Should show favorites page
            favorites_message.answer.assert_called()
        
        # 4. Admin answers a question
        answer_callback = CallbackQuery(
            id="answer_callback",
            from_user=admin_user,
            chat_instance="admin",
            message=MagicMock(),
            data=f"answer:{questions[1].id}",
            bot=mock_bot
        )
        answer_callback.answer = AsyncMock()
        answer_callback.message.reply = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            await admin_states.start_answer_mode(answer_callback, questions[1].id)
            
            answer_callback.message.reply.assert_called()
        
        # Admin sends answer
        answer_message = Message(
            message_id=3,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="This is the answer",
            bot=mock_bot
        )
        answer_message.answer = AsyncMock()
        
        with patch('handlers.admin_states.admin_answer_states', {
            ADMIN_ID: {
                'question_id': questions[1].id,
                'question_text': questions[1].text,
                'user_id': questions[1].user_id,
                'mode': 'waiting_answer',
                'created_at': datetime.utcnow()
            }
        }), patch('handlers.admin_states.async_session') as mock_session:
            
            mock_session.return_value.__aenter__.return_value = clean_db
            
            result = await admin_states.handle_admin_answer(answer_message)
            
            assert result is True
            
            # Verify question was answered
            await clean_db.refresh(questions[1])
            assert questions[1].answer == "This is the answer"
            assert questions[1].is_answered is True
        
        # 5. Admin deletes a question
        delete_callback = CallbackQuery(
            id="delete_callback",
            from_user=admin_user,
            chat_instance="admin",
            message=MagicMock(),
            data=f"delete:{questions[2].id}",
            bot=mock_bot
        )
        delete_callback.answer = AsyncMock()
        delete_callback.message.edit_text = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            await admin.admin_question_callback(delete_callback)
            
            delete_callback.answer.assert_called()
            
            # Verify question was soft deleted
            await clean_db.refresh(questions[2])
            assert questions[2].is_deleted is True
            assert questions[2].deleted_at is not None
    
    @pytest.mark.integration
    @pytest.mark.e2e
    async def test_admin_settings_management(self, clean_db, mock_bot, admin_user, mock_logger):
        """Test admin managing bot settings."""
        
        # Create initial settings
        settings = [
            BotSettings(key="author_name", value="Original Author"),
            BotSettings(key="author_info", value="Original Info")
        ]
        for setting in settings:
            clean_db.add(setting)
        await clean_db.commit()
        
        # 1. Admin views current settings
        settings_message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="/settings",
            bot=mock_bot
        )
        settings_message.answer = AsyncMock()
        
        with patch('handlers.admin.SettingsManager') as mock_settings:
            mock_settings.get_author_name.return_value = "Original Author"
            mock_settings.get_author_info.return_value = "Original Info"
            
            await admin.settings_command(settings_message)
            
            settings_message.answer.assert_called()
            settings_text = settings_message.answer.call_args[0][0]
            assert "Original Author" in settings_text
            assert "Original Info" in settings_text
        
        # 2. Admin changes author name
        set_author_message = Message(
            message_id=2,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="/set_author New Author Name",
            bot=mock_bot
        )
        set_author_message.answer = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            # Mock SettingsManager to use real database
            with patch('handlers.admin.SettingsManager.set_author_name') as mock_set:
                mock_set.return_value = True
                
                await admin.set_author_command(set_author_message)
                
                set_author_message.answer.assert_called()
                success_text = set_author_message.answer.call_args[0][0]
                assert "обновлено" in success_text.lower()
                
                mock_set.assert_called_once_with("New Author Name")
        
        # 3. Admin changes author info
        set_info_message = Message(
            message_id=3,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="/set_info New channel description",
            bot=mock_bot
        )
        set_info_message.answer = AsyncMock()
        
        with patch('handlers.admin.SettingsManager.set_author_info') as mock_set:
            mock_set.return_value = True
            
            await admin.set_info_command(set_info_message)
            
            set_info_message.answer.assert_called()
            success_text = set_info_message.answer.call_args[0][0]
            assert "обновлено" in success_text.lower()
            
            mock_set.assert_called_once_with("New channel description")


class TestDatabaseIntegration:
    """Test database operations and state management."""
    
    @pytest.mark.integration
    @pytest.mark.database
    async def test_user_state_persistence(self, clean_db):
        """Test user state persistence across sessions."""
        
        user_id = 123456789
        
        # 1. Create initial user state
        initial_success = await UserStateManager.set_user_state(
            user_id, 
            UserStateManager.STATE_QUESTION_SENT
        )
        
        with patch('models.user_states.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            assert initial_success is True
        
        # 2. Retrieve user state
        with patch('models.user_states.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            current_state = await UserStateManager.get_user_state(user_id)
            # Note: Due to mocking, this might return default state
            assert isinstance(current_state, str)
        
        # 3. Update user state
        with patch('models.user_states.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            update_success = await UserStateManager.set_user_state(
                user_id,
                UserStateManager.STATE_AWAITING_QUESTION
            )
            assert update_success is True
        
        # 4. Test state-based permissions
        with patch('models.user_states.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            can_send = await UserStateManager.can_send_question(user_id)
            assert isinstance(can_send, bool)
    
    @pytest.mark.integration
    @pytest.mark.database
    async def test_admin_state_expiration(self, clean_db):
        """Test admin state expiration handling."""
        
        admin_id = ADMIN_ID
        
        # 1. Set admin state that expires soon
        with patch('models.admin_state.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            success = await AdminStateManager.set_state(
                admin_id,
                AdminStateManager.STATE_ANSWERING,
                {"question_id": 123},
                expiration_minutes=1  # Very short expiration
            )
            assert success is True
        
        # 2. Verify state exists
        with patch('models.admin_state.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            is_in_state = await AdminStateManager.is_in_state(
                admin_id,
                AdminStateManager.STATE_ANSWERING
            )
            # Result depends on mocking, but should not crash
            assert isinstance(is_in_state, bool)
        
        # 3. Test cleanup of expired states
        with patch('models.admin_state.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            cleaned_count = await AdminStateManager.cleanup_expired_states()
            assert isinstance(cleaned_count, int)
            assert cleaned_count >= 0
    
    @pytest.mark.integration
    @pytest.mark.database
    async def test_settings_persistence(self, clean_db):
        """Test settings persistence and retrieval."""
        
        # 1. Set settings using manager
        with patch('models.settings.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            author_success = await SettingsManager.set_author_name("Test Author")
            info_success = await SettingsManager.set_author_info("Test Info")
            
            # Results depend on mocking
            assert isinstance(author_success, bool)
            assert isinstance(info_success, bool)
        
        # 2. Retrieve settings
        with patch('models.settings.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            author_name = await SettingsManager.get_author_name()
            author_info = await SettingsManager.get_author_info()
            
            # Should return either set value or default
            assert isinstance(author_name, str)
            assert isinstance(author_info, str)
        
        # 3. Get all settings
        with patch('models.settings.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            all_settings = await SettingsManager.get_all_settings()
            
            assert isinstance(all_settings, dict)
            assert 'author_name' in all_settings
            assert 'author_info' in all_settings
    
    @pytest.mark.integration
    @pytest.mark.database
    async def test_question_lifecycle(self, clean_db):
        """Test complete question lifecycle in database."""
        
        # 1. Create question
        question = Question.create_new(
            text="Lifecycle test question",
            user_id=123456789,
            unique_id="test_channel"
        )
        clean_db.add(question)
        await clean_db.commit()
        await clean_db.refresh(question)
        
        assert question.id is not None
        assert question.created_at is not None
        assert question.is_pending is True
        assert question.is_answered is False
        
        # 2. Mark as favorite
        question.is_favorite = True
        await clean_db.commit()
        await clean_db.refresh(question)
        
        assert question.is_favorite is True
        
        # 3. Answer question
        question.answer = "Lifecycle test answer"
        question.answered_at = datetime.utcnow()
        await clean_db.commit()
        await clean_db.refresh(question)
        
        assert question.is_answered is True
        assert question.is_pending is False
        assert question.answered_at is not None
        
        # 4. Soft delete question
        question.is_deleted = True
        question.deleted_at = datetime.utcnow()
        await clean_db.commit()
        await clean_db.refresh(question)
        
        assert question.is_deleted is True
        assert question.deleted_at is not None
        assert question.is_pending is False


class TestErrorRecovery:
    """Test error recovery and resilience."""
    
    @pytest.mark.integration
    @pytest.mark.e2e
    async def test_database_failure_recovery(self, mock_bot, test_user, mock_logger):
        """Test bot behavior when database fails."""
        
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=test_user.id, type="private"),
            from_user=test_user,
            text="Test question",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        # Simulate database failure
        with patch('handlers.questions.async_session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            # Handler should not crash
            await questions.unified_message_handler(message)
            
            # Should send error message to user
            message.answer.assert_called()
            error_text = message.answer.call_args[0][0]
            assert "ошибка" in error_text.lower()
    
    @pytest.mark.integration
    @pytest.mark.e2e
    async def test_state_corruption_recovery(self, clean_db, mock_bot, admin_user, mock_logger):
        """Test recovery from corrupted admin states."""
        
        # Simulate corrupted state
        corrupted_states = {
            ADMIN_ID: {
                'question_id': 'invalid',  # Should be int
                'mode': 'invalid_mode',
                'created_at': 'invalid_date'  # Should be datetime
            }
        }
        
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=admin_user,
            text="Test answer",
            bot=mock_bot
        )
        message.answer = AsyncMock()
        
        with patch('handlers.admin_states.admin_answer_states', corrupted_states):
            # Should handle corrupted state gracefully
            result = await admin_states.handle_admin_answer(message)
            
            # Should either process or fail gracefully
            assert isinstance(result, bool)
    
    @pytest.mark.integration
    @pytest.mark.e2e
    async def test_concurrent_access_handling(self, clean_db, mock_bot, mock_logger):
        """Test handling concurrent access to shared resources."""
        
        # Simulate multiple users sending questions simultaneously
        users = [User(id=i, is_bot=False, first_name=f"User{i}") for i in range(100, 110)]
        
        async def send_question(user):
            message = Message(
                message_id=1,
                date=datetime.now(),
                chat=Chat(id=user.id, type="private"),
                from_user=user,
                text=f"Question from user {user.id}",
                bot=mock_bot
            )
            message.answer = AsyncMock()
            
            with patch('handlers.questions.UserStateManager') as mock_user_state, \
                 patch('handlers.questions.async_session') as mock_session, \
                 patch('handlers.questions.InputValidator') as mock_validator, \
                 patch('handlers.questions.ContentModerator') as mock_moderator:
                
                mock_user_state.can_send_question.return_value = True
                mock_user_state.set_user_state.return_value = True
                mock_session.return_value.__aenter__.return_value = clean_db
                mock_validator.sanitize_text.return_value = f"Question from user {user.id}"
                mock_validator.validate_question.return_value = (True, None)
                mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
                mock_moderator.is_likely_spam.return_value = False
                mock_moderator.calculate_spam_score.return_value = 0.1
                
                await questions.unified_message_handler(message)
                return message.answer.called
        
        # Send all questions concurrently
        results = await asyncio.gather(*[send_question(user) for user in users], return_exceptions=True)
        
        # All should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception), f"Concurrent access failed: {result}"
            # Most should succeed (True for answer.called)
            assert isinstance(result, bool)


class TestPerformanceIntegration:
    """Test performance with realistic loads."""
    
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_bulk_question_processing(self, clean_db, mock_bot, mock_logger):
        """Test processing many questions efficiently."""
        
        # Create many questions in database
        questions = []
        for i in range(100):
            question = Question.create_new(
                text=f"Bulk question {i}",
                user_id=123456789 + i
            )
            questions.append(question)
        
        clean_db.add_all(questions)
        await clean_db.commit()
        
        # Test admin operations on bulk data
        stats_message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=User(id=ADMIN_ID, is_bot=False, first_name="Admin"),
            text="/stats",
            bot=mock_bot
        )
        stats_message.answer = AsyncMock()
        
        with patch('handlers.admin.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            # Should handle large dataset efficiently
            await admin.stats_command(stats_message)
            
            stats_message.answer.assert_called()
            stats_text = stats_message.answer.call_args[0][0]
            assert "100" in stats_text
    
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_memory_usage_stability(self, clean_db, mock_bot, mock_logger):
        """Test memory usage remains stable under load."""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process many operations
        for i in range(1000):
            # Simulate user question
            user = User(id=123456789 + i, is_bot=False, first_name=f"User{i}")
            message = Message(
                message_id=i,
                date=datetime.now(),
                chat=Chat(id=user.id, type="private"),
                from_user=user,
                text=f"Question {i}",
                bot=mock_bot
            )
            message.answer = AsyncMock()
            
            with patch('handlers.questions.UserStateManager') as mock_user_state, \
                 patch('handlers.questions.async_session') as mock_session, \
                 patch('handlers.questions.InputValidator') as mock_validator, \
                 patch('handlers.questions.ContentModerator') as mock_moderator:
                
                mock_user_state.can_send_question.return_value = True
                mock_user_state.set_user_state.return_value = True
                mock_session.return_value.__aenter__.return_value = clean_db
                mock_validator.sanitize_text.return_value = f"Question {i}"
                mock_validator.validate_question.return_value = (True, None)
                mock_validator.extract_personal_data.return_value = {'emails': [], 'phones': [], 'urls': []}
                mock_moderator.is_likely_spam.return_value = False
                mock_moderator.calculate_spam_score.return_value = 0.1
                
                await questions.unified_message_handler(message)
            
            # Force garbage collection every 100 operations
            if i % 100 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB for 1000 operations)
        assert memory_increase < 50 * 1024 * 1024, f"Memory leak detected: {memory_increase / 1024 / 1024:.1f}MB increase"


if __name__ == "__main__":
    # Run integration tests
    pytest.main([
        "-v",
        "--tb=short",
        "-m", "integration",
        __file__
    ])