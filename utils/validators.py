"""Input validation and content moderation."""

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from config import (
    ERROR_MESSAGE_TOO_LONG,
    MAX_ANSWER_LENGTH,
    MAX_QUESTION_LENGTH,
    MIN_QUESTION_LENGTH,
)
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class InputValidator:
    """Input validation and sanitization."""

    URL_PATTERN = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"  # noqa: E501
    )
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_PATTERN = re.compile(
        r"[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,5}[-\s\.]?[0-9]{1,5}"  # noqa: E501
    )
    PROFANITY_WORDS = {"блять", "хуй", "пизда", "ебать", "сука"}

    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize and normalize text input."""
        if not text:
            return ""

        text = text.strip()
        text = "".join(char for char in text if ord(char) >= 32 or char == "\n")
        text = html.escape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        if max_length and len(text) > max_length:
            text = text[:max_length]

        return text

    @staticmethod
    def validate_question(
        text: str, max_length: Optional[int] = None, min_length: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate question text."""
        if not text or not text.strip():
            return False, "Вопрос не может быть пустым"

        min_len = (
            min_length
            if (isinstance(min_length, int) and min_length > 0)
            else MIN_QUESTION_LENGTH
        )
        if len(text.strip()) < min_len:
            return (
                False,
                f"❌ Слишком короткий вопрос (минимум {min_len} симв.). Похоже на флуд.",
            )

        max_len = (
            max_length
            if (isinstance(max_length, int) and max_length > 0)
            else MAX_QUESTION_LENGTH
        )
        if len(text) > max_len:
            return False, ERROR_MESSAGE_TOO_LONG.format(max_length=max_len)

        urls = InputValidator.URL_PATTERN.findall(text)
        if len(urls) > 2:
            return False, "Слишком много ссылок в вопросе"

        if InputValidator.contains_profanity(text):
            logger.warning("Profanity detected in question")

        return True, None

    @staticmethod
    def validate_answer(
        text: str, max_length: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate answer text."""
        if not text or not text.strip():
            return False, "Ответ не может быть пустым"

        max_len = (
            max_length
            if isinstance(max_length, int) and max_length > 0
            else MAX_ANSWER_LENGTH
        )
        if len(text) > max_len:
            return (
                False,
                f"Ответ слишком длинный (максимум {max_len} символов)",
            )

        if len(text.strip()) < 2:
            return False, "Ответ слишком короткий"

        return True, None

    @staticmethod
    def contains_profanity(text: str) -> bool:
        """Check if text contains profanity."""
        text_lower = text.lower()
        return any(word in text_lower for word in InputValidator.PROFANITY_WORDS)

    @staticmethod
    def extract_personal_data(text: str) -> Dict[str, list]:
        """Extract potential personal data from text."""
        data = {
            "emails": InputValidator.EMAIL_PATTERN.findall(text),
            "phones": InputValidator.PHONE_PATTERN.findall(text),
            "urls": InputValidator.URL_PATTERN.findall(text),
        }

        return data


class ContentModerator:
    """Content moderation and spam detection.

    Loads spam keywords and regex patterns from an external JSON file.
    Call load_spam_words() once at bot startup before processing messages.
    """

    _categories: list[dict[str, Any]] = []
    _regex_patterns: list[tuple[re.Pattern, float]] = []
    _loaded: bool = False

    @classmethod
    def load_spam_words(cls, path: str) -> None:
        """Load spam word categories and regex patterns from JSON file.

        Args:
            path: path to JSON file relative to project root or absolute.

        Raises:
            FileNotFoundError: if file does not exist.
            json.JSONDecodeError: if file contains invalid JSON.
        """
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = Path(__file__).resolve().parent.parent / path

        raw: dict = json.loads(file_path.read_text(encoding="utf-8"))

        cls._categories = []
        cls._regex_patterns = []

        for category_name, category_data in raw.items():
            weight = float(category_data.get("weight", 0.1))

            words = category_data.get("words", [])
            if words:
                cls._categories.append(
                    {
                        "name": category_name,
                        "weight": weight,
                        "words": [w.lower() for w in words],
                    }
                )

            regex_dict = category_data.get("regex", {})
            for pattern_name, pattern_str in regex_dict.items():
                try:
                    compiled = re.compile(pattern_str)
                    cls._regex_patterns.append((compiled, weight))
                except re.error as e:
                    logger.error(
                        f"invalid_regex_in_spam_config: pattern='{pattern_name}', "
                        f"error='{e}'"
                    )

        total_words = sum(len(c["words"]) for c in cls._categories)
        cls._loaded = True
        logger.info(
            f"Spam config loaded: {len(cls._categories)} categories, "
            f"{total_words} words, {len(cls._regex_patterns)} regex patterns"
        )

    @classmethod
    def calculate_spam_score(cls, text: str) -> float:
        """Calculate spam probability score (0.0 to 1.0).

        Checks loaded keyword categories and regex patterns.
        Also applies built-in heuristics (caps ratio, punctuation, URLs,
        repeated characters).
        """
        if not cls._loaded:
            logger.warning("spam_words_not_loaded, using built-in heuristics only")

        score = 0.0
        text_lower = text.lower()

        # --- Keyword categories from JSON ---
        for category in cls._categories:
            for word in category["words"]:
                if word in text_lower:
                    score += category["weight"]
                    break

        for pattern, weight in cls._regex_patterns:
            if pattern.search(text):
                score += weight

        if re.search(r"(.)\1{4,}", text):
            score += 0.3

        if len(text) > 10:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.5:
                score += 0.2
        punct_ratio = sum(1 for c in text if c in "!?.,;:") / max(len(text), 1)
        if punct_ratio > 0.2:
            score += 0.1

        url_count = len(InputValidator.URL_PATTERN.findall(text))
        score += url_count * 0.1

        return min(score, 1.0)
