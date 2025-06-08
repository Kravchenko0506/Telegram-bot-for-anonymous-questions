"""
Input Validators and Sanitizers

Provides validation and sanitization for user input to prevent XSS and injection attacks.
"""

import re
import html
from typing import Optional, Tuple, Dict

from config import MAX_QUESTION_LENGTH, MAX_ANSWER_LENGTH
from utils.logger import get_bot_logger

logger = get_bot_logger()


class InputValidator:
    """Validates and sanitizes user input."""
    
    # Patterns for detection
    URL_PATTERN = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )
    
    PHONE_PATTERN = re.compile(
        r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,5}[-\s\.]?[0-9]{1,5}'
    )
    
    # Forbidden patterns (for spam detection)
    SPAM_PATTERNS = [
        re.compile(r'(.)\1{5,}'),  # Same character repeated 6+ times
        re.compile(r'[A-Z\s]{20,}'),  # All caps text
        re.compile(r'(viagra|cialis|casino|crypto|bitcoin)', re.IGNORECASE),
        re.compile(r'(click here|buy now|limited offer)', re.IGNORECASE),
    ]
    
    # Profanity list (basic example - expand as needed)
    PROFANITY_WORDS = {
        'блять', 'хуй', 'пизда', 'ебать', 'сука',
        # Add more as needed
    }
    
    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize text input.
        
        Args:
            text: Raw text input
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove control characters except newlines
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        # Escape HTML entities to prevent XSS
        text = html.escape(text)
        
        # Limit consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Limit length if specified
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    @staticmethod
    def validate_question(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate question text.
        
        Args:
            text: Question text
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if empty
        if not text or not text.strip():
            return False, "Вопрос не может быть пустым"
        
        # Check length
        if len(text) > MAX_QUESTION_LENGTH:
            return False, f"Вопрос слишком длинный (максимум {MAX_QUESTION_LENGTH} символов)"
        
        # Check minimum length
        if len(text.strip()) < 5:
            return False, "Вопрос слишком короткий (минимум 5 символов)"
        
        # Check for spam patterns
        for pattern in InputValidator.SPAM_PATTERNS:
            if pattern.search(text):
                logger.warning(f"Spam pattern detected in question: {pattern.pattern}")
                return False, "Вопрос похож на спам"
        
        # Check for excessive URLs
        urls = InputValidator.URL_PATTERN.findall(text)
        if len(urls) > 2:
            return False, "Слишком много ссылок в вопросе"
        
        # Check for profanity (optional - can be warning instead of block)
        if InputValidator.contains_profanity(text):
            logger.warning("Profanity detected in question")
            # You can choose to block or just log
            # return False, "Вопрос содержит нецензурную лексику"
        
        return True, None
    
    @staticmethod
    def validate_answer(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate answer text.
        
        Args:
            text: Answer text
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if empty
        if not text or not text.strip():
            return False, "Ответ не может быть пустым"
        
        # Check length
        if len(text) > MAX_ANSWER_LENGTH:
            return False, f"Ответ слишком длинный (максимум {MAX_ANSWER_LENGTH} символов)"
        
        # Check minimum length
        if len(text.strip()) < 2:
            return False, "Ответ слишком короткий"
        
        return True, None
    
    @staticmethod
    def contains_profanity(text: str) -> bool:
        """Check if text contains profanity."""
        text_lower = text.lower()
        
        for word in InputValidator.PROFANITY_WORDS:
            if word in text_lower:
                return True
        
        return False
    
    @staticmethod
    def extract_personal_data(text: str) -> Dict[str, list]:
        """
        Extract potential personal data from text.
        
        Returns dict with found emails, phones, etc.
        """
        data = {
            'emails': InputValidator.EMAIL_PATTERN.findall(text),
            'phones': InputValidator.PHONE_PATTERN.findall(text),
            'urls': InputValidator.URL_PATTERN.findall(text)
        }
        
        # Log if personal data found
        if any(data.values()):
            logger.warning(f"Personal data detected in text: {list(data.keys())}")
        
        return data
    
    @staticmethod
    def clean_command_args(args: str) -> str:
        """Clean command arguments."""
        if not args:
            return ""
        
        # Remove potential command injection attempts
        args = re.sub(r'[;&|`$]', '', args)
        
        # Limit length
        args = args[:100]
        
        return args.strip()
    
    @staticmethod
    def is_valid_username(username: str) -> bool:
        """Validate Telegram username format."""
        if not username:
            return False
        
        # Telegram username rules:
        # - 5-32 characters
        # - Only a-z, 0-9, and underscores
        # - Cannot start with number
        pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$')
        return bool(pattern.match(username))
    
    @staticmethod
    def format_error_message(error: str, user_friendly: bool = True) -> str:
        """Format error message for user display."""
        if not user_friendly:
            return error
        
        # Make technical errors more user-friendly
        error_mapping = {
            'database': '❌ Временная проблема с базой данных. Попробуйте позже.',
            'connection': '❌ Проблема с соединением. Проверьте интернет.',
            'timeout': '❌ Превышено время ожидания. Попробуйте еще раз.',
            'validation': '❌ Проверьте правильность введенных данных.',
        }
        
        for key, friendly_message in error_mapping.items():
            if key in error.lower():
                return friendly_message
        
        return f"❌ {error}"


class ContentModerator:
    """Advanced content moderation."""
    
    @staticmethod
    def calculate_spam_score(text: str) -> float:
        """
        Calculate spam score (0.0 - 1.0).
        
        Higher score = more likely spam.
        """
        score = 0.0
        
        # Check for repeated characters
        if re.search(r'(.)\1{4,}', text):
            score += 0.3
        
        # Check for all caps (if more than 50%)
        if len(text) > 10:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.5:
                score += 0.2
        
        # Check for spam keywords
        spam_keywords = ['заработок', 'доход', 'инвестиции', 'криптовалюта']
        for keyword in spam_keywords:
            if keyword.lower() in text.lower():
                score += 0.1
        
        # Check for excessive punctuation
        punct_ratio = sum(1 for c in text if c in '!?.,;:') / max(len(text), 1)
        if punct_ratio > 0.2:
            score += 0.1
        
        # Check for URLs
        url_count = len(InputValidator.URL_PATTERN.findall(text))
        score += url_count * 0.1
        
        return min(score, 1.0)
    
    @staticmethod
    def is_likely_spam(text: str, threshold: float = 0.5) -> bool:
        """Check if text is likely spam."""
        return ContentModerator.calculate_spam_score(text) >= threshold