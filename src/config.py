"""
Модуль конфигурации.
Загружает все настройки из переменных окружения.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict
from dotenv import load_dotenv

# Загружаем .env файл (для локальной разработки)
load_dotenv()


# Предустановленные RSS-ленты
DEFAULT_RSS_FEEDS: List[Dict[str, str]] = [
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "icon": "🔶"
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "icon": "🔷"
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "icon": "🟠"
    },
]


@dataclass(frozen=True)
class Config:
    """
    Иммутабельная конфигурация приложения.
    Все секреты загружаются из переменных окружения.
    """
    
    # Обязательные параметры
    telegram_token: str
    gemini_api_key: str
    channel_id: str
    
    # Опциональные параметры с значениями по умолчанию
    gemini_model: str = "gemini-1.5-flash"
    database_path: str = "processed.db"
    max_articles_per_run: int = 5
    rss_feeds: tuple = field(default_factory=lambda: tuple(DEFAULT_RSS_FEEDS))
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Фабричный метод для создания конфигурации из env-переменных.
        
        Raises:
            ValueError: если отсутствуют обязательные переменные
        """
        telegram_token = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        channel_id = os.getenv("CHANNEL_ID")
        
        # Валидация обязательных переменных
        missing = []
        if not telegram_token:
            missing.append("TELEGRAM_BOT_TOKEN or TG_TOKEN")
        if not gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not channel_id:
            missing.append("CHANNEL_ID")
        
        if missing:
            raise ValueError(
                f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}"
            )
        
        # Парсинг дополнительных RSS (если заданы)
        custom_feeds = os.getenv("CUSTOM_RSS_FEEDS")
        rss_feeds = list(DEFAULT_RSS_FEEDS)
        
        if custom_feeds:
            # Формат: "Name1|URL1,Name2|URL2"
            for feed_str in custom_feeds.split(","):
                parts = feed_str.strip().split("|")
                if len(parts) >= 2:
                    rss_feeds.append({
                        "name": parts[0].strip(),
                        "url": parts[1].strip(),
                        "icon": parts[2].strip() if len(parts) > 2 else "📰"
                    })
        
        return cls(
            telegram_token=telegram_token,
            gemini_api_key=gemini_api_key,
            channel_id=channel_id,
            gemini_model=os.getenv("GEMINI_MODEL", cls.gemini_model),
            database_path=os.getenv("DATABASE_PATH", cls.database_path),
            max_articles_per_run=int(
                os.getenv("MAX_ARTICLES_PER_RUN", str(cls.max_articles_per_run))
            ),
            rss_feeds=tuple(rss_feeds),
        )
