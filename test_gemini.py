import os
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key (first 10 chars): {api_key[:10]}...")

try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Say hello in Russian"
    )
    print("✅ Gemini API работает!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Ошибка Gemini API: {e}")
