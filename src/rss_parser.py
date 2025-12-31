"""
Модуль парсинга RSS-лент.
Поддерживает несколько источников с параллельной загрузкой.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any
from datetime import datetime

import feedparser

logger = logging.getLogger("NewsBot.RSS")


class RSSParser:
    """
    Парсер RSS-лент с поддержкой множества источников.
    Использует asyncio для параллельной загрузки.
    """

    def __init__(self, feeds: tuple):
        """
        Инициализация парсера.
        
        Args:
            feeds: кортеж словарей с информацией о RSS-лентах
        """
        self.feeds = feeds
        logger.info(f"RSS парсер инициализирован с {len(feeds)} источниками")

    async def fetch_feed(self, feed_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Загрузка одной RSS-ленты.
        
        Args:
            feed_info: словарь с name, url, icon
            
        Returns:
            Список статей
        """
        name = feed_info["name"]
        url = feed_info["url"]
        icon = feed_info.get("icon", "📰")
        
        try:
            logger.debug(f"Загрузка RSS: {name}")
            
            # feedparser синхронный, оборачиваем в thread
            loop = asyncio.get_running_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            
            # Проверка на ошибки парсинга
            if feed.bozo:
                logger.warning(f"RSS предупреждение [{name}]: {feed.bozo_exception}")
            
            articles = []
            for entry in feed.entries[:10]:  # Берем только последние 10
                article = {
                    "title": self._clean_text(entry.get("title", "Без заголовка")),
                    "link": entry.get("link", ""),
                    "summary": self._clean_html(entry.get("summary", "")),
                    "published": self._parse_date(entry.get("published")),
                    "author": entry.get("author", ""),
                    "source": name,
                    "source_icon": icon,
                }
                
                # Извлекаем контент, если есть
                if hasattr(entry, "content") and entry.content:
                    article["content"] = self._clean_html(
                        entry.content[0].get("value", "")
                    )
                else:
                    article["content"] = article["summary"]
                
                articles.append(article)
            
            logger.info(f"✓ {name}: загружено {len(articles)} статей")
            return articles
            
        except Exception as e:
            logger.error(f"✗ {name}: ошибка загрузки - {e}")
            return []

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """
        Параллельная загрузка всех RSS-лент.
        
        Returns:
            Объединенный список статей, отсортированный по дате
        """
        logger.info(f"Загрузка {len(self.feeds)} RSS-лент...")
        
        # Запускаем все задачи параллельно
        tasks = [self.fetch_feed(feed) for feed in self.feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Объединяем результаты
        all_articles = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Ошибка в задаче: {result}")
            elif isinstance(result, list):
                all_articles.extend(result)
        
        # Сортируем по дате (новые первыми)
        all_articles.sort(
            key=lambda x: x.get("published") or datetime.min,
            reverse=True
        )
        
        logger.info(f"Всего загружено {len(all_articles)} статей из {len(self.feeds)} источников")
        return all_articles

    @staticmethod
    def _clean_html(text: str) -> str:
        """Удаление HTML-тегов и очистка текста."""
        if not text:
            return ""
        
        # Удаляем HTML теги
        clean = re.sub(r"<[^>]+>", " ", text)
        # Нормализуем пробелы
        clean = re.sub(r"\s+", " ", clean).strip()
        # Декодируем HTML-сущности
        entities = {
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#39;": "'",
            "&nbsp;": " ",
            "&mdash;": "—",
            "&ndash;": "–",
        }
        for entity, char in entities.items():
            clean = clean.replace(entity, char)
        
        # Ограничиваем длину
        return clean[:2000]

    @staticmethod
    def _clean_text(text: str) -> str:
        """Базовая очистка текста."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Парсинг даты из различных форматов."""
        if not date_str:
            return datetime.now()
        
        # feedparser обычно предоставляет parsed time tuple
        try:
            from time import mktime
            import feedparser
            parsed = feedparser._parse_date(date_str)
            if parsed:
                return datetime.fromtimestamp(mktime(parsed))
        except Exception:
            pass
        
        return datetime.now()
