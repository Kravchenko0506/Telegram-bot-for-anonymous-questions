"""
User States Model for Question Flow Control

Manages user states to prevent commands from being treated as questions
after user has already submitted a question.
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Boolean
from sqlalchemy.sql import func
from typing import Optional
from datetime import datetime, timedelta

from models.database import Base, async_session

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
                    return user_state.state
                return UserStateManager.STATE_IDLE
        except Exception:
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
                    user_state.state = state
                    if state == UserStateManager.STATE_QUESTION_SENT:
                        user_state.last_question_at = datetime.utcnow()
                        user_state.questions_count += 1
                else:
                    # Create new
                    user_state = UserState(
                        user_id=user_id,
                        state=state,
                        last_question_at=datetime.utcnow() if state == UserStateManager.STATE_QUESTION_SENT else None,
                        questions_count=1 if state == UserStateManager.STATE_QUESTION_SENT else 0
                    )
                    session.add(user_state)
                
                await session.commit()
                return True
                
        except Exception:
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
        return state in [UserStateManager.STATE_IDLE, UserStateManager.STATE_AWAITING_QUESTION]
    
    @staticmethod
    async def allow_new_question(user_id: int) -> bool:
        """
        Allow user to send new question (after clicking inline button).
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if successful
        """
        return await UserStateManager.set_user_state(user_id, UserStateManager.STATE_AWAITING_QUESTION)
    
    @staticmethod
    async def reset_to_idle(user_id: int) -> bool:
        """
        Reset user to idle state.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if successful
        """
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
        except Exception:
            return {
                'questions_count': 0,
                'last_question_at': None,
                'current_state': UserStateManager.STATE_IDLE,
                'member_since': None
            }