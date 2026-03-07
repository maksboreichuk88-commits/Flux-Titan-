import asyncio
import logging
import sys
from datetime import datetime

from flux_titan.config import Config
from flux_titan.storage.sqlite import Database
from flux_titan.feeds import RSSParser
from flux_titan.image_extractor import ImageExtractor
from flux_titan.summarizers.gemini import GeminiSummarizer
from flux_titan.publishers.telegram import TelegramPoster

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("NewsBot")

class NewsBot:
    """
    Main orchestrator for Flux-Titan.
    Coordinates: RSS -> Image -> Gemini -> Telegram -> SQLite.
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
        logger.info("NewsBot initialized")

    async def process_article(self, article: dict) -> bool:
        try:
            title = article["title"]
            logger.info(f"Processing: {title[:60]}...")
            
            image_url = await self.image_extractor.extract(article["link"])
            summary = await self.summarizer.summarize(article)
            
            if not summary:
                logger.error("  ✗ Summarization failed")
                return False
                
            success = await self.telegram.post(text=summary, image_url=image_url)
            
            if success:
                logger.info("  ✓ Sent to Telegram")
                return True
            else:
                logger.error("  ✗ Send failed")
                return False
                
        except Exception as e:
            logger.exception(f"Error processing article: {e}")
            return False

    async def run(self) -> dict:
        stats = {
            "articles_found": 0, "articles_new": 0, 
            "articles_processed": 0, "articles_failed": 0
        }
        
        try:
            if not await self.telegram.test_connection():
                logger.error("❌ Telegram connection failed")
                return stats
            
            articles = await self.rss_parser.fetch_all()
            stats["articles_found"] = len(articles)
            
            if not articles:
                return stats
            
            new_articles = [a for a in articles if not self.db.is_processed(a["link"])]
            stats["articles_new"] = len(new_articles)
            
            articles_to_process = new_articles[:self.config.max_articles_per_run]
            
            for i, article in enumerate(articles_to_process, 1):
                success = await self.process_article(article)
                if success:
                    self.db.mark_processed(link=article["link"], title=article["title"], source=article.get("source", "unknown"))
                    stats["articles_processed"] += 1
                else:
                    stats["articles_failed"] += 1
                    
                if i < len(articles_to_process):
                    await asyncio.sleep(3)
                    
            db_stats = self.db.get_stats()
            logger.info(f"Run complete. New: {stats['articles_new']}, Processed: {stats['articles_processed']}, DB Total: {db_stats['total']}")
            
        finally:
            await self.telegram.close()
            await self.image_extractor.close()
            
        return stats

def run_cli():
    """CLI entry point for Flux-Titan."""
    print("📰 Flux-Titan Telegram News Bot")
    try:
        config = Config.from_env()
        bot = NewsBot(config)
        
        stats = asyncio.run(bot.run())
        
        if stats["articles_failed"] > 0 and stats["articles_processed"] == 0:
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_cli()
