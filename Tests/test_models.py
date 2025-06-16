"""
Tests for model operations and data integrity validation.
This module contains comprehensive tests for all database models,
covering CRUD operations, state management, and data validation.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy import select, func


class TestCriticalQuestionModel:
    """Tests for Question model covering core functionality and state management.

    This test suite ensures that the Question model properly handles:
    - Creation and initialization
    - State transitions
    - Data validation
    - CRUD operations
    - Text preview generation
    """

    @pytest.mark.unit
    @pytest.mark.models
    def test_create_new_question(self):
        """Test Question model factory method for creating new questions.

        Verifies:
        - All fields are properly initialized
        - Default values are correctly set
        - State flags are in expected initial state
        """
        from models.questions import Question

        question = Question.create_new(
            text="Test question",
            user_id=123456789
        )

        assert question.text == "Test question"
        assert question.user_id == 123456789
        assert question.is_favorite is False
        assert question.is_deleted is False
        assert question.answer is None
        assert question.is_answered is False
        assert question.is_pending is True

    @pytest.mark.unit
    @pytest.mark.models
    def test_question_state_properties(self):
        """Test question state logic - critical for bot workflow."""
        from models.questions import Question

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

    @pytest.mark.asyncio
    @pytest.mark.database
    @pytest.mark.models
    async def test_question_crud_operations(self, clean_db):
        """Test question CRUD - essential for bot functionality."""
        from models.questions import Question

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

    @pytest.mark.models
    @pytest.mark.unit
    def test_question_preview_text(self):
        """Test generation of preview text for admin interface."""
        from models.questions import Question

        # Short text
        short_question = Question.create_new(text="Short?")
        assert short_question.preview_text == "Short?"

        # Long text
        long_text = "x" * 150
        long_question = Question.create_new(text=long_text)
        assert len(long_question.preview_text) <= 100
        assert long_question.preview_text.endswith("...")

    @pytest.mark.models
    @pytest.mark.unit
    def test_question_to_dict(self):
        """Test converting model instance to dictionary."""
        from models.questions import Question

        question = Question.create_new(
            text="Test question",
            user_id=123456789,
            unique_id="test_123"
        )
        question.answer = "Test answer"

        data = question.to_dict()

        assert data['text'] == "Test question"
        assert data['user_id'] == 123456789
        assert data['unique_id'] == "test_123"
        assert data['answer'] == "Test answer"
        assert data['is_answered'] is True
        assert data['is_pending'] is False
        assert 'created_at' in data
        assert 'preview_text' in data


class TestCriticalSettings:
    """Critical tests for bot settings - essential for configuration."""

    @pytest.mark.asyncio
    @pytest.mark.database
    @pytest.mark.models
    async def test_settings_basic_operations(self, clean_db):
        """Test settings CRUD operations."""
        from models.settings import BotSettings

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

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.models
    async def test_settings_manager_core_functions(self, clean_db):
        """Test SettingsManager core functionality."""
        from models.settings import SettingsManager, BotSettings

        # Create test settings in database
        test_setting = BotSettings(key="author_name", value="Test Author")
        clean_db.add(test_setting)
        await clean_db.commit()

        # Patch async_session to use our test session
        from unittest.mock import patch
        with patch('models.settings.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db

            # Test getting setting
            name = await SettingsManager.get_author_name()
            assert isinstance(name, str)

            # Test setting setting
            success = await SettingsManager.set_author_name('New Test Author')
            assert success is True

    @pytest.mark.asyncio
    @pytest.mark.models
    @pytest.mark.unit
    async def test_settings_manager_defaults(self):
        """Test returning default values when database fails."""
        from models.settings import SettingsManager
        from unittest.mock import patch

        # Mock database error
        with patch('models.settings.async_session') as mock_session:
            mock_session.side_effect = Exception("DB Error")

            # Should return default value
            name = await SettingsManager.get_author_name()
            assert name == SettingsManager.DEFAULT_SETTINGS['author_name']

            info = await SettingsManager.get_author_info()
            assert info == SettingsManager.DEFAULT_SETTINGS['author_info']


class TestCriticalUserStates:
    """Critical tests for user state management - essential for bot flow."""

    @pytest.mark.asyncio
    @pytest.mark.database
    @pytest.mark.models
    async def test_user_state_crud(self, clean_db):
        """Test user state CRUD operations."""
        from models.user_states import UserState

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

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.models
    async def test_user_state_manager_core(self, clean_db):
        """Test UserStateManager core functionality."""
        from models.user_states import UserStateManager
        from unittest.mock import patch

        user_id = 123456789

        with patch('models.user_states.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db

            # Test setting state
            success = await UserStateManager.set_user_state(
                user_id,
                UserStateManager.STATE_QUESTION_SENT
            )
            assert success is True

            # Test getting state
            state = await UserStateManager.get_user_state(user_id)
            assert isinstance(state, str)

            # Test checking if user can send question
            can_send = await UserStateManager.can_send_question(user_id)
            assert isinstance(can_send, bool)

    @pytest.mark.asyncio
    @pytest.mark.models
    @pytest.mark.unit
    async def test_user_state_constants(self):
        """Test state constants are properly defined."""
        from models.user_states import UserStateManager

        assert hasattr(UserStateManager, 'STATE_IDLE')
        assert hasattr(UserStateManager, 'STATE_QUESTION_SENT')
        assert hasattr(UserStateManager, 'STATE_AWAITING_QUESTION')

        assert UserStateManager.STATE_IDLE == "idle"
        assert UserStateManager.STATE_QUESTION_SENT == "question_sent"
        assert UserStateManager.STATE_AWAITING_QUESTION == "awaiting_question"


class TestCriticalDataIntegrity:
    """Tests for data integrity and consistency."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.models
    async def test_question_user_relationship(self, clean_db):
        """Test question-user data consistency."""
        from models.questions import Question
        from models.user_states import UserState, UserStateManager

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

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.models
    async def test_question_workflow_states(self, clean_db):
        """Test question states through complete workflow."""
        from models.questions import Question

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

    @pytest.mark.asyncio
    @pytest.mark.database
    @pytest.mark.models
    async def test_database_constraints(self, clean_db):
        """Test database constraints and data validation."""
        from models.questions import Question
        from models.settings import BotSettings

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

    @pytest.mark.asyncio
    @pytest.mark.database
    @pytest.mark.models
    async def test_pending_questions_query(self, clean_db):
        """Test query for pending questions - used in admin interface."""
        from models.questions import Question

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

    @pytest.mark.asyncio
    @pytest.mark.database
    @pytest.mark.models
    async def test_stats_queries(self, clean_db):
        """Test statistics queries - used in admin dashboard."""
        from models.questions import Question

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


class TestModelValidation:
    """Tests for model validation and data integrity."""

    @pytest.mark.models
    @pytest.mark.unit
    def test_question_factory_validation(self):
        """Test validation when creating question."""
        from models.questions import Question

        # Valid data
        question = Question.create_new(
            text="  Valid question  ",  # With spaces
            user_id=123456789
        )

        # Text should be cleaned
        assert question.text == "Valid question"
        assert question.user_id == 123456789

        # Default values
        assert question.is_favorite is False
        assert question.is_deleted is False
        assert question.answer is None

    @pytest.mark.models
    @pytest.mark.unit
    def test_settings_key_validation(self):
        """Test validation of settings keys."""
        from models.settings import BotSettings

        # Valid keys
        valid_keys = ["author_name", "author_info", "custom_setting"]

        for key in valid_keys:
            setting = BotSettings(key=key, value="test")
            assert setting.key == key
            assert setting.value == "test"

    @pytest.mark.models
    @pytest.mark.unit
    def test_user_state_validation(self):
        """Test validation of user states."""
        from models.user_states import UserState, UserStateManager

        # Valid states
        valid_states = [
            UserStateManager.STATE_IDLE,
            UserStateManager.STATE_QUESTION_SENT,
            UserStateManager.STATE_AWAITING_QUESTION
        ]

        for state in valid_states:
            user_state = UserState(
                user_id=123456789,
                state=state,
                questions_count=0
            )
            assert user_state.state == state
            assert user_state.user_id == 123456789


class TestAdminStateModel:
    """Tests for AdminState model functionality."""

    @pytest.mark.asyncio
    @pytest.mark.database
    @pytest.mark.models
    async def test_admin_state_crud(self, clean_db):
        """Test AdminState CRUD operations."""
        from models.admin_state import AdminState
        from datetime import timedelta

        # Create
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        admin_state = AdminState(
            admin_id=123456789,
            state_type="answering_question",
            state_data={"question_id": 123},
            expires_at=expires_at
        )
        clean_db.add(admin_state)
        await clean_db.commit()

        # Read
        found = await clean_db.get(AdminState, 123456789)
        assert found.state_type == "answering_question"
        assert found.state_data["question_id"] == 123

        # Update
        found.state_data = {"question_id": 456}
        await clean_db.commit()

        updated = await clean_db.get(AdminState, 123456789)
        assert updated.state_data["question_id"] == 456

        # Delete
        await clean_db.delete(updated)
        await clean_db.commit()

        deleted = await clean_db.get(AdminState, 123456789)
        assert deleted is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.models
    async def test_admin_state_manager(self, clean_db):
        """Test AdminStateManager functionality."""
        from models.admin_state import AdminStateManager
        from unittest.mock import patch

        admin_id = 123456789
        state_data = {"question_id": 123, "user_id": 987654321}

        with patch('models.admin_state.async_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = clean_db

            # Test setting state
            success = await AdminStateManager.set_state(
                admin_id,
                AdminStateManager.STATE_ANSWERING,
                state_data
            )
            assert success is True

            # Test getting state
            state = await AdminStateManager.get_state(admin_id)
            assert state is not None
            assert state['type'] == AdminStateManager.STATE_ANSWERING
            assert state['data'] == state_data

            # Test checking if admin is in state
            is_in_state = await AdminStateManager.is_in_state(
                admin_id,
                AdminStateManager.STATE_ANSWERING
            )
            assert is_in_state is True

            # Test clearing state
            success = await AdminStateManager.clear_state(admin_id)
            assert success is True
