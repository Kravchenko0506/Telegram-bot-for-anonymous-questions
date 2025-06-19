"""
Rate Limiting System

A comprehensive rate limiting system that prevents spam and abuse by implementing
intelligent limits on user actions with configurable thresholds.

Features:
- Question rate limiting
- Cooldown periods
- First-time user handling
- Admin exemptions
- Violation tracking
- Usage statistics
- Memory management

Technical Features:
- Configurable limits
- State-aware limiting
- Memory optimization
- Statistics tracking
- Cleanup routines
- Error handling
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
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """
    Advanced rate limiting middleware for spam prevention.

    This middleware provides:
    - Configurable rate limits
    - User state tracking
    - Violation monitoring
    - Statistics collection
    - Memory management

    Features:
    - Hourly question limits
    - Message cooldowns
    - First-time user detection
    - Admin exemptions
    - Command bypassing
    - Violation tracking
    - Usage statistics

    Technical Features:
    - State-aware limiting
    - Memory optimization
    - Atomic operations
    - Error handling
    - Cleanup routines
    """

    def __init__(
        self,
        questions_per_hour: int = RATE_LIMIT_QUESTIONS_PER_HOUR,
        cooldown_seconds: int = RATE_LIMIT_COOLDOWN_SECONDS
    ):
        """
        Initialize rate limiter with configuration.

        Args:
            questions_per_hour: Maximum questions allowed per hour
            cooldown_seconds: Required wait time between questions
        """
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
        """
        Process message through rate limiting system.

        This method:
        - Validates message type
        - Checks user permissions
        - Applies rate limits
        - Tracks violations
        - Updates statistics

        Args:
            handler: Message handler to execute
            event: Telegram message event
            data: Additional context data

        Returns:
            Any: Handler result if allowed
        """

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
                    logger.warning(
                        f"Rate limit cooldown hit for user {user_id}")
                    return  # Don't process further
            else:
                logger.info(
                    f"First question from user {user_id} - skipping cooldown")

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
        """
        Check if user is in question-sending state.

        This method:
        - Checks user state
        - Validates permissions
        - Handles state transitions

        Args:
            user_id: Telegram user identifier

        Returns:
            bool: True if user can send questions
        """
        # Import here to avoid circular imports
        from models.user_states import UserStateManager

        # Check if user can send a question based on their state
        can_send = await UserStateManager.can_send_question(user_id)
        return can_send

    async def _check_question_cooldown(self, user_id: int, now: datetime) -> bool:
        """
        Verify cooldown period compliance.

        This method:
        - Checks last question time
        - Calculates time passed
        - Validates cooldown period

        Args:
            user_id: Telegram user identifier
            now: Current timestamp

        Returns:
            bool: True if cooldown period passed
        """
        last_question = self.user_last_question.get(user_id)

        if not last_question:
            return True

        time_passed = (now - last_question).total_seconds()
        return time_passed >= self.cooldown_seconds

    def _get_cooldown_remaining(self, user_id: int) -> int:
        """
        Calculate remaining cooldown time.

        This method:
        - Gets last question time
        - Calculates remaining time
        - Handles edge cases

        Args:
            user_id: Telegram user identifier

        Returns:
            int: Seconds remaining in cooldown
        """
        last_question = self.user_last_question.get(user_id)
        if not last_question:
            return 0

        now = datetime.now()
        time_passed = (now - last_question).total_seconds()
        remaining = self.cooldown_seconds - time_passed

        return max(0, int(remaining))

    async def _check_hourly_limit(self, user_id: int, now: datetime) -> bool:
        """
        Verify hourly question limit compliance.

        This method:
        - Cleans old entries
        - Counts recent questions
        - Updates violation tracking
        - Handles limit enforcement

        Args:
            user_id: Telegram user identifier
            now: Current timestamp

        Returns:
            bool: True if under hourly limit
        """
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
        """
        Retrieve comprehensive user statistics.

        This method provides:
        - Recent question count
        - Cooldown status
        - First-time status
        - Violation count
        - Limit information

        Args:
            user_id: Telegram user identifier

        Returns:
            dict: User statistics and metrics
        """
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
        """
        Clean up expired tracking data.

        This method:
        - Removes old timestamps
        - Frees memory
        - Maintains data integrity
        - Optimizes storage
        """
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

        logger.debug(
            f"Cleaned up rate limit data. Active users: {len(self.user_questions)}")


class CallbackRateLimitMiddleware(BaseMiddleware):
    """
    Rate limiting middleware for callback queries.

    This middleware provides:
    - Callback query limiting
    - Spam prevention
    - Resource protection

    Features:
    - Configurable cooldown
    - User tracking
    - Error handling
    """

    def __init__(self, cooldown_seconds: int = 1):
        """
        Initialize callback rate limiter.

        Args:
            cooldown_seconds: Required wait time between callbacks
        """
        self.cooldown_seconds = cooldown_seconds
        self.user_last_callback: Dict[int, datetime] = {}

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process callback through rate limiting.

        This method:
        - Validates callback type
        - Applies rate limits
        - Updates tracking
        - Handles violations

        Args:
            handler: Callback handler to execute
            event: Telegram callback event
            data: Additional context data

        Returns:
            Any: Handler result if allowed
        """
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        user_id = event.from_user.id

        # Admin bypass
        if user_id == ADMIN_ID:
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
