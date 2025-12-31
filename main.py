#!/usr/bin/env python3
"""
Telegram News Automation Bot
Запускается через GitHub Actions, парсит новости, суммаризирует через Gemini,
отправляет в Telegram с og:image.

Author: Senior Python Developer
Version: 3.0.0
Python: 3.11+
"""

import asyncio
import logging
import sys
from datetime import datetime

from src.config import Config
from src.database import Database
from src.rss_parser import RSSParser
from src.image_extractor import ImageExtractor
from src.summarizer import GeminiSummarizer
from src.telegram_bot import TelegramPoster


# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("NewsBot")


# ============================================================================
# MAIN BOT CLASS
# ============================================================================

class NewsBot:
    """
    Главный оркестратор бота.
    Координирует: RSS → Image Extraction → Gemini → Telegram
    """

    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.database_path)
        self.rss_parser = RSSParser(config.rss_feeds)
        self.image_extractor = ImageExtractor()
        self.summarizer = GeminiSummarizer(
            api_key=config.gemini_api_key,
            model=config.gemini_model
        )
        self.telegram = TelegramPoster(
            token=config.telegram_token,
            channel_id=config.channel_id
        )
        
        logger.info("NewsBot инициализирован")

    async def process_article(self, article: dict) -> bool:
        """
        Обработка одной статьи.
        
        Returns:
            True если успешно обработана и отправлена
        """
        try:
            title = article["title"]
            link = article["link"]
            
            logger.info(f"Обработка: {title[:60]}...")
            
            # 1. Извлекаем og:image
            image_url = await self.image_extractor.extract(link)
            if image_url:
                logger.info(f"  ✓ Найдено изображение")
            else:
                logger.warning(f"  ⚠ Изображение не найдено")
            
            # 2. Суммаризируем через Gemini
            summary = await self.summarizer.summarize(article)
            if not summary:
                logger.error(f"  ✗ Ошибка суммаризации")
                return False
            logger.info(f"  ✓ Суммаризация завершена")
            
            # 3. Отправляем в Telegram
            success = await self.telegram.post(
                text=summary,
                image_url=image_url
            )
            
            if success:
                logger.info(f"  ✓ Отправлено в Telegram")
                return True
            else:
                logger.error(f"  ✗ Ошибка отправки")
                return False
                
        except Exception as e:
            logger.exception(f"Ошибка обработки статьи: {e}")
            return False

    async def run(self) -> dict:
        """
        Главный метод запуска бота.
        
        Returns:
            Статистика выполнения
        """
        stats = {
            "started_at": datetime.now().isoformat(),
            "articles_found": 0,
            "articles_new": 0,
            "articles_processed": 0,
            "articles_failed": 0,
            "errors": []
        }
        
        logger.info("=" * 60)
        logger.info("🚀 Запуск цикла обработки новостей")
        logger.info("=" * 60)
        
        try:
            # 1. Проверяем подключение к Telegram
            if not await self.telegram.test_connection():
                stats["errors"].append("Telegram connection failed")
                logger.error("❌ Не удалось подключиться к Telegram")
                return stats
            
            # 2. Получаем статьи из RSS
            articles = await self.rss_parser.fetch_all()
            stats["articles_found"] = len(articles)
            logger.info(f"📰 Найдено статей: {len(articles)}")
            
            if not articles:
                logger.info("Новых статей не найдено")
                return stats
            
            # 3. Фильтруем уже обработанные
            new_articles = []
            for article in articles:
                if not self.db.is_processed(article["link"]):
                    new_articles.append(article)
            
            stats["articles_new"] = len(new_articles)
            logger.info(f"🆕 Новых статей: {len(new_articles)}")
            
            # 4. Ограничиваем количество за один запуск
            articles_to_process = new_articles[:self.config.max_articles_per_run]
            
            # 5. Обрабатываем каждую статью
            for i, article in enumerate(articles_to_process, 1):
                logger.info(f"\n[{i}/{len(articles_to_process)}] {article['title'][:50]}...")
                
                success = await self.process_article(article)
                
                if success:
                    # Отмечаем как обработанную ТОЛЬКО после успешной отправки
                    self.db.mark_processed(
                        link=article["link"],
                        title=article["title"],
                        source=article.get("source", "unknown")
                    )
                    stats["articles_processed"] += 1
                else:
                    stats["articles_failed"] += 1
                
                # Пауза между отправками (rate limiting)
                if i < len(articles_to_process):
                    await asyncio.sleep(3)
            
            # 6. Выводим итоговую статистику
            db_stats = self.db.get_stats()
            logger.info("\n" + "=" * 60)
            logger.info("📊 ИТОГИ ЗАПУСКА:")
            logger.info(f"   • Найдено статей: {stats['articles_found']}")
            logger.info(f"   • Новых статей: {stats['articles_new']}")
            logger.info(f"   • Успешно обработано: {stats['articles_processed']}")
            logger.info(f"   • Ошибок: {stats['articles_failed']}")
            logger.info(f"   • Всего в БД: {db_stats['total']}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.exception(f"Критическая ошибка: {e}")
            stats["errors"].append(str(e))
        
        finally:
            await self.cleanup()
        
        stats["finished_at"] = datetime.now().isoformat()
        return stats

    async def cleanup(self):
        """Освобождение ресурсов."""
        await self.telegram.close()
        await self.image_extractor.close()
        logger.info("🧹 Ресурсы освобождены")


# ============================================================================
# ENTRY POINT
# ============================================================================

def print_banner():
    """Красивый баннер при запуске."""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║   📰  TELEGRAM NEWS BOT  v3.0.0                                  ║
    ║                                                                   ║
    ║   Pipeline: RSS → og:image → Gemini AI → Telegram                ║
    ║   Mode: GitHub Actions (one-shot execution)                       ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def main():
    """Точка входа в приложение."""
    print_banner()
    
    try:
        # Загружаем конфигурацию
        logger.info("📋 Загрузка конфигурации...")
        config = Config.from_env()
        
        logger.info(f"   • Модель: {config.gemini_model}")
        logger.info(f"   • Канал: {config.channel_id}")
        logger.info(f"   • RSS источников: {len(config.rss_feeds)}")
        logger.info(f"   • Макс. статей за запуск: {config.max_articles_per_run}")
        
        # Запускаем бота
        bot = NewsBot(config)
        stats = await bot.run()
        
        # Код возврата для GitHub Actions
        if stats["articles_failed"] > 0 and stats["articles_processed"] == 0:
            sys.exit(1)
        
    except ValueError as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        print("\n⚠️  Проверьте переменные окружения:")
        print("   TG_TOKEN, GEMINI_API_KEY, CHANNEL_ID")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("\n👋 Остановлено пользователем")
        
    except Exception as e:
        logger.exception(f"💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
