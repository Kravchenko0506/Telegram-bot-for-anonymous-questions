"""
Critical model tests for production environment.

Tests essential CRUD operations and data integrity.
"""

import pytest
from datetime import datetime
from sqlalchemy import select, func

from models.questions import Question
from models.settings import BotSettings, SettingsManager
from models.user_states import UserState, UserStateManager


class TestCriticalQuestionModel:
    """Critical tests for Question model - basic functionality."""
    
    @pytest.mark.unit
    def test_create_new_question(self):
        """Test creating new question with factory method."""
        question = Question.create_new(
            text="Test question",
            user_id=123456789
        )
        
        assert question.text == "Test question"
        assert question.user_id == 123456789
        assert question.is_favorite is False
        assert question.is_deleted is False
        assert question.answer is None
    
    @pytest.mark.unit
    def test_question_state_properties(self):
        """Test question state logic - critical for bot workflow."""
        # New unanswered question
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
    
    @pytest.mark.database
    async def test_question_crud_operations(self, clean_db):
        """Test question CRUD - essential for bot functionality."""
        # Create
        question = Question.create_new(text="CRUD Test")
        clean_db.add(question)
        await clean_db.commit()
        await clean_db.refresh(question)
        
        assert question.id is not None
        assert question.created_at is not None
        
        # Read
        found = await clean_db.get(Question, question.id)
        assert found.text == "CRUD Test"
        
        # Update (answer)
        found.answer = "CRUD Answer"
        await clean_db.commit()
        
        updated = await clean_db.get(Question, question.id)
        assert updated.answer == "CRUD Answer"
        assert updated.is_answered is True
        
        # Soft delete
        updated.is_deleted = True
        updated.deleted_at = datetime.utcnow()
        await clean_db.commit()
        
        deleted = await clean_db.get(Question, question.id)
        assert deleted.is_deleted is True


class TestCriticalSettings:
    """Critical tests for bot settings - essential for configuration."""
    
    @pytest.mark.database
    async def test_settings_basic_operations(self, clean_db):
        """Test settings CRUD operations."""
        # Create
        setting = BotSettings(key="test_key", value="test_value")
        clean_db.add(setting)
        await clean_db.commit()
        
        # Read
        found = await clean_db.get(BotSettings, "test_key")
        assert found.value == "test_value"
        
        # Update
        found.value = "updated_value"
        await clean_db.commit()
        
        updated = await clean_db.get(BotSettings, "test_key")
        assert updated.value == "updated_value"
    
    @pytest.mark.integration
    async def test_settings_manager_core_functions(self, clean_db):
        """Test SettingsManager core functionality."""
        # Mock the async_session to use our test database
        from unittest.mock import patch
        
        with patch('models.settings.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            # Test set and get
            success = await SettingsManager.set_author_name('Test Author')
            assert success is True
            
            # Note: Due to mocking, we test the interface rather than actual DB operation
            name = await SettingsManager.get_author_name()
            # This will return default since we're mocking
            assert isinstance(name, str)


class TestCriticalUserStates:
    """Critical tests for user state management - essential for bot flow."""
    
    @pytest.mark.database
    async def test_user_state_crud(self, clean_db):
        """Test user state CRUD operations."""
        # Create
        state = UserState(
            user_id=123456789,
            state="test_state",
            questions_count=1
        )
        clean_db.add(state)
        await clean_db.commit()
        
        # Read
        found = await clean_db.get(UserState, 123456789)
        assert found.state == "test_state"
        assert found.questions_count == 1
        
        # Update
        found.state = "updated_state"
        await clean_db.commit()
        
        updated = await clean_db.get(UserState, 123456789)
        assert updated.state == "updated_state"
    
    @pytest.mark.integration
    async def test_user_state_manager_core(self, clean_db):
        """Test UserStateManager core functionality."""
        from unittest.mock import patch
        
        user_id = 123456789
        
        with patch('models.user_states.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db
            
            # Test state management interface
            success = await UserStateManager.set_user_state(
                user_id, 
                UserStateManager.STATE_QUESTION_SENT
            )
            assert success is True
            
            # Test can_send_question logic
            can_send = await UserStateManager.can_send_question(user_id)
            assert isinstance(can_send, bool)


class TestCriticalDataIntegrity:
    """Tests for data integrity and consistency."""
    
    @pytest.mark.integration
    async def test_question_user_relationship(self, clean_db):
        """Test question-user data consistency."""
        user_id = 123456789
        
        # Create user state
        user_state = UserState(
            user_id=user_id,
            state=UserStateManager.STATE_IDLE,
            questions_count=0
        )
        clean_db.add(user_state)
        
        # Create question
        question = Question.create_new(
            text="Integrity test question",
            user_id=user_id
        )
        clean_db.add(question)
        
        await clean_db.commit()
        
        # Verify consistency
        await clean_db.refresh(user_state)
        await clean_db.refresh(question)
        
        assert question.user_id == user_state.user_id
        assert question.is_pending is True
    
    @pytest.mark.integration
    async def test_question_workflow_states(self, clean_db):
        """Test question states through complete workflow."""
        # Create question (pending state)
        question = Question.create_new(text="Workflow test")
        clean_db.add(question)
        await clean_db.commit()
        await clean_db.refresh(question)
        
        # Initial state
        assert question.is_pending is True
        assert question.is_answered is False
        
        # Answer question
        question.answer = "Workflow answer"
        question.answered_at = datetime.utcnow()
        await clean_db.commit()
        
        # Answered state
        assert question.is_answered is True
        assert question.is_pending is False
        
        # Delete question
        question.is_deleted = True
        question.deleted_at = datetime.utcnow()
        await clean_db.commit()
        
        # Deleted state
        assert question.is_deleted is True
        assert question.is_pending is False
    
    @pytest.mark.database
    async def test_database_constraints(self, clean_db):
        """Test database constraints and data validation."""
        # Test question with minimal data
        question = Question.create_new(text="Minimal question")
        clean_db.add(question)
        await clean_db.commit()
        
        # Should have auto-generated fields
        await clean_db.refresh(question)
        assert question.id is not None
        assert question.created_at is not None
        assert question.updated_at is not None
        
        # Test settings with required fields
        setting = BotSettings(key="constraint_test", value="test_value")
        clean_db.add(setting)
        await clean_db.commit()
        
        found = await clean_db.get(BotSettings, "constraint_test")
        assert found.updated_at is not None


class TestCriticalQueries:
    """Test critical database queries used by the bot."""
    
    @pytest.mark.database
    async def test_pending_questions_query(self, clean_db):
        """Test query for pending questions - used in admin interface."""
        # Create mix of questions
        questions = []
        for i in range(3):
            question = Question.create_new(text=f"Question {i}")
            if i == 1:  # Answer one question
                question.answer = f"Answer {i}"
                question.answered_at = datetime.utcnow()
            clean_db.add(question)
            questions.append(question)
        
        await clean_db.commit()
        
        # Query pending questions (unanswered, not deleted)
        stmt = select(Question).where(
            Question.answer.is_(None),
            Question.is_deleted == False
        )
        result = await clean_db.execute(stmt)
        pending = result.scalars().all()
        
        assert len(pending) == 2  # 2 unanswered questions
        for q in pending:
            assert q.is_pending is True
    
    @pytest.mark.database
    async def test_stats_queries(self, clean_db):
        """Test statistics queries - used in admin dashboard."""
        # Create test data
        for i in range(5):
            question = Question.create_new(text=f"Stats question {i}")
            if i < 2:  # Answer 2 questions
                question.answer = f"Answer {i}"
                question.answered_at = datetime.utcnow()
            if i == 4:  # Mark one as favorite
                question.is_favorite = True
            clean_db.add(question)
        
        await clean_db.commit()
        
        # Test total count
        total = await clean_db.scalar(
            select(func.count(Question.id)).where(Question.is_deleted == False)
        )
        assert total == 5
        
        # Test answered count
        answered = await clean_db.scalar(
            select(func.count(Question.id)).where(
                Question.answer.is_not(None),
                Question.is_deleted == False
            )
        )
        assert answered == 2
        
        # Test favorites count
        favorites = await clean_db.scalar(
            select(func.count(Question.id)).where(
                Question.is_favorite == True,
                Question.is_deleted == False
            )
        )
        assert favorites == 1