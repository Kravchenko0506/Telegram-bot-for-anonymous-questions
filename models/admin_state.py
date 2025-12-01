"""
Admin state management with database persistence and expiration.
"""

from sqlalchemy import Column, BigInteger, String, DateTime, JSON
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from models.database import Base, async_session
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class AdminState(Base):
    """Database model for admin states with expiration."""

    __tablename__ = "admin_states"

    admin_id = Column(BigInteger, primary_key=True)
    state_type = Column(String(50), nullable=False)
    state_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<AdminState(admin_id={self.admin_id}, type='{self.state_type}')>"


class AdminStateManager:
    """Manager for admin states with automatic expiration."""

    STATE_ANSWERING = "answering_question"
    DEFAULT_EXPIRATION_MINUTES = 10

    @staticmethod
    def _utc_now() -> datetime:
        """Get current UTC time as naive datetime."""
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _to_naive(dt: Optional[datetime]) -> Optional[datetime]:
        """Convert datetime to naive UTC."""
        if dt is None or dt.tzinfo is None:
            return dt
        return dt.replace(tzinfo=None)

    @staticmethod
    async def set_state(
        admin_id: int,
        state_type: str,
        state_data: Dict[str, Any],
        expiration_minutes: int = DEFAULT_EXPIRATION_MINUTES
    ) -> bool:
        """Set or update admin state with expiration."""
        try:
            expires_at = AdminStateManager._utc_now() + timedelta(minutes=expiration_minutes)

            async with async_session() as session:
                existing = await session.get(AdminState, admin_id)

                if existing:
                    existing.state_type = state_type
                    existing.state_data = state_data
                    existing.expires_at = expires_at
                else:
                    session.add(AdminState(
                        admin_id=admin_id,
                        state_type=state_type,
                        state_data=state_data,
                        expires_at=expires_at
                    ))

                await session.commit()
                logger.info(f"State set for admin {admin_id}: {state_type}")
                return True

        except Exception as e:
            logger.error(f"Failed to set admin state: {e}")
            return False

    @staticmethod
    async def get_state(admin_id: int) -> Optional[Dict[str, Any]]:
        """Get admin state if valid, auto-delete if expired."""
        try:
            async with async_session() as session:
                state = await session.get(AdminState, admin_id)

                if not state:
                    return None

                now = AdminStateManager._utc_now()
                expires_at = AdminStateManager._to_naive(state.expires_at)

                if now > expires_at:
                    await session.delete(state)
                    await session.commit()
                    logger.info(f"Expired state removed for admin {admin_id}")
                    return None

                return {
                    'type': state.state_type,
                    'data': state.state_data,
                    'created_at': AdminStateManager._to_naive(state.created_at),
                    'expires_at': expires_at
                }

        except Exception as e:
            logger.error(f"Failed to get admin state: {e}")
            return None

    @staticmethod
    async def clear_state(admin_id: int) -> bool:
        """Remove admin state from database."""
        try:
            async with async_session() as session:
                state = await session.get(AdminState, admin_id)
                if state:
                    await session.delete(state)
                    await session.commit()
                    logger.info(f"Cleared state for admin {admin_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to clear admin state: {e}")
            return False

    @staticmethod
    async def is_in_state(admin_id: int, state_type: str) -> bool:
        """Check if admin is in a specific state."""
        state = await AdminStateManager.get_state(admin_id)
        return state is not None and state['type'] == state_type

    @staticmethod
    async def cleanup_expired_states() -> int:
        """Remove all expired states from database."""
        try:
            async with async_session() as session:
                from sqlalchemy import delete

                now = AdminStateManager._utc_now()
                stmt = delete(AdminState).where(AdminState.expires_at < now)
                result = await session.execute(stmt)
                await session.commit()

                count = result.rowcount
                if count > 0:
                    logger.info(f"Cleaned up {count} expired admin states")
                return count

        except Exception as e:
            logger.error(f"Failed to cleanup expired states: {e}")
            return 0
