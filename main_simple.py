import asyncio
import feedparser
import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import google.generativeai as genai
import requests
from dotenv import load_dotenv


class DatabaseManager:
    def __init__(self, db_path: str = "processed.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS processed_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def is_article_processed(self, url: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT url FROM processed_articles WHERE url = ?", (url,))
            return cursor.fetchone() is not None
    
    def mark_article_processed(self, url: str, title: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_articles (url, title) VALUES (?, ?)",
                (url, title)
            )
            conn.commit()


class RSSParser:
    def __init__(self, rss_url: str):
        self.rss_url = rss_url
    
    def fetch_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            feed = feedparser.parse(self.rss_url)
            articles = []
            
            for entry in feed.entries[:limit]:
                article = {
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.summary if hasattr(entry, 'summary') else '',
                    'published': entry.published if hasattr(entry, 'published') else '',
                    'author': entry.author if hasattr(entry, 'author') else ''
                }
                articles.append(article)
            
            return articles
        except Exception as e:
            logging.error(f"Ошибка при парсинге RSS: {e}")
            return []


class AIRewriter:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.rewrite_prompt = (
            "Сделай краткий и дерзкий рерайт на русском для IT-предпринимателей, "
            "выдели 3 главных мысли и добавь ссылку на оригинал"
        )
    
    async def rewrite_article(self, article: Dict[str, Any]) -> Optional[str]:
        try:
            text_to_rewrite = f"""
            Заголовок: {article['title']}
            Содержание: {article['summary']}
            Ссылка: {article['link']}
            """
            
            full_prompt = f"{self.rewrite_prompt}\n\n{text_to_rewrite}"
            
            response = await asyncio.to_thread(
                self.model.generate_content, full_prompt
            )
            
            return response.text if response else None
        except Exception as e:
            logging.error(f"Ошибка при рерайте статьи: {e}")
            return None


class TelegramBot:
    def __init__(self, token: str, gemini_api_key: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.db = DatabaseManager()
        self.parser = RSSParser("https://techcrunch.com/feed/")
        self.ai_rewriter = AIRewriter(gemini_api_key)
    
    async def send_message(self, chat_id: str, text: str) -> bool:
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=data)
            return response.status_code == 200
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения: {e}")
            return False
    
    async def process_and_send_news(self, chat_id: str) -> int:
        articles = self.parser.fetch_articles(limit=5)
        processed_count = 0
        
        for article in articles:
            if not self.db.is_article_processed(article['link']):
                rewritten_content = await self.ai_rewriter.rewrite_article(article)
                
                if rewritten_content:
                    message = f"📰 *{article['title']}*\n\n{rewritten_content}\n\n🔗 [Оригинал]({article['link']})"
                    success = await self.send_message(chat_id, message)
                    
                    if success:
                        self.db.mark_article_processed(article['link'], article['title'])
                        processed_count += 1
                        logging.info(f"Отправлена статья: {article['title']}")
                    else:
                        logging.error(f"Не удалось отправить: {article['title']}")
                else:
                    logging.error(f"Не удалось обработать: {article['title']}")
        
        return processed_count


async def main():
    load_dotenv()
    
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not telegram_token or not gemini_api_key:
        print("Ошибка: Не найдены токены в .env файле!")
        return
    
    logging.basicConfig(level=logging.INFO)
    
    bot = TelegramBot(telegram_token, gemini_api_key)
    
    # Получаем chat_id (для примера используем тестовый)
    chat_id = input("Введите chat_id для отправки новостей: ")
    
    print("Начинаю обработку новостей...")
    count = await bot.process_and_send_news(chat_id)
    print(f"Обработано новостей: {count}")


if __name__ == "__main__":
    asyncio.run(main())
