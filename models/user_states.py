"""User state management for question flow control."""

from sqlalchemy import Column, BigInteger, String, DateTime, select, and_
from sqlalchemy.sql import func
from datetime import datetime, timedelta

from models.database import Base, async_session
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class UserState(Base):
    """Database model for user state tracking."""

    __tablename__ = "user_states"

    user_id = Column(BigInteger, primary_key=True)
    state = Column(String(50), nullable=False, default="idle")
    last_question_at = Column(DateTime, nullable=True)
    questions_count = Column(BigInteger, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<UserState(user_id={self.user_id}, state='{self.state}', questions={self.questions_count})>"


class UserStateManager:
    """Manager for user state operations."""

    STATE_IDLE = "idle"
    STATE_QUESTION_SENT = "question_sent"
    STATE_AWAITING_QUESTION = "awaiting_question"

    @staticmethod
    async def get_user_state(user_id: int) -> str:
        """Get current user state, returns 'idle' if not found."""
        try:
            async with async_session() as session:
                user_state = await session.get(UserState, user_id)
                if user_state:
                    return user_state.state
                return UserStateManager.STATE_IDLE
        except Exception as e:
            logger.error(f"Error getting user state for {user_id}: {e}")
            return UserStateManager.STATE_IDLE


    @staticmethod
    async def set_user_state(user_id: int, state: str) -> bool:
        """Set user state with question counting."""
        try:
            async with async_session() as session:
                user_state = await session.get(UserState, user_id)

                if user_state:
                    user_state.state = state
                    if state == UserStateManager.STATE_QUESTION_SENT:
                        user_state.last_question_at = datetime.utcnow()
                        user_state.questions_count += 1
                else:
                    user_state = UserState(
                        user_id=user_id,
                        state=state,
                        last_question_at=datetime.utcnow(
                        ) if state == UserStateManager.STATE_QUESTION_SENT else None,
                        questions_count=1 if state == UserStateManager.STATE_QUESTION_SENT else 0
                    )
                    session.add(user_state)

                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting user state for {user_id}: {e}")
            return False


    @staticmethod
    async def can_send_question(user_id: int) -> bool:
        """Check if user can submit a question (idle or awaiting_question state)."""
        state = await UserStateManager.get_user_state(user_id)
        return state in [UserStateManager.STATE_IDLE, UserStateManager.STATE_AWAITING_QUESTION]


    @staticmethod
    async def allow_new_question(user_id: int) -> bool:
        """Enable new question submission for user."""
        return await UserStateManager.set_user_state(user_id, UserStateManager.STATE_AWAITING_QUESTION)


    @staticmethod
    async def reset_to_idle(user_id: int) -> bool:
        """Reset user state to idle."""
        return await UserStateManager.set_user_state(user_id, UserStateManager.STATE_IDLE)


    @staticmethod
    async def cleanup_old_states(hours: int = 24) -> int:
        """Reset states to idle for users inactive for specified hours."""
        try:
            async with async_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)

                stmt = select(UserState).where(
                    and_(
                        UserState.state != UserStateManager.STATE_IDLE,
                        UserState.updated_at < cutoff_time
                    )
                )

                result = await session.execute(stmt)
                old_states = result.scalars().all()

                count = 0
                for user_state in old_states:
                    user_state.state = UserStateManager.STATE_IDLE
                    count += 1

                await session.commit()

                if count > 0:
                    logger.info(f"Cleaned up {count} old user states")

                return count
        except Exception as e:
            logger.error(f"Error cleaning up old user states: {e}")
            return 0
