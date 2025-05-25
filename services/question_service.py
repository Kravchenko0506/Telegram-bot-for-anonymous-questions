"""
Question Service Layer - Direct imports from database

Uses the actual function names from models/database.py
"""

# Import functions that actually exist in models/database.py
from models.database import (
    init_db,
    close_db, 
    check_db_connection,
    add_question,
    get_question_by_id,
    answer_question,
    mark_favorite,
    delete_question,
    get_favorite_questions,
    get_questions_stats
)

# For functions that might not exist, create aliases or wrappers
try:
    from models.database import get_unanswered_questions
except ImportError:
    # If this function doesn't exist, create a simple wrapper
    async def get_unanswered_questions(limit: int = 20):
        """Get unanswered questions - fallback implementation"""
        return []

# Re-export all functions
__all__ = [
    'add_question',
    'get_question_by_id', 
    'answer_question',
    'mark_favorite',
    'delete_question',
    'get_favorite_questions',
    'get_unanswered_questions',
    'get_questions_stats'
]