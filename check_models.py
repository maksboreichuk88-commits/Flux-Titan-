import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"Проверка доступных моделей для API ключа: {api_key[:10]}...")

try:
    genai.configure(api_key=api_key)
    
    # Получаем список всех моделей
    models = genai.list_models()
    
    print("\nДоступные модели:")
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f"✅ {model.name} - {model.display_name}")
        else:
            print(f"❌ {model.name} - {model.display_name} (не поддерживает generateContent)")
            
except Exception as e:
    print(f"❌ Ошибка получения моделей: {e}")
