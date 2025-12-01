"""Rate limiting middleware for spam prevention."""

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
from models.settings import SettingsManager

logger = get_logger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting for user questions with cooldown and hourly limits."""

    def __init__(
        self,
        questions_per_hour: int = RATE_LIMIT_QUESTIONS_PER_HOUR,
        cooldown_seconds: int = RATE_LIMIT_COOLDOWN_SECONDS
    ):
        self.questions_per_hour = questions_per_hour
        self.cooldown_seconds = cooldown_seconds

        self.user_questions: Dict[int, list[datetime]] = defaultdict(list)
        self.user_last_question: Dict[int, datetime] = {}
        self.user_has_sent_first: set[int] = set()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """Process message through rate limiting."""
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id

        # Admin and commands bypass
        if user_id == ADMIN_ID or (event.text and event.text.startswith('/')):
            return await handler(event, data)

        # Only rate limit when user is sending a question
        if not await self._is_sending_question(user_id):
            return await handler(event, data)

        now = datetime.now()
        is_first = user_id not in self.user_has_sent_first

        # Check cooldown (skip for first question)
        if not is_first:
            remaining = await self._get_cooldown_remaining(user_id)
            if remaining > 0:
                await event.answer(ERROR_RATE_LIMIT.format(seconds=remaining))
                logger.warning(f"Cooldown hit for user {user_id}")
                return

        # Check hourly limit
        if not await self._check_hourly_limit(user_id, now):
            limit = await SettingsManager.get_rate_limit_per_hour()
            await event.answer(f"❌ Лимит вопросов ({limit} в час) превышен. Попробуйте позже.")
            logger.warning(f"Hourly limit hit for user {user_id}")
            return

        # Update tracking
        self.user_last_question[user_id] = now
        if is_first:
            self.user_has_sent_first.add(user_id)

        return await handler(event, data)

    async def _is_sending_question(self, user_id: int) -> bool:
        """Check if user is in question-sending state."""
        from models.user_states import UserStateManager
        return await UserStateManager.can_send_question(user_id)

    async def _get_cooldown_remaining(self, user_id: int) -> int:
        """Get remaining cooldown seconds."""
        last = self.user_last_question.get(user_id)
        if not last:
            return 0

        cooldown = await SettingsManager.get_rate_limit_cooldown()
        passed = (datetime.now() - last).total_seconds()
        return max(0, int(cooldown - passed))

    async def _check_hourly_limit(self, user_id: int, now: datetime) -> bool:
        """Check and update hourly question limit."""
        hour_ago = now - timedelta(hours=1)

        # Clean old entries
        self.user_questions[user_id] = [
            t for t in self.user_questions[user_id] if t > hour_ago
        ]

        limit = await SettingsManager.get_rate_limit_per_hour()
        if len(self.user_questions[user_id]) >= limit:
            return False

        self.user_questions[user_id].append(now)
        return True


class CallbackRateLimitMiddleware(BaseMiddleware):
    """ Rate limiting for callback queries."""

    def __init__(self, cooldown_seconds: int = 1):
        self.cooldown_seconds = cooldown_seconds
        self.user_last_callback: Dict[int, datetime] = {}

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Process callback with rate limiting."""
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        user_id = event.from_user.id

        if user_id == ADMIN_ID:
            return await handler(event, data)

        now = datetime.now()
        last = self.user_last_callback.get(user_id)

        if last and (now - last).total_seconds() < self.cooldown_seconds:
            await event.answer("⏳ Подождите секунду.", show_alert=False)
            return

        self.user_last_callback[user_id] = now
        return await handler(event, data)
