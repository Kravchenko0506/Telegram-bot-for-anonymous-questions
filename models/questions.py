"""Question model."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.sql import func
from typing import Optional
from models.database import Base

class Question(Base):
    """Model for anonymous questions with answers, favorites, and soft deletion."""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=True, index=True)
    unique_id = Column(String(255), nullable=True, index=True)

    text = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)

    is_favorite = Column(Boolean, default=False, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime, server_default=func.now(),
                        nullable=False, index=True)
    answered_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(),
                        onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, answered={self.is_answered}, deleted={self.is_deleted})>"

    @property
    def is_answered(self) -> bool:
        """Check if question has been answered."""
        return self.answer is not None and self.answer.strip() != ""

    @property
    def is_pending(self) -> bool:
        """Check if question needs admin attention."""
        return not self.is_answered and not self.is_deleted

    @property
    def preview_text(self) -> str:
        """Get shortened preview (max 100 chars)."""
        return self.text if len(self.text) <= 100 else self.text[:97] + "..."

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
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
