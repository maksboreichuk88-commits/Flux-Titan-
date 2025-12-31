import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")

print("Получение обновлений бота...")
print("Отправьте любое сообщение боту @borey_system_bot")

url = f"https://api.telegram.org/bot{token}/getUpdates"
response = requests.get(url)

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    data = response.json()
    if data['result']:
        for update in data['result']:
            if 'message' in update:
                chat = update['message']['chat']
                print(f"\nID найден:")
                print(f"  Chat ID: {chat['id']}")
                print(f"  Type: {chat.get('type', 'unknown')}")
                print(f"  Name: {chat.get('first_name', '')} {chat.get('last_name', '')}")
                print(f"  Username: @{chat.get('username', '')}")
