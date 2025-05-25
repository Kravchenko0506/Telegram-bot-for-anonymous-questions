# models/question.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from models.database import Base

class Question(Base):
    """
    Модель для хранения анонимных вопросов.
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)                 # Сам вопрос
    created_at = Column(DateTime, server_default=func.now())
    is_favorite = Column(Boolean, default=False)        # Пометка "избранное"
    is_deleted = Column(Boolean, default=False)         # Если удалено
    answer = Column(Text, nullable=True)                # Ответ админа (если был)
    #user_id = Column(Integer, nullable=True)            # Можно хранить Telegram user_id, если нужно

    def __repr__(self):
        return f"<Question id={self.id} text={self.text[:15]}... favorite={self.is_favorite}>"
