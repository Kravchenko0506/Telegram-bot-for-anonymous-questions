"""
User States Model for Question Flow Control

Manages user states to prevent commands from being treated as questions
after user has already submitted a question.
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, select, and_
from sqlalchemy.sql import func
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from models.database import Base, async_session
from utils.logger import get_bot_logger

logger = get_bot_logger()


class UserState(Base):
    """
    Model for tracking user states in the bot.
    
    Prevents commands from being treated as questions after user
    has submitted a question. User can ask new question only via inline button.
    """
    
    __tablename__ = "user_states"

    # User identification
    user_id = Column(BigInteger, primary_key=True)
    """Telegram user ID"""
    
    # State management
    state = Column(String(50), nullable=False, default="idle")
    """Current user state: 'idle', 'question_sent', 'awaiting_question'"""
    
    last_question_at = Column(DateTime(timezone=True), nullable=True)
    """When user last sent a question"""
    
    questions_count = Column(BigInteger, default=0, nullable=False)
    """Total questions sent by this user"""
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<UserState(user_id={self.user_id}, state='{self.state}', questions={self.questions_count})>"


class UserStateManager:
    """Helper class for managing user states."""
    
    # State constants
    STATE_IDLE = "idle"
    STATE_QUESTION_SENT = "question_sent"
    STATE_AWAITING_QUESTION = "awaiting_question"
    
    @staticmethod
    async def get_user_state(user_id: int) -> str:
        """
        Get current user state.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            str: Current state or 'idle' if not found
        """
        try:
            async with async_session() as session:
                user_state = await session.get(UserState, user_id)
                if user_state:
                    logger.debug(f"User {user_id} current state: {user_state.state}")
                    return user_state.state
                logger.debug(f"User {user_id} not found, returning idle state")
                return UserStateManager.STATE_IDLE
        except Exception as e:
            logger.error(f"Error getting user state for {user_id}: {e}")
            return UserStateManager.STATE_IDLE
    
    @staticmethod
    async def set_user_state(user_id: int, state: str) -> bool:
        """
        Set user state.
        
        Args:
            user_id: Telegram user ID
            state: New state
            
        Returns:
            bool: True if successful
        """
        try:
            async with async_session() as session:
                user_state = await session.get(UserState, user_id)
                
                if user_state:
                    # Update existing
                    old_state = user_state.state
                    user_state.state = state
                    if state == UserStateManager.STATE_QUESTION_SENT:
                        user_state.last_question_at = datetime.utcnow()
                        user_state.questions_count += 1
                    logger.info(f"User {user_id} state changed: {old_state} -> {state}")
                else:
                    # Create new
                    user_state = UserState(
                        user_id=user_id,
                        state=state,
                        last_question_at=datetime.utcnow() if state == UserStateManager.STATE_QUESTION_SENT else None,
                        questions_count=1 if state == UserStateManager.STATE_QUESTION_SENT else 0
                    )
                    session.add(user_state)
                    logger.info(f"User {user_id} state created: {state}")
                
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting user state for {user_id}: {e}")
            return False
    
    @staticmethod
    async def can_send_question(user_id: int) -> bool:
        """
        Check if user can send a question.
        
        Users can send questions if:
        - They are in 'idle' state (first time or after clicking "ask another")
        - They are in 'awaiting_question' state (clicked "ask another")
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user can send question
        """
        state = await UserStateManager.get_user_state(user_id)
        can_send = state in [UserStateManager.STATE_IDLE, UserStateManager.STATE_AWAITING_QUESTION]
        logger.debug(f"User {user_id} can_send_question: {can_send} (state: {state})")
        return can_send
    
    @staticmethod
    async def allow_new_question(user_id: int) -> bool:
        """
        Allow user to send new question (after clicking inline button).
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Allowing new question for user {user_id}")
        success = await UserStateManager.set_user_state(user_id, UserStateManager.STATE_AWAITING_QUESTION)
        if success:
            logger.info(f"User {user_id} can now send a new question")
        else:
            logger.error(f"Failed to allow new question for user {user_id}")
        return success
    
    @staticmethod
    async def reset_to_idle(user_id: int) -> bool:
        """
        Reset user to idle state.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Resetting user {user_id} to idle state")
        return await UserStateManager.set_user_state(user_id, UserStateManager.STATE_IDLE)
    
    @staticmethod
    async def get_user_stats(user_id: int) -> dict:
        """
        Get user statistics.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            dict: User statistics
        """
        try:
            async with async_session() as session:
                user_state = await session.get(UserState, user_id)
                if user_state:
                    return {
                        'questions_count': user_state.questions_count,
                        'last_question_at': user_state.last_question_at,
                        'current_state': user_state.state,
                        'member_since': user_state.created_at
                    }
                return {
                    'questions_count': 0,
                    'last_question_at': None,
                    'current_state': UserStateManager.STATE_IDLE,
                    'member_since': None
                }
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return {
                'questions_count': 0,
                'last_question_at': None,
                'current_state': UserStateManager.STATE_IDLE,
                'member_since': None
            }
    
    @staticmethod
    async def cleanup_old_states(hours: int = 24) -> int:
        """
        Clean up old user states.
        
        Resets states to 'idle' for users who haven't been active for specified hours.
        
        Args:
            hours: Number of hours after which to reset state
            
        Returns:
            int: Number of states cleaned
        """
        try:
            async with async_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                
                # Find users with old states that aren't idle
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
                    logger.info(
                        f"Resetting old state for user {user_state.user_id}: "
                        f"{user_state.state} -> idle (last updated: {user_state.updated_at})"
                    )
                    user_state.state = UserStateManager.STATE_IDLE
                    count += 1
                
                await session.commit()
                
                if count > 0:
                    logger.info(f"Cleaned up {count} old user states")
                
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up old user states: {e}")
            return 0
    
    @staticmethod
    async def auto_reset_if_needed(user_id: int, timeout_minutes: int = 30) -> bool:
        """
        Auto-reset user state if it's been too long since last activity.
        
        Args:
            user_id: Telegram user ID
            timeout_minutes: Minutes after which to reset state
            
        Returns:
            bool: True if state was reset
        """
        try:
            async with async_session() as session:
                user_state = await session.get(UserState, user_id)
                
                if not user_state or user_state.state == UserStateManager.STATE_IDLE:
                    return False
                
                # Check if state is old
                time_since_update = datetime.utcnow() - user_state.updated_at
                if time_since_update > timedelta(minutes=timeout_minutes):
                    logger.info(
                        f"Auto-resetting old state for user {user_id}: "
                        f"{user_state.state} -> idle (inactive for {time_since_update})"
                    )
                    user_state.state = UserStateManager.STATE_IDLE
                    await session.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error in auto-reset for user {user_id}: {e}")
            return False