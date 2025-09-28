#!/usr/bin/env python3
"""
Скрипт для перевірки всіх імпортів перед deploy
"""

import sys
import os

def test_imports():
    """Перевірка всіх імпортів"""
    print("🔍 Testing imports...")
    
    # Додаємо поточну директорію в sys.path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    errors = []
    
    # Тест config
    try:
        import config
        print("✅ config imported successfully")
    except Exception as e:
        errors.append(f"❌ config: {e}")
        print(f"❌ config import failed: {e}")
    
    # Тест services
    try:
        from services import telegram
        print("✅ services.telegram imported successfully")
    except Exception as e:
        errors.append(f"❌ services.telegram: {e}")
        print(f"❌ services.telegram import failed: {e}")
    
    try:
        from services import gemini
        print("✅ services.gemini imported successfully")
    except Exception as e:
        errors.append(f"❌ services.gemini: {e}")
        print(f"❌ services.gemini import failed: {e}")
    
    try:
        from services import sheets
        print("✅ services.sheets imported successfully")
    except Exception as e:
        errors.append(f"❌ services.sheets: {e}")
        print(f"❌ services.sheets import failed: {e}")
    
    # Тест models
    try:
        from models import user
        print("✅ models.user imported successfully")
    except Exception as e:
        errors.append(f"❌ models.user: {e}")
        print(f"❌ models.user import failed: {e}")
    
    # Тест handlers
    try:
        from handlers import message_processor
        print("✅ handlers.message_processor imported successfully")
    except Exception as e:
        errors.append(f"❌ handlers.message_processor: {e}")
        print(f"❌ handlers.message_processor import failed: {e}")
    
    # Підсумок
    if errors:
        print(f"\n💥 Found {len(errors)} import errors:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n🎉 All imports successful!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)