import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key (first 10 chars): {api_key[:10]}...")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Say hello in Russian")
    print("✅ Gemini API работает!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Ошибка Gemini API: {e}")
    
    # Пробуем альтернативную модель
    try:
        print("\nПробую модель gemini-1.5-flash-latest...")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content("Say hello in Russian")
        print("✅ Альтернативная модель работает!")
        print(f"Response: {response.text}")
    except Exception as e2:
        print(f"❌ Ошибка с альтернативной моделью: {e2}")
