"""
Database Manager for Anonymous Questions Bot

Этот модуль управляет всеми операциями с базой данных SQLite.
Содержит функции для создания таблиц, добавления вопросов,
обновления статусов и получения статистики.

Database Schema:
- questions: хранит все вопросы с их статусами и ответами
- Поддерживает миграции схемы для будущих обновлений

Architecture Pattern: Repository Pattern
Все SQL-запросы инкапсулированы в функции для лучшей поддержки
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from contextlib import asynccontextmanager
import aiosqlite

from config import DB_PATH


# Setup module logger
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


@asynccontextmanager
async def get_db_connection():
    """
    Async context manager for database connections.
    
    Provides proper connection management with automatic cleanup.
    All database operations should use this context manager.
    
    Yields:
        aiosqlite.Connection: Database connection
        
    Raises:
        DatabaseError: If connection fails
    """
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            # Enable foreign key constraints
            await conn.execute("PRAGMA foreign_keys = ON")
            yield conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise DatabaseError(f"Failed to connect to database: {e}")


async def init_db() -> None:
    """
    Initialize database and create necessary tables.
    
    Creates the questions table if it doesn't exist.
    This function is idempotent - safe to call multiple times.
    
    Table Structure:
    - id: Primary key, auto-increment
    - user_id: Telegram user ID (для статистики, но не раскрывает анонимность)
    - question: Text of the question
    - answer: Admin's answer (NULL if not answered)
    - status: 'pending', 'answered', 'rejected'
    - created_at: Timestamp when question was created
    - answered_at: Timestamp when question was answered
    
    Raises:
        DatabaseError: If table creation fails
    """
    try:
        async with get_db_connection() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'answered', 'rejected')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    answered_at TIMESTAMP
                )
            """)
            
            # Create index for better query performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_questions_status 
                ON questions(status)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_questions_created_at 
                ON questions(created_at)
            """)
            
            await conn.commit()
            logger.info("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(f"Database initialization failed: {e}")


async def add_question(user_id: int, question: str) -> int:
    """
    Add a new question to the database.
    
    Args:
        user_id (int): Telegram user ID of the questioner
        question (str): The question text
        
    Returns:
        int: ID of the created question
        
    Raises:
        DatabaseError: If question creation fails
        ValueError: If question is empty or too long
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    
    question = question.strip()
    
    try:
        async with get_db_connection() as conn:
            cursor = await conn.execute(
                "INSERT INTO questions (user_id, question) VALUES (?, ?)",
                (user_id, question)
            )
            await conn.commit()
            
            question_id = cursor.lastrowid
            logger.info(f"Question {question_id} added for user {user_id}")
            return question_id
            
    except Exception as e:
        logger.error(f"Failed to add question: {e}")
        raise DatabaseError(f"Failed to save question: {e}")


async def get_pending_questions() -> List[Dict]:
    """
    Get all pending (unanswered) questions.
    
    Returns:
        List[Dict]: List of pending questions with their details
        Each dict contains: id, user_id, question, created_at
        
    Raises:
        DatabaseError: If query fails
    """
    try:
        async with get_db_connection() as conn:
            cursor = await conn.execute("""
                SELECT id, user_id, question, created_at
                FROM questions 
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """)
            
            rows = await cursor.fetchall()
            
            # Convert to list of dictionaries for easier handling
            questions = []
            for row in rows:
                questions.append({
                    'id': row[0],
                    'user_id': row[1],
                    'question': row[2],
                    'created_at': row[3]
                })
            
            logger.info(f"Retrieved {len(questions)} pending questions")
            return questions
            
    except Exception as e:
        logger.error(f"Failed to get pending questions: {e}")
        raise DatabaseError(f"Failed to retrieve questions: {e}")


async def answer_question(question_id: int, answer: str) -> bool:
    """
    Add an answer to a question and mark it as answered.
    
    Args:
        question_id (int): ID of the question to answer
        answer (str): The answer text
        
    Returns:
        bool: True if question was successfully answered
        
    Raises:
        DatabaseError: If update fails
        ValueError: If answer is empty
    """
    if not answer or not answer.strip():
        raise ValueError("Answer cannot be empty")
    
    answer = answer.strip()
    
    try:
        async with get_db_connection() as conn:
            cursor = await conn.execute("""
                UPDATE questions 
                SET answer = ?, status = 'answered', answered_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
            """, (answer, question_id))
            
            await conn.commit()
            
            # Check if any row was updated
            if cursor.rowcount == 0:
                logger.warning(f"No pending question found with ID {question_id}")
                return False
            
            logger.info(f"Question {question_id} answered successfully")
            return True
            
    except Exception as e:
        logger.error(f"Failed to answer question {question_id}: {e}")
        raise DatabaseError(f"Failed to save answer: {e}")


async def get_question_by_id(question_id: int) -> Optional[Dict]:
    """
    Get a specific question by its ID.
    
    Args:
        question_id (int): ID of the question
        
    Returns:
        Optional[Dict]: Question details or None if not found
        Dict contains: id, user_id, question, answer, status, created_at, answered_at
        
    Raises:
        DatabaseError: If query fails
    """
    try:
        async with get_db_connection() as conn:
            cursor = await conn.execute("""
                SELECT id, user_id, question, answer, status, created_at, answered_at
                FROM questions 
                WHERE id = ?
            """, (question_id,))
            
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'user_id': row[1],
                'question': row[2],
                'answer': row[3],
                'status': row[4],
                'created_at': row[5],
                'answered_at': row[6]
            }
            
    except Exception as e:
        logger.error(f"Failed to get question {question_id}: {e}")
        raise DatabaseError(f"Failed to retrieve question: {e}")


async def reject_question(question_id: int) -> bool:
    """
    Mark a question as rejected.
    
    Args:
        question_id (int): ID of the question to reject
        
    Returns:
        bool: True if question was successfully rejected
        
    Raises:
        DatabaseError: If update fails
    """
    try:
        async with get_db_connection() as conn:
            cursor = await conn.execute("""
                UPDATE questions 
                SET status = 'rejected'
                WHERE id = ? AND status = 'pending'
            """, (question_id,))
            
            await conn.commit()
            
            if cursor.rowcount == 0:
                logger.warning(f"No pending question found with ID {question_id}")
                return False
            
            logger.info(f"Question {question_id} rejected")
            return True
            
    except Exception as e:
        logger.error(f"Failed to reject question {question_id}: {e}")
        raise DatabaseError(f"Failed to reject question: {e}")


async def get_statistics() -> Dict[str, int]:
    """
    Get comprehensive statistics about questions.
    
    Returns:
        Dict[str, int]: Statistics dictionary with counts
        Keys: total, pending, answered, rejected, today
        
    Raises:
        DatabaseError: If query fails
    """
    try:
        async with get_db_connection() as conn:
            # Get total counts by status
            cursor = await conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'answered' THEN 1 ELSE 0 END) as answered,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
                FROM questions
            """)
            
            row = await cursor.fetchone()
            
            # Get questions from today
            today_cursor = await conn.execute("""
                SELECT COUNT(*) 
                FROM questions 
                WHERE DATE(created_at) = DATE('now')
            """)
            
            today_count = await today_cursor.fetchone()
            
            stats = {
                'total': row[0] or 0,
                'pending': row[1] or 0,
                'answered': row[2] or 0,
                'rejected': row[3] or 0,
                'today': today_count[0] or 0
            }
            
            logger.info(f"Statistics retrieved: {stats}")
            return stats
            
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise DatabaseError(f"Failed to retrieve statistics: {e}")


async def export_all_questions() -> List[Dict]:
    """
    Export all questions for backup or analysis.
    
    Returns:
        List[Dict]: All questions with full details
        
    Raises:
        DatabaseError: If query fails
    """
    try:
        async with get_db_connection() as conn:
            cursor = await conn.execute("""
                SELECT id, user_id, question, answer, status, created_at, answered_at
                FROM questions 
                ORDER BY created_at DESC
            """)
            
            rows = await cursor.fetchall()
            
            questions = []
            for row in rows:
                questions.append({
                    'id': row[0],
                    'user_id': row[1],
                    'question': row[2],
                    'answer': row[3],
                    'status': row[4],
                    'created_at': row[5],
                    'answered_at': row[6]
                })
            
            logger.info(f"Exported {len(questions)} questions")
            return questions
            
    except Exception as e:
        logger.error(f"Failed to export questions: {e}")
        raise DatabaseError(f"Failed to export questions: {e}")


# Database maintenance functions
async def cleanup_old_rejected_questions(days_old: int = 30) -> int:
    """
    Clean up old rejected questions to keep database size manageable.
    
    Args:
        days_old (int): Delete rejected questions older than this many days
        
    Returns:
        int: Number of questions deleted
        
    Raises:
        DatabaseError: If cleanup fails
    """
    try:
        async with get_db_connection() as conn:
            cursor = await conn.execute("""
                DELETE FROM questions 
                WHERE status = 'rejected' 
                AND created_at < datetime('now', '-{} days')
            """.format(days_old))
            
            await conn.commit()
            
            deleted_count = cursor.rowcount
            logger.info(f"Cleaned up {deleted_count} old rejected questions")
            return deleted_count
            
    except Exception as e:
        logger.error(f"Failed to cleanup old questions: {e}")
        raise DatabaseError(f"Failed to cleanup database: {e}")
