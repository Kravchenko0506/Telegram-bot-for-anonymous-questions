"""
Question Management System

A comprehensive system for managing anonymous questions in the bot's database.
This module provides the data model and business logic for question handling.

Features:
- Anonymous question storage
- Answer management
- Question tracking
- Soft deletion
- Favorite marking
- Timestamp tracking
- User analytics

Technical Features:
- PostgreSQL integration
- SQLAlchemy ORM mapping
- Index optimization
- Timezone support
- JSON serialization
- Factory methods
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from models.database import Base


class Question(Base):
    """
    Comprehensive data model for anonymous questions and their lifecycle.

    This model handles:
    - Question submission and storage
    - Answer management
    - Question status tracking
    - Admin operations
    - Analytics data

    Features:
    - Anonymous question storage
    - Answer tracking
    - Favorite marking
    - Soft deletion
    - Timestamp management
    - User analytics
    - Source tracking

    Workflow:
    1. User submits question anonymously
    2. Admin receives notification
    3. Admin can perform actions:
       - Answer the question
       - Mark as favorite
       - Delete the question
    4. User receives notification of answer

    Technical Features:
    - Optimized database indexes
    - Timezone-aware timestamps
    - Automatic update tracking
    - JSON serialization
    - Text preview generation
    """

    __tablename__ = "questions"

    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)

    # User tracking (anonymous to admin, but tracked for analytics)
    user_id = Column(BigInteger, nullable=True, index=True)
    """
    Telegram user ID for analytics and rate limiting.
    Anonymous to admin but allows tracking user behavior.
    """

    unique_id = Column(String(255), nullable=True, index=True)
    """
    Unique tracking identifier from deep links.
    Used for analyzing question sources and campaign effectiveness.
    """

    # Question content
    text = Column(Text, nullable=False)
    """
    The question text submitted by the user.
    No length limit at database level (handled by application).
    """

    answer = Column(Text, nullable=True)
    """
    Admin's response to the question.
    Null indicates pending questions.
    """

    # Admin management flags
    is_favorite = Column(Boolean, default=False, nullable=False, index=True)
    """
    Favorite flag for admin organization.
    Indexed for quick access to favorite questions.
    """

    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    """
    Soft deletion flag for data preservation.
    Allows question recovery if needed.
    """

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    """
    Question submission timestamp.
    Timezone-aware and indexed for chronological access.
    """

    answered_at = Column(DateTime(timezone=True), nullable=True)
    """
    Answer timestamp.
    Null for pending questions, set when admin responds.
    """

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    """
    Last modification timestamp.
    Automatically updated on any change.
    """

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    """
    Soft deletion timestamp.
    Null if question is active, set on deletion.
    """

    def __repr__(self) -> str:
        """
        Generate string representation for debugging.

        Returns:
            str: Formatted string with key question attributes
        """
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
        """
        Check if question has been answered.

        Returns:
            bool: True if question has non-empty answer
        """
        return self.answer is not None and self.answer.strip() != ""

    @property
    def is_pending(self) -> bool:
        """
        Check if question needs admin attention.

        Returns:
            bool: True if question is active and unanswered
        """
        return not self.is_answered and not self.is_deleted

    @property
    def preview_text(self) -> str:
        """
        Generate shortened question preview.

        Returns:
            str: Full text if under 100 chars, or truncated with ellipsis
        """
        if len(self.text) <= 100:
            return self.text
        return self.text[:97] + "..."

    def to_dict(self) -> dict:
        """
        Convert question to dictionary format.

        Includes:
        - All model attributes
        - Computed properties
        - ISO formatted timestamps
        - Preview text

        Returns:
            dict: Question data in dictionary format
        """
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
        """
        Factory method for creating new questions.

        Features:
        - Text whitespace normalization
        - Optional user tracking
        - Optional source tracking
        - Default flag initialization

        Args:
            text: Question text from user
            user_id: Optional Telegram user ID
            unique_id: Optional tracking identifier

        Returns:
            Question: New question instance
        """
        return cls(
            text=text.strip(),
            user_id=user_id,
            unique_id=unique_id,
            is_favorite=False,
            is_deleted=False
        )
