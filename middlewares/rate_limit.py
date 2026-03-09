"""Rate limiting middleware for spam prevention."""

from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import (
    ADMIN_ID,
    ERROR_RATE_LIMIT,
    RATE_LIMIT_COOLDOWN_SECONDS,
    RATE_LIMIT_QUESTIONS_PER_HOUR,
)
from models.settings import SettingsManager
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting for user questions with cooldown and hourly limits."""

    def __init__(
        self,
        questions_per_hour: int = RATE_LIMIT_QUESTIONS_PER_HOUR,
        cooldown_seconds: int = RATE_LIMIT_COOLDOWN_SECONDS,
    ):
        self.questions_per_hour = questions_per_hour
        self.cooldown_seconds = cooldown_seconds

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        """Process message through rate limiting."""
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id

        # Admin and commands bypass
        if user_id == ADMIN_ID or (event.text and event.text.startswith("/")):
            return await handler(event, data)

        # Only rate limit when user is sending a question
        if not await self._is_sending_question(user_id):
            return await handler(event, data)

        # Naive UTC — matches naive datetime stored in SQLite
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Get user stats directly from DB
        stats = await self._get_user_db_stats(user_id, now)
        is_first = stats["total_questions"] == 0

        # Check cooldown (skip for first question)
        if not is_first:
            cooldown_setting = await SettingsManager.get_rate_limit_cooldown()
            last_time = stats["last_question_time"]
            if last_time:
                passed = (now - last_time).total_seconds()
                remaining = max(0, int(cooldown_setting - passed))
                if remaining > 0:
                    await event.answer(ERROR_RATE_LIMIT.format(seconds=remaining))
                    logger.warning(f"Cooldown hit for user {user_id}")
                    return

        # Check hourly limit
        limit = await SettingsManager.get_rate_limit_per_hour()
        if stats["questions_last_hour"] >= limit:
            await event.answer(
                f"❌ Лимит вопросов ({limit} в час) превышен. Попробуйте позже."
            )
            logger.warning(f"Hourly limit hit for user {user_id}")
            return

        return await handler(event, data)

    async def _is_sending_question(self, user_id: int) -> bool:
        """Check if user is in question-sending state."""
        from models.user_states import UserStateManager

        return await UserStateManager.can_send_question(user_id)

    async def _get_user_db_stats(self, user_id: int, now: datetime) -> dict:
        """Fetch real-time statistics from the database for rate limiting."""
        from sqlalchemy import select, func
        from models.database import async_session
        from models.questions import Question

        hour_ago = now - timedelta(hours=1)

        async with async_session() as session:
            # Check total count to know if this is their first ever question
            total_query = select(func.count(Question.id)).where(
                Question.user_id == user_id
            )
            total_questions = (await session.execute(total_query)).scalar() or 0

            # If no questions at all, skip other queries
            if total_questions == 0:
                return {
                    "total_questions": 0,
                    "last_question_time": None,
                    "questions_last_hour": 0,
                }

            # Time of the very last question (for cooldown)
            last_q_query = (
                select(Question.created_at)
                .where(Question.user_id == user_id)
                .order_by(Question.created_at.desc())
                .limit(1)
            )
            last_question_time = (await session.execute(last_q_query)).scalar()

            # How many questions in the last 1 hour (for hourly limit)
            hour_query = select(func.count(Question.id)).where(
                Question.user_id == user_id, Question.created_at >= hour_ago
            )
            questions_last_hour = (await session.execute(hour_query)).scalar() or 0

        return {
            "total_questions": total_questions,
            "last_question_time": last_question_time,
            "questions_last_hour": questions_last_hour,
        }


class CallbackRateLimitMiddleware(BaseMiddleware):
    """Rate limiting for callback queries."""

    def __init__(self, cooldown_seconds: int = 1):
        self.cooldown_seconds = cooldown_seconds
        self.user_last_callback: Dict[int, datetime] = {}

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        """Process callback with rate limiting."""
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        user_id = event.from_user.id

        if user_id == ADMIN_ID:
            return await handler(event, data)

        now = datetime.now(timezone.utc)
        last = self.user_last_callback.get(user_id)

        if last and (now - last).total_seconds() < self.cooldown_seconds:
            await event.answer("⏳ Подождите секунду.", show_alert=False)
            return

        self.user_last_callback[user_id] = now
        return await handler(event, data)
