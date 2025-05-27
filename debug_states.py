"""
Простая проверка состояний админа - исправленная версия
"""

# Сначала импортируем все нужные модули
import sys
import os

def check_admin_states():
    """Проверить текущие состояния администратора."""
    print("🔍 === ДИАГНОСТИКА СОСТОЯНИЙ ===")
    
    try:
        # Импортируем после настройки окружения
        from handlers.admin_states import admin_answer_states
        from config import ADMIN_ID
        
        print(f"📋 Все состояния: {admin_answer_states}")
        print(f"👤 ID админа: {ADMIN_ID}")
        print(f"🔢 Количество активных состояний: {len(admin_answer_states)}")
        
        if ADMIN_ID in admin_answer_states:
            admin_state = admin_answer_states[ADMIN_ID]
            print(f"🎯 Состояние админа {ADMIN_ID}: {admin_state}")
            print("⚠️  ПРОБЛЕМА: Админ застрял в состоянии ответа!")
            print("💡 РЕШЕНИЕ: Нужно очистить состояние")
            
            # Показываем что в состоянии
            if 'question_id' in admin_state:
                print(f"📋 Застрял на вопросе: {admin_state['question_id']}")
            if 'mode' in admin_state:
                print(f"🔧 Режим: {admin_state['mode']}")
            
            return True  # Есть проблема
        else:
            print("✅ Состояние админа в порядке (нет активных состояний)")
            return False  # Нет проблемы
            
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Это нормально, если бот не запущен")
        return False
    except Exception as e:
        print(f"❌ Другая ошибка: {e}")
        return False

def clear_admin_state_if_needed():
    """Очистить состояние админа если он застрял."""
    print("\n🛠 === ПОПЫТКА ОЧИСТКИ ===")
    
    try:
        from handlers.admin_states import admin_answer_states
        from config import ADMIN_ID
        
        if ADMIN_ID in admin_answer_states:
            # Сохраняем информацию о состоянии
            old_state = admin_answer_states[ADMIN_ID].copy()
            
            # Очищаем состояние
            del admin_answer_states[ADMIN_ID]
            
            print(f"✅ Состояние админа {ADMIN_ID} очищено!")
            print(f"📋 Было: {old_state}")
            print("💡 Теперь админ может нормально отвечать на вопросы")
            return True
        else:
            print("ℹ️  Состояние админа уже чистое")
            return False
            
    except Exception as e:
        print(f"❌ Не удалось очистить состояние: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Проверка состояний админа...")
    
    # Проверяем есть ли проблема
    has_problem = check_admin_states()
    
    if has_problem:
        print("\n" + "="*50)
        print("⚠️  ОБНАРУЖЕНА ПРОБЛЕМА!")
        print("💡 Админ застрял в режиме ответа")
        print("🔧 Попробуем очистить состояние...")
        
        cleared = clear_admin_state_if_needed()
        
        if cleared:
            print("\n✅ ПРОБЛЕМА РЕШЕНА!")
            print("🚀 Теперь можно запускать бота заново")
        else:
            print("\n❌ Не удалось автоматически решить проблему")
            print("💡 Рекомендуется перезапустить бота полностью")
    else:
        print("\n✅ ВСЕ В ПОРЯДКЕ!")
        print("🚀 Состояния чистые, можно запускать бота")
    
    print("\n" + "="*50)
    print("🎯 ЗАКЛЮЧЕНИЕ:")
    print("- Если состояния очищены → запускайте бота")
    print("- Если проблема повторяется → сообщите мне")
    print("- Для запуска: python main.py")