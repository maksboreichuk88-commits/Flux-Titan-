import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("CHANNEL_ID", "8387754806")

print(f"Токен: {token[:10]}...")
print(f"Chat ID: {chat_id}")

# Тестовое сообщение
url = f"https://api.telegram.org/bot{token}/sendMessage"
data = {
    'chat_id': chat_id,
    'text': '🚀 Тестовое сообщение от News Bot!',
    'parse_mode': 'Markdown'
}

print("\nОтправка тестового сообщения...")
response = requests.post(url, data=data)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    print("✅ Сообщение отправлено успешно!")
else:
    print("❌ Ошибка отправки")
