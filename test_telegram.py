import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
print(f"Token (first 10 chars): {token[:10]}...")

try:
    url = f"https://api.telegram.org/bot{token}/getMe"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data['ok']:
            bot_info = data['result']
            print(f"✅ Telegram бот работает!")
            print(f"Имя: {bot_info['first_name']}")
            print(f"Username: @{bot_info['username']}")
        else:
            print(f"❌ Ошибка API: {data}")
    else:
        print(f"❌ HTTP ошибка: {response.status_code}")
        
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
