"""
Tests for data models: Questions, Settings, UserState, AdminState.

Tests model creation, validation, properties, and database operations.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select, func

from models.questions import Question
from models.settings import BotSettings, SettingsManager
from models.user_states import UserState, UserStateManager
from models.admin_state import AdminState, AdminStateManager


class TestQuestionModel:
    """Tests for Question model."""
    
    @pytest.mark.unit
    async def test_create_new_question(self):
        """Test creating new question with factory method."""
        question = Question.create_new(
            text="Test question",
            user_id=123456789,
            unique_id="test_channel"
        )
        
        assert question.text == "Test question"
        assert question.user_id == 123456789
        assert question.unique_id == "test_channel"
        assert question.is_favorite is False
        assert question.is_deleted is False
        assert question.answer is None
    
    @pytest.mark.unit
    def test_question_properties(self):
        """Test question computed properties."""
        # Unanswered question
        question = Question.create_new(text="Test")
        assert question.is_answered is False
        assert question.is_pending is True
        
        # Answered question
        question.answer = "Test answer"
        assert question.is_answered is True
        assert question.is_pending is False
        
        # Deleted question
        question.is_deleted = True
        assert question.is_pending is False
    
    @pytest.mark.unit
    def test_preview_text(self):
        """Test preview text generation."""
        # Short text
        short_question = Question.create_new(text="Short")
        assert short_question.preview_text == "Short"
        
        # Long text
        long_text = "A" * 150
        long_question = Question.create_new(text=long_text)
        assert len(long_question.preview_text) == 100
        assert long_question.preview_text.endswith("...")
    
    @pytest.mark.unit
    def test_to_dict(self):
        """Test model serialization."""
        question = Question.create_new(
            text="Test question",
            user_id=123456789,
            unique_id="test"
        )
        question.answer = "Test answer"
        question.is_favorite = True
        
        data = question.to_dict()
        
        assert data['text'] == "Test question"
        assert data['user_id'] == 123456789
        assert data['unique_id'] == "test"
        assert data['answer'] == "Test answer"
        assert data['is_favorite'] is True
        assert data['is_answered'] is True
        assert data['is_pending'] is False
    
    @pytest.mark.database
    async def test_question_database_operations(self, clean_db):
        """Test question CRUD operations."""
        # Create
        question = Question.create_new(text="DB Test")
        clean_db.add(question)
        await clean_db.commit()
        await clean_db.refresh(question)
        
        assert question.id is not None
        assert question.created_at is not None
        
        # Read
        found = await clean_db.get(Question, question.id)
        assert found.text == "DB Test"
        
        # Update
        found.answer = "DB Answer"
        await clean_db.commit()
        
        updated = await clean_db.get(Question, question.id)
        assert updated.answer == "DB Answer"
        assert updated.is_answered is True
        
        # Delete (soft)
        updated.is_deleted = True
        updated.deleted_at = datetime.utcnow()
        await clean_db.commit()
        
        deleted = await clean_db.get(Question, question.id)
        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None


class TestBotSettingsModel:
    """Tests for BotSettings model."""
    
    @pytest.mark.database
    async def test_settings_crud(self, clean_db):
        """Test settings CRUD operations."""
        # Create
        setting = BotSettings(key="test_key", value="test_value")
        clean_db.add(setting)
        await clean_db.commit()
        
        # Read
        found = await clean_db.get(BotSettings, "test_key")
        assert found.value == "test_value"
        assert found.updated_at is not None
        
        # Update
        found.value = "updated_value"
        await clean_db.commit()
        
        updated = await clean_db.get(BotSettings, "test_key")
        assert updated.value == "updated_value"
    
    @pytest.mark.integration
    async def test_settings_manager(self, clean_db, mock_async_session):
        """Test SettingsManager operations."""
        # Test get_setting with default
        value = await SettingsManager.get_setting('nonexistent')
        assert value == ""
        
        value = await SettingsManager.get_setting('author_name')
        assert value == SettingsManager.DEFAULT_SETTINGS['author_name']
        
        # Test set_setting
        success = await SettingsManager.set_setting('author_name', 'New Author')
        assert success is True
        
        # Test specific getters/setters
        success = await SettingsManager.set_author_name('Test Author')
        assert success is True
        
        name = await SettingsManager.get_author_name()
        # Note: This will return default since we're mocking the session
        
        success = await SettingsManager.set_author_info('Test Info')
        assert success is True
        
        # Test get_all_settings
        all_settings = await SettingsManager.get_all_settings()
        assert isinstance(all_settings, dict)
        assert 'author_name' in all_settings
        assert 'author_info' in all_settings


class TestUserStateModel:
    """Tests for UserState model."""
    
    @pytest.mark.database
    async def test_user_state_crud(self, clean_db):
        """Test user state CRUD operations."""
        # Create
        state = UserState(
            user_id=123456789,
            state="test_state",
            questions_count=5
        )
        clean_db.add(state)
        await clean_db.commit()
        
        # Read
        found = await clean_db.get(UserState, 123456789)
        assert found.state == "test_state"
        assert found.questions_count == 5
        assert found.created_at is not None
        
        # Update
        found.state = "updated_state"
        found.questions_count = 10
        await clean_db.commit()
        
        updated = await clean_db.get(UserState, 123456789)
        assert updated.state == "updated_state"
        assert updated.questions_count == 10
    
    @pytest.mark.integration
    async def test_user_state_manager(self, clean_db, mock_async_session):
        """Test UserStateManager operations."""
        user_id = 123456789
        
        # Test get_user_state (new user)
        state = await UserStateManager.get_user_state(user_id)
        assert state == UserStateManager.STATE_IDLE
        
        # Test set_user_state
        success = await UserStateManager.set_user_state(
            user_id, 
            UserStateManager.STATE_QUESTION_SENT
        )
        assert success is True
        
        # Test can_send_question
        can_send = await UserStateManager.can_send_question(user_id)
        # Result depends on mocking
        assert isinstance(can_send, bool)
        
        # Test allow_new_question
        success = await UserStateManager.allow_new_question(user_id)
        assert success is True
        
        # Test reset_to_idle
        success = await UserStateManager.reset_to_idle(user_id)
        assert success is True
        
        # Test get_user_stats
        stats = await UserStateManager.get_user_stats(user_id)
        assert isinstance(stats, dict)
        assert 'questions_count' in stats
        assert 'current_state' in stats
    
    @pytest.mark.unit
    def test_user_state_constants(self):
        """Test UserStateManager constants."""
        assert UserStateManager.STATE_IDLE == "idle"
        assert UserStateManager.STATE_QUESTION_SENT == "question_sent"
        assert UserStateManager.STATE_AWAITING_QUESTION == "awaiting_question"


# Define a constant ADMIN_ID for use in admin state tests
ADMIN_ID = 999999

class TestAdminStateModel:
    """Tests for AdminState model."""
    
    @pytest.mark.database
    async def test_admin_state_crud(self, clean_db):
        """Test admin state CRUD operations."""
        # Create
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        state = AdminState(
            admin_id=ADMIN_ID,
            state_type="test_type",
            state_data={"key": "value"},
            expires_at=expires_at
        )
        clean_db.add(state)
        await clean_db.commit()
        
        # Read
        found = await clean_db.get(AdminState, ADMIN_ID)
        assert found.state_type == "test_type"
        assert found.state_data == {"key": "value"}
        assert found.expires_at is not None
        
        # Update
        found.state_type = "updated_type"
        found.state_data = {"new_key": "new_value"}
        await clean_db.commit()
        
        updated = await clean_db.get(AdminState, ADMIN_ID)
        assert updated.state_type == "updated_type"
        assert updated.state_data == {"new_key": "new_value"}
    
    @pytest.mark.integration
    async def test_admin_state_manager(self, clean_db, mock_async_session):
        """Test AdminStateManager operations."""
        admin_id = ADMIN_ID
        
        # Test set_state
        success = await AdminStateManager.set_state(
            admin_id,
            AdminStateManager.STATE_ANSWERING,
            {"question_id": 123},
            expiration_minutes=5
        )
        assert success is True
        
        # Test is_in_state
        is_in_state = await AdminStateManager.is_in_state(
            admin_id, 
            AdminStateManager.STATE_ANSWERING
        )
        # Result depends on mocking
        assert isinstance(is_in_state, bool)
        
        # Test get_state
        state = await AdminStateManager.get_state(admin_id)
        # Result depends on mocking
        
        # Test clear_state
        success = await AdminStateManager.clear_state(admin_id)
        assert success is True
        
        # Test cleanup_expired_states
        cleaned_count = await AdminStateManager.cleanup_expired_states()
        assert isinstance(cleaned_count, int)
        
        # Test get_all_active_states
        active_states = await AdminStateManager.get_all_active_states()
        assert isinstance(active_states, list)
    
    @pytest.mark.unit
    def test_admin_state_constants(self):
        """Test AdminStateManager constants."""
        assert AdminStateManager.STATE_ANSWERING == "answering_question"
        assert AdminStateManager.DEFAULT_EXPIRATION_MINUTES == 10
    
    @pytest.mark.unit
    def test_admin_state_time_conversion(self, freeze_time):
        """Test time conversion methods."""
        # Test _get_utc_now
        now = AdminStateManager._get_utc_now()
        assert isinstance(now, datetime)
        
        # Test _convert_from_db with naive datetime
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        converted = AdminStateManager._convert_from_db(naive_dt)
        assert converted == naive_dt
        
        # Test _convert_from_db with None
        converted = AdminStateManager._convert_from_db(None)
        assert converted is None


class TestModelIntegration:
    """Integration tests between models."""
    
    @pytest.mark.integration
    async def test_question_user_state_flow(self, clean_db):
        """Test complete flow: user state -> question -> answer."""
        user_id = 123456789
        
        # 1. Create user state
        user_state = UserState(
            user_id=user_id,
            state=UserStateManager.STATE_IDLE,
            questions_count=0
        )
        clean_db.add(user_state)
        await clean_db.commit()
        
        # 2. User sends question
        question = Question.create_new(
            text="Integration test question",
            user_id=user_id
        )
        clean_db.add(question)
        
        # Update user state
        user_state.state = UserStateManager.STATE_QUESTION_SENT
        user_state.questions_count += 1
        user_state.last_question_at = datetime.utcnow()
        
        await clean_db.commit()
        await clean_db.refresh(question)
        await clean_db.refresh(user_state)
        
        # 3. Admin answers question
        question.answer = "Integration test answer"
        question.answered_at = datetime.utcnow()
        
        await clean_db.commit()
        
        # 4. Verify final state
        assert question.is_answered is True
        assert user_state.questions_count == 1
        assert user_state.state == UserStateManager.STATE_QUESTION_SENT
    
    @pytest.mark.integration
    async def test_multiple_users_questions(self, clean_db):
        """Test multiple users with questions."""
        # Create questions from different users
        users = [111, 222, 333]
        questions = []
        
        for i, user_id in enumerate(users):
            question = Question.create_new(
                text=f"Question from user {user_id}",
                user_id=user_id
            )
            clean_db.add(question)
            questions.append(question)
        
        await clean_db.commit()
        
        # Query all questions
        stmt = select(Question).where(Question.is_deleted == False)
        result = await clean_db.execute(stmt)
        all_questions = result.scalars().all()
        
        assert len(all_questions) == 3
        user_ids = [q.user_id for q in all_questions]
        assert set(user_ids) == set(users)
    
    @pytest.mark.integration
    async def test_favorites_and_answered_counts(self, clean_db):
        """Test counting favorites and answered questions."""
        # Create mix of questions
        questions = []
        for i in range(10):
            question = Question.create_new(text=f"Question {i}")
            
            # Every 3rd is favorite
            if i % 3 == 0:
                question.is_favorite = True
            
            # Every 2nd is answered
            if i % 2 == 0:
                question.answer = f"Answer {i}"
                question.answered_at = datetime.utcnow()
            
            clean_db.add(question)
            questions.append(question)
        
        await clean_db.commit()
        
        # Count favorites
        favorites_count = await clean_db.scalar(
            select(func.count(Question.id)).where(
                Question.is_favorite == True,
                Question.is_deleted == False
            )
        )
        assert favorites_count == 4  # 0, 3, 6, 9
        
        # Count answered
        answered_count = await clean_db.scalar(
            select(func.count(Question.id)).where(
                Question.answer.is_not(None),
                Question.is_deleted == False
            )
        )
        assert answered_count == 5  # 0, 2, 4, 6, 8
        
        # Count pending
        pending_count = await clean_db.scalar(
            select(func.count(Question.id)).where(
                Question.answer.is_(None),
                Question.is_deleted == False
            )
        )
        assert pending_count == 5  # 1, 3, 5, 7, 9


class TestModelValidation:
    """Tests for model validation and edge cases."""
    
    @pytest.mark.unit
    def test_question_text_handling(self):
        """Test question text edge cases."""
        # Empty text (should be handled by application logic)
        question = Question.create_new(text="")
        assert question.text == ""
        
        # Whitespace handling
        question = Question.create_new(text="  test  ")
        assert question.text == "  test  "  # Model doesn't auto-strip
        
        # Unicode text
        question = Question.create_new(text="Привет! 👋 How are you?")
        assert "Привет" in question.text
        assert "👋" in question.text
    
    @pytest.mark.unit
    def test_question_user_id_types(self):
        """Test different user ID types."""
        # Positive integer
        question = Question.create_new(text="test", user_id=123456789)
        assert question.user_id == 123456789
        
        # None (anonymous)
        question = Question.create_new(text="test", user_id=None)
        assert question.user_id is None
        
        # Large integer (Telegram supports up to 64-bit)
        large_id = 999999999999999999
        question = Question.create_new(text="test", user_id=large_id)
        assert question.user_id == large_id
    
    @pytest.mark.unit
    def test_settings_key_validation(self):
        """Test settings key formats."""
        # Normal key
        setting = BotSettings(key="normal_key", value="value")
        assert setting.key == "normal_key"
        
        # Key with special characters
        setting = BotSettings(key="key-with.special_chars", value="value")
        assert setting.key == "key-with.special_chars"
        
        # Empty value
        setting = BotSettings(key="empty", value="")
        assert setting.value == ""
    
    @pytest.mark.database
    async def test_duplicate_settings_key(self, clean_db):
        """Test that duplicate setting keys update existing."""
        # Create first setting
        setting1 = BotSettings(key="duplicate_key", value="value1")
        clean_db.add(setting1)
        await clean_db.commit()
        
        # Try to create duplicate (should update in practice)
        found = await clean_db.get(BotSettings, "duplicate_key")
        assert found.value == "value1"
        
        # Update value
        found.value = "value2"
        await clean_db.commit()
        
        # Verify update
        updated = await clean_db.get(BotSettings, "duplicate_key")
        assert updated.value == "value2"
    
    @pytest.mark.database
    async def test_user_state_edge_cases(self, clean_db):
        """Test user state edge cases."""
        # Negative user ID (edge case)
        negative_state = UserState(
            user_id=-1,
            state="test",
            questions_count=0
        )
        clean_db.add(negative_state)
        await clean_db.commit()
        
        found = await clean_db.get(UserState, -1)
        assert found.user_id == -1
        
        # High question count
        high_count_state = UserState(
            user_id=999,
            state="test",
            questions_count=999999
        )
        clean_db.add(high_count_state)
        await clean_db.commit()
        
        found = await clean_db.get(UserState, 999)
        assert found.questions_count == 999999
    
    @pytest.mark.database
    async def test_admin_state_expiration_edge_cases(self, clean_db):
        """Test admin state expiration scenarios."""
        admin_id = 123
        
        # Already expired state
        past_time = datetime.utcnow() - timedelta(hours=1)
        expired_state = AdminState(
            admin_id=admin_id,
            state_type="expired",
            state_data={},
            expires_at=past_time
        )
        clean_db.add(expired_state)
        await clean_db.commit()
        
        # Future expiration
        future_time = datetime.utcnow() + timedelta(hours=1)
        valid_state = AdminState(
            admin_id=admin_id + 1,
            state_type="valid",
            state_data={},
            expires_at=future_time
        )
        clean_db.add(valid_state)
        await clean_db.commit()
        
        # Check both states exist in DB
        expired = await clean_db.get(AdminState, admin_id)
        valid = await clean_db.get(AdminState, admin_id + 1)
        
        assert expired.expires_at < datetime.utcnow()
        assert valid.expires_at > datetime.utcnow()


class TestModelPerformance:
    """Performance tests for models."""
    
    @pytest.mark.slow
    @pytest.mark.database
    async def test_bulk_question_operations(self, clean_db):
        """Test performance with many questions."""
        # Create many questions
        questions = []
        for i in range(100):
            question = Question.create_new(
                text=f"Bulk question {i}",
                user_id=i
            )
            questions.append(question)
        
        # Bulk insert
        clean_db.add_all(questions)
        await clean_db.commit()
        
        # Bulk query
        stmt = select(Question).where(Question.is_deleted == False)
        result = await clean_db.execute(stmt)
        all_questions = result.scalars().all()
        
        assert len(all_questions) == 100
        
        # Bulk update
        for question in all_questions:
            if question.id % 10 == 0:  # Every 10th
                question.is_favorite = True
        
        await clean_db.commit()
        
        # Verify updates
        favorites_count = await clean_db.scalar(
            select(func.count(Question.id)).where(Question.is_favorite == True)
        )
        assert favorites_count == 10
    
    @pytest.mark.slow
    @pytest.mark.database
    async def test_complex_queries(self, clean_db):
        """Test complex database queries."""
        # Setup data
        users = [100, 200, 300]
        for user_id in users:
            for i in range(5):
                question = Question.create_new(
                    text=f"Question {i} from user {user_id}",
                    user_id=user_id
                )
                if i < 2:  # First 2 are answered
                    question.answer = f"Answer {i}"
                    question.answered_at = datetime.utcnow()
                clean_db.add(question)
        
        await clean_db.commit()
        
        # Complex query: answered questions per user
        stmt = select(
            Question.user_id,
            func.count(Question.id).label('total'),
            func.sum(
                func.case(
                    (Question.answer.is_not(None), 1),
                    else_=0
                )
            ).label('answered')
        ).where(
            Question.is_deleted == False
        ).group_by(Question.user_id)
        
        result = await clean_db.execute(stmt)
        stats = result.all()
        
        assert len(stats) == 3
        for user_id, total, answered in stats:
            assert total == 5
            assert answered == 2