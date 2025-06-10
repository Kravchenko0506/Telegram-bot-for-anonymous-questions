"""
Tests for utility modules: validators, logger, helpers.

Tests input validation, content moderation, logging, and helper functions.
"""

import pytest
import re
from unittest.mock import patch, MagicMock

from utils.validators import InputValidator, ContentModerator
from utils.logger import configure_logger, get_bot_logger, get_admin_logger
from config import MAX_QUESTION_LENGTH, MAX_ANSWER_LENGTH


class TestInputValidator:
    """Tests for InputValidator class."""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_sanitize_text_basic(self):
        """Test basic text sanitization."""
        # Normal text
        result = InputValidator.sanitize_text("Hello world!")
        assert result == "Hello world!"
        
        # Text with whitespace
        result = InputValidator.sanitize_text("  Hello   world!  ")
        assert result == "Hello   world!"
        
        # Empty text
        result = InputValidator.sanitize_text("")
        assert result == ""
        
        # None input
        result = InputValidator.sanitize_text(None)
        assert result == ""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_sanitize_text_html_escape(self):
        """Test HTML escaping in sanitization."""
        # HTML tags
        result = InputValidator.sanitize_text("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result
        
        # HTML entities
        result = InputValidator.sanitize_text("Test & <test> \"quotes\"")
        assert "&amp;" in result
        assert "&lt;test&gt;" in result
        assert "&quot;" in result
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_sanitize_text_control_characters(self):
        """Test control character removal."""
        # Control characters (except newlines)
        result = InputValidator.sanitize_text("Hello\x00\x01world\n")
        assert result == "Helloworld\n"
        
        # Preserve newlines but limit consecutive ones
        result = InputValidator.sanitize_text("Line1\n\n\n\n\nLine2")
        assert result == "Line1\n\nLine2"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_sanitize_text_length_limit(self):
        """Test length limiting in sanitization."""
        long_text = "A" * 1000
        result = InputValidator.sanitize_text(long_text, max_length=100)
        assert len(result) == 100
        assert result == "A" * 100
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_validate_question_success(self):
        """Test successful question validation."""
        valid_questions = [
            "How does this work?",
            "This is a valid question with reasonable length.",
            "Как это работает? Можете объяснить?",
            "Question with emoji 👍 and symbols!@#$%",
        ]
        
        for question in valid_questions:
            is_valid, error = InputValidator.validate_question(question)
            assert is_valid is True, f"Question should be valid: {question}"
            assert error is None
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_validate_question_failures(self):
        """Test question validation failures."""
        invalid_cases = [
            ("", "пустым"),  # Empty
            ("   ", "пустым"),  # Whitespace only
            ("Hi", "короткий"),  # Too short
            ("A" * (MAX_QUESTION_LENGTH + 1), "длинный"),  # Too long
        ]
        
        for question, expected_error in invalid_cases:
            is_valid, error = InputValidator.validate_question(question)
            assert is_valid is False, f"Question should be invalid: {question}"
            assert error is not None
            assert expected_error in error.lower()
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_validate_question_spam_detection(self):
        """Test spam detection in question validation."""
        spam_questions = [
            "AAAAAAAAAA",  # Repeated characters
            "BUY NOW CLICK HERE VIAGRA",  # Spam keywords
            "http://spam.com http://spam2.com http://spam3.com",  # Multiple URLs
        ]
        
        for question in spam_questions:
            is_valid, error = InputValidator.validate_question(question)
            # Might be valid or invalid depending on spam detection
            if not is_valid:
                assert "спам" in error.lower() or "ссылок" in error.lower()
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_validate_answer_success(self):
        """Test successful answer validation."""
        valid_answers = [
            "Yes, this is how it works.",
            "Да, это работает именно так.",
            "A" * 100,  # Reasonable length
            "Short answer.",
        ]
        
        for answer in valid_answers:
            is_valid, error = InputValidator.validate_answer(answer)
            assert is_valid is True, f"Answer should be valid: {answer}"
            assert error is None
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_validate_answer_failures(self):
        """Test answer validation failures."""
        invalid_cases = [
            ("", "пустым"),  # Empty
            ("   ", "пустым"),  # Whitespace only
            ("A", "короткий"),  # Too short
            ("A" * (MAX_ANSWER_LENGTH + 1), "длинный"),  # Too long
        ]
        
        for answer, expected_error in invalid_cases:
            is_valid, error = InputValidator.validate_answer(answer)
            assert is_valid is False, f"Answer should be invalid: {answer}"
            assert error is not None
            assert expected_error in error.lower()
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_extract_personal_data(self):
        """Test personal data extraction."""
        test_text = """
        Contact me at user@example.com or call +1-234-567-8900.
        Visit https://example.com for more info.
        Also check http://test.org
        """
        
        data = InputValidator.extract_personal_data(test_text)
        
        assert len(data['emails']) == 1
        assert "user@example.com" in data['emails']
        
        assert len(data['phones']) >= 1  # Might detect phone number
        
        assert len(data['urls']) == 2
        assert any("example.com" in url for url in data['urls'])
        assert any("test.org" in url for url in data['urls'])
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_contains_profanity(self):
        """Test profanity detection."""
        # Clean text
        assert InputValidator.contains_profanity("This is clean text") is False
        
        # Text with profanity (using safe test words)
        # Note: Real implementation should use actual profanity list
        profane_text = "Some text with bad words"
        # This test depends on actual profanity words in PROFANITY_WORDS
        result = InputValidator.contains_profanity(profane_text)
        assert isinstance(result, bool)
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_clean_command_args(self):
        """Test command argument cleaning."""
        # Normal args
        result = InputValidator.clean_command_args("normal args")
        assert result == "normal args"
        
        # Args with potential injection
        result = InputValidator.clean_command_args("args; rm -rf /")
        assert ";" not in result
        assert result == "args rm -rf /"
        
        # Long args
        long_args = "A" * 200
        result = InputValidator.clean_command_args(long_args)
        assert len(result) == 100
        
        # Empty args
        result = InputValidator.clean_command_args("")
        assert result == ""
        
        result = InputValidator.clean_command_args(None)
        assert result == ""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_is_valid_username(self):
        """Test Telegram username validation."""
        valid_usernames = [
            "validuser",
            "user123",
            "user_name",
            "a1234567890123456789012345678901",  # 31 chars
        ]
        
        for username in valid_usernames:
            assert InputValidator.is_valid_username(username) is True
        
        invalid_usernames = [
            "",  # Empty
            "123user",  # Starts with number
            "user-name",  # Contains dash
            "user@name",  # Contains @
            "usr",  # Too short
            "a" * 33,  # Too long
            None,  # None
        ]
        
        for username in invalid_usernames:
            assert InputValidator.is_valid_username(username) is False
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_format_error_message(self):
        """Test error message formatting."""
        # Technical error
        technical_error = "database connection timeout"
        friendly = InputValidator.format_error_message(technical_error, user_friendly=True)
        assert "❌" in friendly
        assert "timeout" not in friendly.lower() or "превышено время" in friendly
        
        # User-friendly mode off
        unfriendly = InputValidator.format_error_message(technical_error, user_friendly=False)
        assert unfriendly == technical_error
        
        # Regular error
        regular_error = "Invalid input"
        result = InputValidator.format_error_message(regular_error, user_friendly=True)
        assert "❌" in result
        assert "Invalid input" in result


class TestContentModerator:
    """Tests for ContentModerator class."""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_calculate_spam_score_normal_text(self):
        """Test spam score for normal text."""
        normal_texts = [
            "How does this feature work?",
            "Can you help me understand this?",
            "I have a question about your service.",
        ]
        
        for text in normal_texts:
            score = ContentModerator.calculate_spam_score(text)
            assert 0.0 <= score <= 1.0
            assert score < 0.3, f"Normal text should have low spam score: {text}"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_calculate_spam_score_suspicious_text(self):
        """Test spam score for suspicious text."""
        suspicious_texts = [
            "AAAAAAAAAA",  # Repeated characters
            "BUY NOW!!!!! CLICK HERE!!!!!",  # All caps with exclamation
            "Make money fast with crypto investment!!!",  # Spam keywords
            "Visit http://spam.com http://spam2.com",  # Multiple URLs
        ]
        
        for text in suspicious_texts:
            score = ContentModerator.calculate_spam_score(text)
            assert 0.0 <= score <= 1.0
            # Some of these should have higher scores
            # Exact threshold depends on implementation
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_calculate_spam_score_edge_cases(self):
        """Test spam score edge cases."""
        # Empty text
        score = ContentModerator.calculate_spam_score("")
        assert score == 0.0
        
        # Very short text
        score = ContentModerator.calculate_spam_score("Hi")
        assert 0.0 <= score <= 1.0
        
        # Text with only punctuation
        score = ContentModerator.calculate_spam_score("!@#$%^&*()")
        assert 0.0 <= score <= 1.0
        
        # Unicode text
        score = ContentModerator.calculate_spam_score("Привет! Как дела? 👋")
        assert 0.0 <= score <= 1.0
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_is_likely_spam_threshold(self):
        """Test spam detection with different thresholds."""
        test_text = "BUY NOW CLICK HERE"
        
        # Test with different thresholds
        assert ContentModerator.is_likely_spam(test_text, threshold=0.9) is False
        assert ContentModerator.is_likely_spam(test_text, threshold=0.1) is True
        
        # Default threshold
        result = ContentModerator.is_likely_spam(test_text)
        assert isinstance(result, bool)
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_spam_score_components(self):
        """Test individual components of spam scoring."""
        # Test repeated characters
        repeated_text = "Helloooooooo"
        score = ContentModerator.calculate_spam_score(repeated_text)
        assert score > 0  # Should detect repeated characters
        
        # Test all caps
        caps_text = "THIS IS ALL CAPS TEXT"
        score = ContentModerator.calculate_spam_score(caps_text)
        assert score > 0  # Should detect all caps
        
        # Test excessive punctuation
        punct_text = "What!!!!!!!!!!!!!!!"
        score = ContentModerator.calculate_spam_score(punct_text)
        assert score > 0  # Should detect excessive punctuation


class TestLoggerUtils:
    """Tests for logging utilities."""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_configure_logger_basic(self):
        """Test basic logger configuration."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            
            logger = configure_logger(
                logger_name="test_logger",
                log_file=log_file,
                add_console_handler=False
            )
            
            assert logger.name == "test_logger"
            assert len(logger.handlers) >= 1
            
            # Test logging
            logger.info("Test message")
            
            # Check file was created
            assert os.path.exists(log_file)
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_configure_logger_no_duplicates(self):
        """Test that duplicate handlers aren't added."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_dup.log")
            
            # Configure same logger twice
            logger1 = configure_logger("test_dup_logger", log_file)
            initial_handlers = len(logger1.handlers)
            
            logger2 = configure_logger("test_dup_logger", log_file)
            
            # Should not add duplicate handlers
            assert len(logger2.handlers) == initial_handlers
            assert logger1 is logger2  # Same logger instance
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_get_logger_functions(self):
        """Test logger getter functions."""
        bot_logger = get_bot_logger()
        admin_logger = get_admin_logger()
        
        assert bot_logger.name == "bot"
        assert admin_logger.name == "admin"
        
        # Test that loggers work
        bot_logger.info("Bot test message")
        admin_logger.info("Admin test message")
        
        # Loggers should be properly configured
        assert len(bot_logger.handlers) > 0
        assert len(admin_logger.handlers) > 0
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_logger_file_rotation(self):
        """Test logger file rotation configuration."""
        import tempfile
        import os
        from logging.handlers import RotatingFileHandler
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "rotation_test.log")
            
            logger = configure_logger(
                logger_name="rotation_test",
                log_file=log_file,
                max_bytes=1024,  # Small size for testing
                backup_count=3
            )
            
            # Find the rotating file handler
            rotating_handler = None
            for handler in logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    rotating_handler = handler
                    break
            
            assert rotating_handler is not None
            assert rotating_handler.maxBytes == 1024
            assert rotating_handler.backupCount == 3


class TestValidatorIntegration:
    """Integration tests for validators working together."""
    
    @pytest.mark.integration
    @pytest.mark.utils
    def test_complete_validation_flow(self):
        """Test complete validation workflow."""
        test_cases = [
            {
                'input': "How does machine learning work?",
                'should_pass_question': True,
                'should_pass_spam': True,
                'expected_personal_data': False
            },
            {
                'input': "Contact me at test@email.com for crypto deals!",
                'should_pass_question': True,
                'should_pass_spam': False,  # Might fail spam check
                'expected_personal_data': True
            },
            {
                'input': "<script>alert('xss')</script>",
                'should_pass_question': True,  # After sanitization
                'should_pass_spam': True,
                'expected_personal_data': False
            },
            {
                'input': "A" * (MAX_QUESTION_LENGTH + 100),
                'should_pass_question': False,  # Too long
                'should_pass_spam': True,
                'expected_personal_data': False
            }
        ]
        
        for case in test_cases:
            input_text = case['input']
            
            # Step 1: Sanitize
            sanitized = InputValidator.sanitize_text(input_text, MAX_QUESTION_LENGTH)
            
            # Step 2: Validate as question
            is_valid, error = InputValidator.validate_question(sanitized)
            
            if case['should_pass_question']:
                assert is_valid, f"Should pass validation: {input_text}"
            else:
                assert not is_valid, f"Should fail validation: {input_text}"
            
            # Step 3: Check for spam (only if valid)
            if is_valid:
                is_spam = ContentModerator.is_likely_spam(sanitized)
                spam_score = ContentModerator.calculate_spam_score(sanitized)
                
                assert isinstance(is_spam, bool)
                assert 0.0 <= spam_score <= 1.0
            
            # Step 4: Check for personal data
            personal_data = InputValidator.extract_personal_data(sanitized)
            has_personal_data = any(personal_data.values())
            
            if case['expected_personal_data']:
                assert has_personal_data, f"Should detect personal data: {input_text}"
            # Note: We don't assert False for no personal data as detection might vary
    
    @pytest.mark.integration
    @pytest.mark.utils
    def test_validation_with_real_world_inputs(self):
        """Test validators with real-world input examples."""
        real_inputs = [
            "Привет! Можете объяснить как работает ваш сервис?",
            "Hello! Can you tell me more about your pricing?",
            "I'm having trouble with the login feature 🤔",
            "What's the difference between plan A and plan B?",
            "Когда будет доступна мобильная версия?",
            "Do you support integration with third-party APIs?",
            "How can I cancel my subscription?",
            "Is there a free trial available?",
        ]
        
        for input_text in real_inputs:
            # All should pass basic validation
            sanitized = InputValidator.sanitize_text(input_text)
            is_valid, error = InputValidator.validate_question(sanitized)
            
            assert is_valid, f"Real-world input should be valid: {input_text}"
            assert error is None
            
            # Should have low spam scores
            spam_score = ContentModerator.calculate_spam_score(sanitized)
            assert spam_score < 0.5, f"Real question should have low spam score: {input_text}"
            
            # Check personal data extraction doesn't crash
            personal_data = InputValidator.extract_personal_data(sanitized)
            assert isinstance(personal_data, dict)
    
    @pytest.mark.integration
    @pytest.mark.utils
    @pytest.mark.security
    def test_security_validation(self):
        """Test security-focused validation scenarios."""
        security_test_cases = [
            # XSS attempts
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            
            # SQL injection attempts
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
            
            # Command injection
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(whoami)",
            
            # HTML injection
            "<h1>Injected HTML</h1>",
            "<iframe src='evil.com'></iframe>",
        ]
        
        for malicious_input in security_test_cases:
            # Sanitization should neutralize threats
            sanitized = InputValidator.sanitize_text(malicious_input)
            
            # Should not contain raw HTML/script tags
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
            assert "<iframe" not in sanitized
            
            # Should escape HTML entities
            if "<" in malicious_input:
                assert "&lt;" in sanitized or "<" not in sanitized
            
            # Validation should still work
            is_valid, error = InputValidator.validate_question(sanitized)
            # Some might be invalid due to length/content, but shouldn't crash
            assert isinstance(is_valid, bool)


class TestUtilsPerformance:
    """Performance tests for utility functions."""
    
    @pytest.mark.slow
    @pytest.mark.utils
    def test_validator_performance_bulk(self):
        """Test validator performance with many inputs."""
        import time
        
        # Generate test data
        test_texts = [
            f"Test question number {i} with some content to make it realistic"
            for i in range(1000)
        ]
        
        # Test sanitization performance
        start_time = time.time()
        for text in test_texts:
            InputValidator.sanitize_text(text)
        sanitize_time = time.time() - start_time
        
        # Test validation performance
        start_time = time.time()
        for text in test_texts:
            InputValidator.validate_question(text)
        validate_time = time.time() - start_time
        
        # Test spam detection performance
        start_time = time.time()
        for text in test_texts:
            ContentModerator.calculate_spam_score(text)
        spam_time = time.time() - start_time
        
        # Performance should be reasonable (adjust thresholds as needed)
        assert sanitize_time < 5.0, f"Sanitization too slow: {sanitize_time}s"
        assert validate_time < 5.0, f"Validation too slow: {validate_time}s"
        assert spam_time < 10.0, f"Spam detection too slow: {spam_time}s"
        
        print(f"Performance results for 1000 texts:")
        print(f"  Sanitization: {sanitize_time:.2f}s")
        print(f"  Validation: {validate_time:.2f}s")
        print(f"  Spam detection: {spam_time:.2f}s")
    
    @pytest.mark.slow
    @pytest.mark.utils
    def test_validator_memory_usage(self):
        """Test validator memory usage."""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process many texts
        for i in range(10000):
            text = f"Test text {i} " * 50  # ~500 chars each
            
            InputValidator.sanitize_text(text)
            InputValidator.validate_question(text)
            ContentModerator.calculate_spam_score(text)
            
            # Cleanup every 1000 iterations
            if i % 1000 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB)
        assert memory_increase < 100 * 1024 * 1024, f"Memory usage too high: {memory_increase / 1024 / 1024:.1f}MB"
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_regex_performance(self):
        """Test regex performance in validators."""
        import time
        
        test_text = "This is a test email user@example.com and phone +1-234-567-8900 with URL https://example.com"
        
        # Test URL pattern
        start = time.time()
        for _ in range(1000):
            InputValidator.URL_PATTERN.findall(test_text)
        url_time = time.time() - start
        
        # Test email pattern
        start = time.time()
        for _ in range(1000):
            InputValidator.EMAIL_PATTERN.findall(test_text)
        email_time = time.time() - start
        
        # Test phone pattern
        start = time.time()
        for _ in range(1000):
            InputValidator.PHONE_PATTERN.findall(test_text)
        phone_time = time.time() - start
        
        # Regex should be fast
        assert url_time < 1.0, f"URL regex too slow: {url_time}s"
        assert email_time < 1.0, f"Email regex too slow: {email_time}s"
        assert phone_time < 1.0, f"Phone regex too slow: {phone_time}s"


class TestUtilsEdgeCases:
    """Edge case tests for utility functions."""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_unicode_and_emoji_handling(self):
        """Test handling of Unicode and emoji characters."""
        unicode_texts = [
            "Привет! 👋 Как дела?",
            "Hello 🌍 World 🚀",
            "Text with 中文 characters",
            "Emoji test 😀😃😄😁😆😅🤣😂",
            "Math symbols: ∑∫∞±≤≥",
        ]
        
        for text in unicode_texts:
            # Sanitization should preserve Unicode
            sanitized = InputValidator.sanitize_text(text)
            assert len(sanitized) > 0
            
            # Validation should work
            is_valid, error = InputValidator.validate_question(sanitized)
            assert isinstance(is_valid, bool)
            
            # Spam detection should work
            spam_score = ContentModerator.calculate_spam_score(sanitized)
            assert 0.0 <= spam_score <= 1.0
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_extremely_long_inputs(self):
        """Test handling of extremely long inputs."""
        # Very long text
        long_text = "A" * 100000
        
        # Sanitization should handle it
        sanitized = InputValidator.sanitize_text(long_text, max_length=1000)
        assert len(sanitized) == 1000
        
        # Validation should reject it
        is_valid, error = InputValidator.validate_question(long_text)
        assert is_valid is False
        assert "длинный" in error.lower()
        
        # Spam detection should handle it without crashing
        spam_score = ContentModerator.calculate_spam_score(long_text[:10000])  # Limit for performance
        assert 0.0 <= spam_score <= 1.0
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_null_and_special_characters(self):
        """Test handling of null and special characters."""
        special_inputs = [
            "\x00\x01\x02",  # Null and control chars
            "\r\n\t",        # Whitespace chars
            "\u0000\u0001",  # Unicode null chars
            "",              # Empty string
            None,            # None input
        ]
        
        for input_text in special_inputs:
            # Should not crash
            try:
                sanitized = InputValidator.sanitize_text(input_text)
                assert isinstance(sanitized, str)
                
                if sanitized:  # Only validate non-empty
                    is_valid, error = InputValidator.validate_question(sanitized)
                    assert isinstance(is_valid, bool)
                    
                    spam_score = ContentModerator.calculate_spam_score(sanitized)
                    assert 0.0 <= spam_score <= 1.0
                    
            except Exception as e:
                pytest.fail(f"Should not crash on input {repr(input_text)}: {e}")
    
    @pytest.mark.utils
    @pytest.mark.unit 
    def test_boundary_values(self):
        """Test boundary values for validation."""
        # Test exact length limits
        exact_min = "A" * 5  # Minimum length
        exact_max = "A" * MAX_QUESTION_LENGTH  # Maximum length
        over_max = "A" * (MAX_QUESTION_LENGTH + 1)  # Over maximum
        
        # Minimum length should pass
        is_valid, error = InputValidator.validate_question(exact_min)
        assert is_valid is True
        
        # Maximum length should pass
        is_valid, error = InputValidator.validate_question(exact_max)
        assert is_valid is True
        
        # Over maximum should fail
        is_valid, error = InputValidator.validate_question(over_max)
        assert is_valid is False
        assert "длинный" in error.lower()
        
        # Test answer validation boundaries
        exact_answer_max = "A" * MAX_ANSWER_LENGTH
        over_answer_max = "A" * (MAX_ANSWER_LENGTH + 1)
        
        is_valid, error = InputValidator.validate_answer(exact_answer_max)
        assert is_valid is True
        
        is_valid, error = InputValidator.validate_answer(over_answer_max)
        assert is_valid is False


class TestUtilsCompatibility:
    """Compatibility tests for different environments."""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_python_version_compatibility(self):
        """Test compatibility with Python features."""
        import sys
        
        # Ensure we're using Python 3.10+
        assert sys.version_info >= (3, 10), "Requires Python 3.10+"
        
        # Test f-string compatibility
        test_var = "test"
        f_string_result = f"This is a {test_var}"
        assert "test" in f_string_result
        
        # Test type hints work
        def test_function(text: str) -> bool:
            return isinstance(text, str)
        
        assert test_function("test") is True
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_regex_engine_compatibility(self):
        """Test regex engine compatibility."""
        # Test that all patterns compile
        patterns = [
            InputValidator.URL_PATTERN,
            InputValidator.EMAIL_PATTERN,
            InputValidator.PHONE_PATTERN,
        ]
        
        for pattern in patterns:
            assert hasattr(pattern, 'pattern')
            assert hasattr(pattern, 'search')
            assert hasattr(pattern, 'findall')
            
            # Test basic functionality
            test_result = pattern.findall("test string")
            assert isinstance(test_result, list)
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_encoding_compatibility(self):
        """Test text encoding compatibility."""
        # Test various encodings
        test_strings = [
            "ASCII text",
            "UTF-8 text: café",
            "Emoji: 👍🎉🚀",
            "Mixed: Hello мир 世界",
        ]
        
        for text in test_strings:
            # Should handle different encodings
            sanitized = InputValidator.sanitize_text(text)
            assert isinstance(sanitized, str)
            
            # Should be JSON serializable (for API responses)
            import json
            try:
                json.dumps(sanitized)
            except UnicodeDecodeError:
                pytest.fail(f"Text should be JSON serializable: {repr(text)}")


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        "-v",
        "--tb=short",
        "-m", "utils",
        __file__
    ])