"""
Prevents spam and abuse by limiting user actions.
"""

from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from config import (
    RATE_LIMIT_QUESTIONS_PER_HOUR,
    RATE_LIMIT_COOLDOWN_SECONDS,
    ERROR_RATE_LIMIT,
    ADMIN_ID
)
from utils.logger import get_bot_logger

logger = get_bot_logger()


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware to limit user actions and prevent spam.
    
    Features:
    - Limits questions per hour
    - Enforces cooldown between messages (except first question)
    - Tracks user violations
    - Exempt admin from limits
    """
    
    def __init__(
        self,
        questions_per_hour: int = RATE_LIMIT_QUESTIONS_PER_HOUR,
        cooldown_seconds: int = RATE_LIMIT_COOLDOWN_SECONDS
    ):
        self.questions_per_hour = questions_per_hour
        self.cooldown_seconds = cooldown_seconds
        
        # Storage for tracking
        self.user_questions: Dict[int, list[datetime]] = defaultdict(list)
        self.user_last_message: Dict[int, datetime] = {}
        self.user_violations: Dict[int, int] = defaultdict(int)
        
        # Track when user sent their last question (not just any message)
        self.user_last_question: Dict[int, datetime] = {}
        
        # Track if user has sent their first question
        self.user_has_sent_first_question: set[int] = set()
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """Process message through rate limiter."""
        
        # Skip if not a message
        if not isinstance(event, Message):
            return await handler(event, data)
        
        user = event.from_user
        if not user:
            return await handler(event, data)
        
        user_id = user.id
        
        # Admin bypass
        if user_id == ADMIN_ID:
            return await handler(event, data)
        
        # Skip rate limiting for commands
        if event.text and event.text.startswith('/'):
            return await handler(event, data)
        
        # Check rate limits
        now = datetime.now()
        
        # Check cooldown only for consecutive questions
        if await self._is_sending_question(user_id):
            # Check if this is user's first question ever
            is_first_question = user_id not in self.user_has_sent_first_question
            
            # Skip cooldown for first question
            if not is_first_question:
                if not await self._check_question_cooldown(user_id, now):
                    remaining = self._get_cooldown_remaining(user_id)
                    await event.answer(
                        ERROR_RATE_LIMIT.format(seconds=remaining)
                    )
                    logger.warning(f"Rate limit cooldown hit for user {user_id}")
                    return  # Don't process further
            else:
                logger.info(f"First question from user {user_id} - skipping cooldown")
            
            # Check hourly limit for questions
            if not await self._check_hourly_limit(user_id, now):
                await event.answer(
                    f"❌ Вы превысили лимит вопросов ({self.questions_per_hour} в час). "
                    f"Попробуйте позже."
                )
                logger.warning(f"Rate limit hourly hit for user {user_id}")
                return  # Don't process further
            
            # Mark this as a question timestamp
            self.user_last_question[user_id] = now
            
            # Mark that user has sent their first question
            if is_first_question:
                self.user_has_sent_first_question.add(user_id)
        
        # Update last message time
        self.user_last_message[user_id] = now
        
        # Process the message
        return await handler(event, data)
    
    async def _is_sending_question(self, user_id: int) -> bool:
        """Check if user is sending a question (not in answer mode)."""
        # Import here to avoid circular imports
        from models.user_states import UserStateManager
        
        # Check if user can send a question based on their state
        can_send = await UserStateManager.can_send_question(user_id)
        return can_send
    
    async def _check_question_cooldown(self, user_id: int, now: datetime) -> bool:
        """Check if user is within cooldown period for questions."""
        last_question = self.user_last_question.get(user_id)
        
        if not last_question:
            return True
        
        time_passed = (now - last_question).total_seconds()
        return time_passed >= self.cooldown_seconds
    
    def _get_cooldown_remaining(self, user_id: int) -> int:
        """Get remaining cooldown seconds."""
        last_question = self.user_last_question.get(user_id)
        if not last_question:
            return 0
        
        now = datetime.now()
        time_passed = (now - last_question).total_seconds()
        remaining = self.cooldown_seconds - time_passed
        
        return max(0, int(remaining))
    
    async def _check_hourly_limit(self, user_id: int, now: datetime) -> bool:
        """Check if user exceeded hourly question limit."""
        # Clean old entries
        hour_ago = now - timedelta(hours=1)
        self.user_questions[user_id] = [
            q_time for q_time in self.user_questions[user_id]
            if q_time > hour_ago
        ]
        
        # Check limit
        questions_count = len(self.user_questions[user_id])
        if questions_count >= self.questions_per_hour:
            self.user_violations[user_id] += 1
            return False
        
        # Add current question
        self.user_questions[user_id].append(now)
        return True
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get rate limit stats for user."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Count recent questions
        recent_questions = len([
            q for q in self.user_questions.get(user_id, [])
            if q > hour_ago
        ])
        
        # Get cooldown status
        cooldown_remaining = self._get_cooldown_remaining(user_id)
        
        # Check if user has sent first question
        has_sent_first = user_id in self.user_has_sent_first_question
        
        return {
            'questions_last_hour': recent_questions,
            'questions_limit': self.questions_per_hour,
            'cooldown_remaining': cooldown_remaining,
            'violations': self.user_violations.get(user_id, 0),
            'has_sent_first_question': has_sent_first
        }
    
    async def cleanup_old_data(self):
        """Clean up old tracking data to prevent memory leaks."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean questions older than 1 hour
        for user_id in list(self.user_questions.keys()):
            self.user_questions[user_id] = [
                q_time for q_time in self.user_questions[user_id]
                if q_time > hour_ago
            ]
            
            # Remove empty entries
            if not self.user_questions[user_id]:
                del self.user_questions[user_id]
        
        # Clean old last message times (older than 1 hour)
        for user_id in list(self.user_last_message.keys()):
            if self.user_last_message[user_id] < hour_ago:
                del self.user_last_message[user_id]
        
        # Clean old last question times
        for user_id in list(self.user_last_question.keys()):
            if self.user_last_question[user_id] < hour_ago:
                del self.user_last_question[user_id]
        
        logger.debug(f"Cleaned up rate limit data. Active users: {len(self.user_questions)}")


class CallbackRateLimitMiddleware(BaseMiddleware):
    """
    Rate limiter for callback queries (button clicks).
    Prevents button spam but is more lenient than message rate limiting.
    """
    
    def __init__(self, cooldown_seconds: int = 1):
        self.cooldown_seconds = cooldown_seconds
        self.user_last_callback: Dict[int, datetime] = {}
        
        # Don't rate limit these callback data patterns
        self.exempt_patterns = [
            'ask_another_question',  # Allow asking another question
            'cancel',  # Allow cancellations
        ]
    
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Process callback through rate limiter."""
        
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)
        
        user_id = event.from_user.id
        
        # Admin bypass
        if user_id == ADMIN_ID:
            return await handler(event, data)
        
        # Check if callback is exempt
        if event.data and any(pattern in event.data for pattern in self.exempt_patterns):
            return await handler(event, data)
        
        # Check cooldown
        now = datetime.now()
        last_callback = self.user_last_callback.get(user_id)
        
        if last_callback:
            time_passed = (now - last_callback).total_seconds()
            if time_passed < self.cooldown_seconds:
                await event.answer("⏳ Слишком быстро! Подождите секунду.", show_alert=False)
                return  # Don't process
        
        # Update last callback time
        self.user_last_callback[user_id] = now
        
        # Process the callback
        return await handler(event, data)