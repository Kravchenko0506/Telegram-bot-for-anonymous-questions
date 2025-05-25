"""
Question Model for Anonymous Questions Bot

Final unified model for PostgreSQL with asyncpg.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from models.database import Base


class Question(Base):
    """
    Model for storing anonymous questions and their metadata.
    
    Complete workflow support:
    1. User sends question via unique link
    2. Admin receives notification with action buttons
    3. Admin can answer, favorite, or delete
    4. User receives answer if provided
    """
    
    __tablename__ = "questions"

    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # User tracking (anonymous to admin, but tracked for analytics)
    user_id = Column(BigInteger, nullable=True, index=True)
    """Telegram user ID - allows tracking but maintains anonymity"""
    
    unique_id = Column(String(255), nullable=True, index=True)
    """Unique identifier from start parameter for tracking question sources"""
    
    # Question content
    text = Column(Text, nullable=False)
    """The actual question text from user"""
    
    answer = Column(Text, nullable=True)
    """Admin's answer - NULL until admin responds"""
    
    # Admin management flags
    is_favorite = Column(Boolean, default=False, nullable=False, index=True)
    """Admin can mark questions as favorites for easy access"""
    
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    """Soft delete flag - allows recovery if needed"""
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )
    """When the question was first submitted"""
    
    answered_at = Column(DateTime(timezone=True), nullable=True)
    """When admin provided an answer - NULL if not answered"""
    
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    """Last time any field was modified"""
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    """When question was soft deleted - NULL if not deleted"""

    def __repr__(self) -> str:
        """String representation for debugging and logging."""
        return (
            f"<Question(id={self.id}, "
            f"user_id={self.user_id}, "
            f"unique_id='{self.unique_id}', "
            f"text='{self.text[:30]}...', "
            f"answered={self.answer is not None}, "
            f"favorite={self.is_favorite}, "
            f"deleted={self.is_deleted})>"
        )
    
    @property
    def is_answered(self) -> bool:
        """Check if question has been answered by admin."""
        return self.answer is not None and self.answer.strip() != ""
    
    @property
    def is_pending(self) -> bool:
        """Check if question is waiting for admin response."""
        return not self.is_answered and not self.is_deleted
    
    @property
    def preview_text(self) -> str:
        """Get shortened text for admin previews."""
        if len(self.text) <= 100:
            return self.text
        return self.text[:97] + "..."
    
    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'unique_id': self.unique_id,
            'text': self.text,
            'answer': self.answer,
            'is_favorite': self.is_favorite,
            'is_deleted': self.is_deleted,
            'is_answered': self.is_answered,
            'is_pending': self.is_pending,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'preview_text': self.preview_text
        }
    
    @classmethod
    def create_new(
        cls, 
        text: str, 
        user_id: Optional[int] = None, 
        unique_id: Optional[str] = None
    ) -> 'Question':
        """Factory method for creating new questions."""
        return cls(
            text=text.strip(),
            user_id=user_id,
            unique_id=unique_id,
            is_favorite=False,
            is_deleted=False
        )