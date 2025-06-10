#!/usr/bin/env python3
"""
Скрипт для отладки функций валидации
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.validators import InputValidator, ContentModerator

def test_sanitize_behavior():
    """Проверяем реальное поведение sanitize_text"""
    
    print("=== Тестируем sanitize_text ===")
    
    test_cases = [
        ("Hello\x00\x01world\n", "контрольные символы"),
        ("Line1\n\n\n\n\nLine2", "множественные переносы"),
        ("  text  ", "пробелы"),
        ("A" * 5, "минимальная длина"),
    ]
    
    for input_text, description in test_cases:
        result = InputValidator.sanitize_text(input_text)
        print(f"{description}:")
        print(f"  Вход: {repr(input_text)}")
        print(f"  Выход: {repr(result)}")
        print()

def test_validation_behavior():
    """Проверяем поведение валидации"""
    
    print("=== Тестируем validate_question ===")
    
    test_cases = [
        "A" * 5,  # Минимальная длина
        "Contact me at test@email.com for crypto deals!",  # Спам
        "AAAAAAA",  # Повторяющиеся символы
    ]
    
    for text in test_cases:
        is_valid, error = InputValidator.validate_question(text)
        spam_score = ContentModerator.calculate_spam_score(text)
        is_spam = ContentModerator.is_likely_spam(text)
        
        print(f"Текст: {text[:50]}...")
        print(f"  Валидный: {is_valid}")
        print(f"  Ошибка: {error}")
        print(f"  Спам-скор: {spam_score:.2f}")
        print(f"  Это спам: {is_spam}")
        print()

if __name__ == "__main__":
    test_sanitize_behavior()
    test_validation_behavior()