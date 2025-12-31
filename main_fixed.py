import asyncio
import feedparser
import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from dotenv import load_dotenv


class DatabaseManager:
    """Класс для управления базой данных SQLite"""
    
    def __init__(self, db_path: str = "processed.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self) -> None:
        """Инициализация базы данных"""
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
        """Проверка, была ли статья уже обработана"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT url FROM processed_articles WHERE url = ?", (url,))
            return cursor.fetchone() is not None
    
    def mark_article_processed(self, url: str, title: str) -> None:
        """Отметить статью как обработанную"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_articles (url, title) VALUES (?, ?)",
                (url, title)
            )
            conn.commit()
    
    def cleanup_old_records(self, days: int = 30) -> None:
        """Очистка старых записей"""
        cutoff_date = datetime.now() - timedelta(days=days)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM processed_articles WHERE processed_at < ?",
                (cutoff_date.isoformat(),)
            )
            conn.commit()


class RSSParser:
    """Класс для парсинга RSS-лент"""
    
    def __init__(self, rss_url: str):
        self.rss_url = rss_url
    
    def fetch_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение статей из RSS-ленты"""
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
    """Класс для рерайта текста с использованием Gemini API"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        # Используем правильную конфигурацию для модели
        self.model = genai.GenerativeModel(model_name)
        self.rewrite_prompt = (
            "Сделай краткий и дерзкий рерайт на русском для IT-предпринимателей, "
            "выдели 3 главных мысли и добавь ссылку на оригинал"
        )
    
    async def rewrite_article(self, article: Dict[str, Any]) -> Optional[str]:
        """Рерайт статьи с использованием ИИ"""
        try:
            text_to_rewrite = f"""
            Заголовок: {article['title']}
            Содержание: {article['summary']}
            Ссылка: {article['link']}
            """
            
            full_prompt = f"{self.rewrite_prompt}\n\n{text_to_rewrite}"
            
            # Используем asyncio.to_thread для неблокирующего вызова
            response = await asyncio.to_thread(
                self.model.generate_content, full_prompt
            )
            
            return response.text if response else None
        except Exception as e:
            logging.error(f"Ошибка при рерайте статьи: {e}")
            # Если основная модель не работает, пробуем альтернативную
            if "flash" in self.model.model_name:
                logging.info("Пробую альтернативную модель...")
                try:
                    alt_model = genai.GenerativeModel("gemini-1.5-flash-latest")
                    response = await asyncio.to_thread(
                        alt_model.generate_content, full_prompt
                    )
                    return response.text if response else None
                except Exception as e2:
                    logging.error(f"Ошибка с альтернативной моделью: {e2}")
            return None


class NewsBot:
    """Основной класс Telegram-бота"""
    
    def __init__(self, telegram_token: str, gemini_api_key: str):
        self.bot = Bot(token=telegram_token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(self.bot, storage=self.storage)
        self.db = DatabaseManager()
        self.parser = RSSParser("https://techcrunch.com/feed/")
        self.ai_rewriter = AIRewriter(gemini_api_key)
        
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Настройка обработчиков команд"""
        
        @self.dp.message_handler(commands=['start'])
        async def cmd_start(message: types.Message):
            """Обработчик команды /start"""
            welcome_text = (
                "🚀 *Добро пожаловать в News Bot!*\n\n"
                "Я автоматически отслеживаю новости с TechCrunch, "
                "перерабатываю их с помощью ИИ и отправляю вам краткую версию.\n\n"
                "📋 *Доступные команды:*\n"
                "/start - Показать это сообщение\n"
                "/news - Получить последние новости\n"
                "/help - Помощь"
            )
            await message.answer(welcome_text, parse_mode="Markdown")
        
        @self.dp.message_handler(commands=['news'])
        async def cmd_news(message: types.Message):
            """Обработчик команды /news"""
            await message.answer("🔄 Получаю свежие новости...")
            
            articles = self.parser.fetch_articles(limit=5)
            processed_count = 0
            
            for article in articles:
                if not self.db.is_article_processed(article['link']):
                    rewritten_content = await self.ai_rewriter.rewrite_article(article)
                    
                    if rewritten_content:
                        await message.answer(
                            f"📰 *{article['title']}*\n\n"
                            f"{rewritten_content}\n\n"
                            f"🔗 [Оригинал]({article['link']})",
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )
                        
                        self.db.mark_article_processed(article['link'], article['title'])
                        processed_count += 1
                    else:
                        logging.error(f"Не удалось обработать статью: {article['title']}")
            
            if processed_count == 0:
                await message.answer("📭 Новых новостей нет. Попробуйте позже!")
            else:
                await message.answer(f"✅ Обработано новостей: {processed_count}")
        
        @self.dp.message_handler(commands=['help'])
        async def cmd_help(message: types.Message):
            """Обработчик команды /help"""
            help_text = (
                "📖 *Справка по боту*\n\n"
                "Бот автоматически отслеживает RSS-ленту TechCrunch, "
                "использует Gemini AI для создания кратких и дерзких "
                "переработанных версий новостей на русском языке.\n\n"
                "🔄 *Команды:*\n"
                "/start - Начать работу с ботом\n"
                "/news - Получить последние новости\n"
                "/help - Показать эту справку"
            )
            await message.answer(help_text, parse_mode="Markdown")
    
    async def start_polling(self) -> None:
        """Запуск бота в режиме опроса"""
        logging.info("Запуск бота...")
        await self.dp.start_polling(self.bot)


def main():
    """Главная функция"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Загрузка переменных окружения
    load_dotenv()
    
    # Получение токенов
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not telegram_token or not gemini_api_key:
        logging.error("Не найдены необходимые токены в .env файле!")
        return
    
    # Создание и запуск бота
    bot = NewsBot(telegram_token, gemini_api_key)
    
    try:
        asyncio.run(bot.start_polling())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")


if __name__ == "__main__":
    main()
