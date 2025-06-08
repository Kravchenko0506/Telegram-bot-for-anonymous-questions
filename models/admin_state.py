"""
Admin State Model for Database Storage

"""

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from models.database import Base, async_session


class AdminState(Base):
    """
    Model for storing admin states in database.
    
    Replaces in-memory storage to persist states across bot restarts.
    """
    
    __tablename__ = "admin_states"

    # Primary key
    admin_id = Column(BigInteger, primary_key=True)
    """Admin's Telegram user ID"""
    
    # State information
    state_type = Column(String(50), nullable=False)
    """Type of state: 'answering_question', etc."""
    
    state_data = Column(JSON, nullable=False, default=dict)
    """JSON data for the state (question_id, etc.)"""
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    """When this state was created"""
    
    expires_at = Column(DateTime(timezone=True), nullable=False)
    """When this state should expire"""
    
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    """Last update time"""

    def __repr__(self) -> str:
        return f"<AdminState(admin_id={self.admin_id}, type='{self.state_type}', data={self.state_data})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if state has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def time_remaining(self) -> timedelta:
        """Get time remaining before expiration."""
        return self.expires_at - datetime.utcnow()


class AdminStateManager:
    """Manager class for admin states with database backend."""
    
    # State types
    STATE_ANSWERING = "answering_question"
    
    # Default expiration time (10 minutes)
    DEFAULT_EXPIRATION_MINUTES = 10
    
    @staticmethod
    async def set_state(
        admin_id: int, 
        state_type: str, 
        state_data: Dict[str, Any],
        expiration_minutes: int = DEFAULT_EXPIRATION_MINUTES
    ) -> bool:
        """
        Set admin state in database.
        
        Args:
            admin_id: Admin's Telegram ID
            state_type: Type of state
            state_data: State data as dictionary
            expiration_minutes: Minutes until expiration
            
        Returns:
            bool: Success status
        """
        try:
            async with async_session() as session:
                # Check if state exists
                existing = await session.get(AdminState, admin_id)
                
                expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)
                
                if existing:
                    # Update existing state
                    existing.state_type = state_type
                    existing.state_data = state_data
                    existing.expires_at = expires_at
                else:
                    # Create new state
                    new_state = AdminState(
                        admin_id=admin_id,
                        state_type=state_type,
                        state_data=state_data,
                        expires_at=expires_at
                    )
                    session.add(new_state)
                
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to set admin state: {e}")
            return False
    
    @staticmethod
    async def get_state(admin_id: int) -> Optional[Dict[str, Any]]:
        """
        Get admin state from database.
        
        Args:
            admin_id: Admin's Telegram ID
            
        Returns:
            State data or None if not found/expired
        """
        try:
            async with async_session() as session:
                state = await session.get(AdminState, admin_id)
                
                if not state:
                    return None
                
                # Check expiration
                if state.is_expired:
                    # Delete expired state
                    await session.delete(state)
                    await session.commit()
                    return None
                
                return {
                    'type': state.state_type,
                    'data': state.state_data,
                    'created_at': state.created_at,
                    'expires_at': state.expires_at
                }
                
        except Exception as e:
            logger.error(f"Failed to get admin state: {e}")
            return None
    
    @staticmethod
    async def clear_state(admin_id: int) -> bool:
        """
        Clear admin state from database.
        
        Args:
            admin_id: Admin's Telegram ID
            
        Returns:
            bool: Success status
        """
        try:
            async with async_session() as session:
                state = await session.get(AdminState, admin_id)
                
                if state:
                    await session.delete(state)
                    await session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear admin state: {e}")
            return False
    
    @staticmethod
    async def is_in_state(admin_id: int, state_type: str) -> bool:
        """
        Check if admin is in specific state.
        
        Args:
            admin_id: Admin's Telegram ID
            state_type: State type to check
            
        Returns:
            bool: True if in specified state
        """
        state = await AdminStateManager.get_state(admin_id)
        return state is not None and state['type'] == state_type
    
    @staticmethod
    async def cleanup_expired_states() -> int:
        """
        Clean up all expired states from database.
        
        Returns:
            int: Number of states cleaned
        """
        try:
            async with async_session() as session:
                from sqlalchemy import select, delete
                
                # Find expired states
                stmt = delete(AdminState).where(
                    AdminState.expires_at < datetime.utcnow()
                )
                
                result = await session.execute(stmt)
                await session.commit()
                
                return result.rowcount
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired states: {e}")
            return 0
    
    @staticmethod
    async def get_all_active_states() -> list[Dict[str, Any]]:
        """
        Get all active (non-expired) states.
        
        Returns:
            List of active states
        """
        try:
            async with async_session() as session:
                from sqlalchemy import select
                
                stmt = select(AdminState).where(
                    AdminState.expires_at > datetime.utcnow()
                )
                
                result = await session.execute(stmt)
                states = result.scalars().all()
                
                return [
                    {
                        'admin_id': state.admin_id,
                        'type': state.state_type,
                        'data': state.state_data,
                        'expires_at': state.expires_at
                    }
                    for state in states
                ]
                
        except Exception as e:
            logger.error(f"Failed to get all active states: {e}")
            return []


# Import logger
from utils.logger import get_admin_logger
logger = get_admin_logger()