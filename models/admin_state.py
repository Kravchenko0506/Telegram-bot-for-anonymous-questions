"""
Admin State Management System

A comprehensive system for managing admin states in the database with timezone support.
This module provides functionality for:
- State persistence and retrieval
- Automatic state expiration
- Timezone-aware datetime handling
- State cleanup and maintenance
- Admin action tracking

Features:
- Timezone-aware state management
- Automatic state expiration
- Database-backed persistence
- Atomic state operations
- State cleanup utilities
- Comprehensive error handling
"""

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from models.database import Base, async_session
from utils.logger import get_admin_logger

logger = get_admin_logger()


class AdminState(Base):
    """
    Database model for storing admin states.

    Features:
    - Timezone-aware timestamps
    - JSON state data storage
    - Automatic timestamp updates
    - State expiration tracking

    Attributes:
        admin_id: Unique identifier for the admin
        state_type: Type of state (e.g., answering_question)
        state_data: JSON data associated with the state
        created_at: Timestamp when state was created
        expires_at: Timestamp when state expires
        updated_at: Timestamp of last update
    """

    __tablename__ = "admin_states"

    admin_id = Column(BigInteger, primary_key=True)
    state_type = Column(String(50), nullable=False)
    state_data = Column(JSON, nullable=False, default=dict)

    # Timestamps с timezone=True
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<AdminState(admin_id={self.admin_id}, type='{self.state_type}', expires={self.expires_at})>"


class AdminStateManager:
    """
    Manager class for handling admin states with timezone support.

    This class provides a comprehensive interface for:
    - Setting and retrieving admin states
    - Managing state expiration
    - Handling timezone conversions
    - Cleaning up expired states
    - Tracking state changes

    All datetime operations are performed in UTC for consistency.
    """

    STATE_ANSWERING = "answering_question"
    DEFAULT_EXPIRATION_MINUTES = 10

    @staticmethod
    def _get_utc_now():
        """
        Get current UTC datetime without timezone info for compatibility.

        Returns:
            datetime: Current UTC time as naive datetime
        """
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _convert_from_db(db_datetime):
        """
        Convert database datetime to naive UTC format.

        PostgreSQL returns timezone-aware datetime in UTC.
        We convert it to naive UTC for consistency.

        Args:
            db_datetime: DateTime from database

        Returns:
            datetime: Naive UTC datetime
        """
        if db_datetime is None:
            return None

        # If datetime is already naive, return as is
        if not hasattr(db_datetime, 'tzinfo') or db_datetime.tzinfo is None:
            return db_datetime

        # If timezone-aware, convert to naive UTC
        # PostgreSQL always returns in UTC, just remove tzinfo
        return db_datetime.replace(tzinfo=None)

    @staticmethod
    async def set_state(
        admin_id: int,
        state_type: str,
        state_data: Dict[str, Any],
        expiration_minutes: int = DEFAULT_EXPIRATION_MINUTES
    ) -> bool:
        """
        Set admin state in database with expiration.

        Creates or updates admin state with:
        - State type and associated data
        - Automatic expiration time
        - Timezone-aware timestamps

        Args:
            admin_id: Admin's Telegram ID
            state_type: Type of state to set
            state_data: Associated state data
            expiration_minutes: Minutes until state expires

        Returns:
            bool: True if state was set successfully
        """
        try:
            # Создаем naive UTC datetime для expires_at
            expires_at = AdminStateManager._get_utc_now(
            ) + timedelta(minutes=expiration_minutes)

            logger.info(
                f"Setting state for admin {admin_id}: {state_type} (expires in {expiration_minutes}min)")
            logger.debug(f"Expires at (naive UTC): {expires_at}")

            async with async_session() as session:
                existing = await session.get(AdminState, admin_id)

                if existing:
                    existing.state_type = state_type
                    existing.state_data = state_data
                    existing.expires_at = expires_at
                    logger.info(f"Updated state for admin {admin_id}")
                else:
                    new_state = AdminState(
                        admin_id=admin_id,
                        state_type=state_type,
                        state_data=state_data,
                        expires_at=expires_at
                    )
                    session.add(new_state)
                    logger.info(f"Created state for admin {admin_id}")

                await session.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to set admin state: {e}")
            return False

    @staticmethod
    async def get_state(admin_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve admin state from database with expiration check.

        Features:
        - Automatic expiration checking
        - Timezone conversion
        - State cleanup on expiration
        - Comprehensive error handling

        Args:
            admin_id: Admin's Telegram ID

        Returns:
            Optional[Dict[str, Any]]: State data if valid, None if expired/not found
        """
        try:
            async with async_session() as session:
                state = await session.get(AdminState, admin_id)

                if not state:
                    return None

                # Конвертируем datetime из БД в naive UTC
                now_utc = AdminStateManager._get_utc_now()
                expires_at = AdminStateManager._convert_from_db(
                    state.expires_at)

                logger.debug(f"State check for admin {admin_id}:")
                logger.debug(f"  Now (naive UTC): {now_utc}")
                logger.debug(f"  Expires (from DB): {expires_at}")
                logger.debug(f"  Raw from DB: {state.expires_at}")

                # Проверяем истечение
                if now_utc > expires_at:
                    time_diff = now_utc - expires_at
                    logger.info(
                        f"State for admin {admin_id} expired {time_diff} ago, removing")
                    await session.delete(state)
                    await session.commit()
                    return None

                time_remaining = expires_at - now_utc
                logger.debug(
                    f"State for admin {admin_id} valid, expires in {time_remaining}")

                return {
                    'type': state.state_type,
                    'data': state.state_data,
                    'created_at': AdminStateManager._convert_from_db(state.created_at),
                    'expires_at': expires_at
                }

        except Exception as e:
            logger.error(f"Failed to get admin state: {e}")
            return None

    @staticmethod
    async def clear_state(admin_id: int) -> bool:
        """
        Remove admin state from database.

        Performs:
        - State deletion
        - Database cleanup
        - Error handling

        Args:
            admin_id: Admin's Telegram ID

        Returns:
            bool: True if state was cleared successfully
        """
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
        """
        Check if admin is in a specific state.

        Performs:
        - State validation
        - Expiration checking
        - Type matching
        - Error handling

        Args:
            admin_id: Admin's Telegram ID
            state_type: State type to check

        Returns:
            bool: True if admin is in specified state
        """
        try:
            state = await AdminStateManager.get_state(admin_id)
            result = state is not None and state['type'] == state_type

            logger.debug(
                f"Admin {admin_id} is_in_state({state_type}): {result}")
            if state:
                expires_in = state['expires_at'] - \
                    AdminStateManager._get_utc_now()
                logger.debug(f"  State expires in: {expires_in}")

            return result
        except Exception as e:
            logger.error(f"Error checking admin state: {e}")
            return False

    @staticmethod
    async def cleanup_expired_states() -> int:
        """
        Remove all expired states from database.

        Features:
        - Batch deletion
        - Automatic timezone handling
        - Performance optimization
        - Result tracking

        Returns:
            int: Number of states cleaned up
        """
        try:
            async with async_session() as session:
                from sqlalchemy import select, delete

                now_utc = AdminStateManager._get_utc_now()

                # Удаляем состояния где expires_at < now (PostgreSQL сам сконвертирует)
                stmt = delete(AdminState).where(
                    AdminState.expires_at < now_utc)

                result = await session.execute(stmt)
                await session.commit()

                cleaned_count = result.rowcount
                if cleaned_count > 0:
                    logger.info(
                        f"Cleaned up {cleaned_count} expired admin states")

                return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired states: {e}")
            return 0

    @staticmethod
    async def get_all_active_states() -> list[Dict[str, Any]]:
        """Get all active (non-expired) states."""
        try:
            async with async_session() as session:
                from sqlalchemy import select

                now_utc = AdminStateManager._get_utc_now()
                stmt = select(AdminState).where(
                    AdminState.expires_at > now_utc)

                result = await session.execute(stmt)
                states = result.scalars().all()

                return [
                    {
                        'admin_id': state.admin_id,
                        'type': state.state_type,
                        'data': state.state_data,
                        'created_at': AdminStateManager._convert_from_db(state.created_at),
                        'expires_at': AdminStateManager._convert_from_db(state.expires_at)
                    }
                    for state in states
                ]

        except Exception as e:
            logger.error(f"Failed to get all active states: {e}")
            return []
