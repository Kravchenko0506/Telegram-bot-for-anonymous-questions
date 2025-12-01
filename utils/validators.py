"""Input validation and content moderation."""

import re
import html
from typing import Optional, Tuple, Dict
from config import MIN_QUESTION_LENGTH, MAX_QUESTION_LENGTH, MAX_ANSWER_LENGTH, ERROR_MESSAGE_TOO_LONG
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class InputValidator:
    """Input validation and sanitization."""

    URL_PATTERN = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(
        r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,5}[-\s\.]?[0-9]{1,5}'
    )
    SPAM_PATTERNS = [
        re.compile(r'(.)\1{5,}'),
        re.compile(r'[A-Z\s]{20,}'),
        re.compile(r'(viagra|cialis|casino|crypto|bitcoin)', re.IGNORECASE),
        re.compile(r'(click here|buy now|limited offer)', re.IGNORECASE),
    ]
    PROFANITY_WORDS = {'блять', 'хуй', 'пизда', 'ебать', 'сука'}


    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize and normalize text input."""
        if not text:
            return ""

        text = text.strip()
        text = ''.join(char for char in text if ord(
            char) >= 32 or char == '\n')
        text = html.escape(text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        if max_length and len(text) > max_length:
            text = text[:max_length]

        return text


    @staticmethod
    def validate_question(text: str, max_length: int = None, min_length: int = None) -> Tuple[bool, Optional[str]]:
        """Validate question text."""
        if not text or not text.strip():
            return False, "Вопрос не может быть пустым"

        min_len = min_length if (isinstance(
            min_length, int) and min_length > 0) else MIN_QUESTION_LENGTH
        if len(text.strip()) < min_len:
            return False, f"❌ Слишком короткий вопрос (минимум {min_len} симв.). Похоже на флуд."

        max_len = max_length if (isinstance(
            max_length, int) and max_length > 0) else MAX_QUESTION_LENGTH
        if len(text) > max_len:
            return False, ERROR_MESSAGE_TOO_LONG.format(max_length=max_len)

        for pattern in InputValidator.SPAM_PATTERNS:
            if pattern.search(text):
                logger.warning(f"Spam pattern detected: {pattern.pattern}")
                return False, "Вопрос похож на спам"

        urls = InputValidator.URL_PATTERN.findall(text)
        if len(urls) > 2:
            return False, "Слишком много ссылок в вопросе"

        if InputValidator.contains_profanity(text):
            logger.warning("Profanity detected in question")

        return True, None


    @staticmethod
    def validate_answer(text: str) -> Tuple[bool, Optional[str]]:
        """Validate answer text."""
        if not text or not text.strip():
            return False, "Ответ не может быть пустым"

        if len(text) > MAX_ANSWER_LENGTH:
            return False, f"Ответ слишком длинный (максимум {MAX_ANSWER_LENGTH} символов)"

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
            'emails': InputValidator.EMAIL_PATTERN.findall(text),
            'phones': InputValidator.PHONE_PATTERN.findall(text),
            'urls': InputValidator.URL_PATTERN.findall(text)
        }

        if any(data.values()):
            logger.warning(f"Personal data detected: {list(data.keys())}")

        return data
    
class ContentModerator:
    """Content moderation and spam detection."""

    @staticmethod
    def calculate_spam_score(text: str) -> float:
        """Calculate spam probability score (0.0 to 1.0)."""
        score = 0.0

        if re.search(r'(.)\1{4,}', text):
            score += 0.3

        if len(text) > 10:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.5:
                score += 0.2

        spam_keywords = ['заработок', 'доход', 'инвестиции', 'криптовалюта']
        for keyword in spam_keywords:
            if keyword.lower() in text.lower():
                score += 0.1

        punct_ratio = sum(1 for c in text if c in '!?.,;:') / max(len(text), 1)
        if punct_ratio > 0.2:
            score += 0.1

        url_count = len(InputValidator.URL_PATTERN.findall(text))
        score += url_count * 0.1

        return min(score, 1.0)


    @staticmethod
    def is_likely_spam(text: str, threshold: float = 0.5) -> bool:
        """Check if text is likely spam."""
        return ContentModerator.calculate_spam_score(text) >= threshold
