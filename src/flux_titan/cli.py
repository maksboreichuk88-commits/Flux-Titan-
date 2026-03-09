"""
CLI entry-point and main orchestrator for Flux-Titan v0.2.

Pipeline per article:
  RSS → Exact-duplicate check → Semantic-duplicate check →
  AI Scoring (NewsEvaluator) → Summarize → Publish to Telegram → Mark in DB
"""

import asyncio
import logging
import sys

from flux_titan.config import Config
from flux_titan.evaluator import NewsEvaluator
from flux_titan.feeds import RSSParser
from flux_titan.image_extractor import ImageExtractor
from flux_titan.publishers.telegram import TelegramPoster
from flux_titan.semantic_filter import check_semantic_duplicate
from flux_titan.storage.sqlite import Database
from flux_titan.summarizers.gemini import GeminiSummarizer
from flux_titan.summarizers.kimi import KimiSummarizer
from flux_titan.summarizers.openai import OpenAISummarizer

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
    Pipeline: collect → exact-dedup → semantic-dedup → AI score → summarize → publish.
    """

    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.database_path)
        self.rss_parser = RSSParser(config.rss_feeds)
        self.image_extractor = ImageExtractor()
        self.evaluator = NewsEvaluator(config)

        # --- Summarizer selection ---
        if config.ai_provider == "gemini":
            self.summarizer = GeminiSummarizer(
                api_key=config.gemini_api_key,
                model=config.gemini_model,
            )
        elif config.ai_provider_input == "kimi":
            self.summarizer = KimiSummarizer(
                api_key=config.openai_api_key,
                model=config.openai_model,
                base_url=config.openai_base_url,
            )
        else:
            self.summarizer = OpenAISummarizer(
                api_key=config.openai_api_key,
                model=config.openai_model,
                base_url=config.openai_base_url,
            )

        self.telegram = TelegramPoster(
            token=config.telegram_token,
            channel_id=config.channel_id,
        )
        logger.info(
            "Flux-Titan v0.2 initialized | backend=%s | clickbait<%d | factuality>%d",
            config.ai_provider_input,
            config.clickbait_threshold,
            config.factuality_threshold,
        )

    # ── Per-article pipeline ────────────────────────────────────────

    async def process_article(self, article: dict) -> bool:
        """Full pipeline for a single article (summarize → image → send)."""
        try:
            title = article["title"]
            logger.info("  → Summarizing: %s", title[:60])

            image_url = await self.image_extractor.resolve(article)
            summary = await self.summarizer.summarize(article)

            if not summary:
                logger.error("  ✗ Summarization failed")
                return False

            success = await self.telegram.post(text=summary, image_url=image_url)

            if success:
                logger.info("  ✓ Sent to Telegram")
                return True

            logger.error("  ✗ Telegram send failed")
            return False

        except Exception as e:
            logger.exception("Error processing article: %s", e)
            return False

    # ── Main run loop ───────────────────────────────────────────────

    async def run(self) -> dict:
        stats = {
            "articles_found": 0,
            "articles_new": 0,
            "articles_processed": 0,
            "articles_failed": 0,
            "articles_skipped_duplicate": 0,
            "articles_skipped_clickbait": 0,
        }

        try:
            # -- Pre-flight check --
            if not await self.telegram.test_connection():
                logger.error("Telegram connection failed — aborting run")
                return stats

            # -- Step 1: Collect RSS --
            articles = await self.rss_parser.fetch_all()
            stats["articles_found"] = len(articles)
            logger.info("RSS collected: %d articles", len(articles))

            if not articles:
                return stats

            # -- Step 2: Exact-duplicate filter (by URL) --
            new_articles = [a for a in articles if not self.db.is_processed(a["link"])]
            stats["articles_new"] = len(new_articles)
            logger.info("After exact-dedup: %d new articles", len(new_articles))

            articles_to_process = new_articles[: self.config.max_articles_per_run]

            # -- Fetch recent titles once for semantic dedup --
            recent_titles = self.db.get_recent_titles(
                hours=self.config.dedup_lookback_hours
            )
            logger.info(
                "Loaded %d recent titles for semantic dedup (%dh window)",
                len(recent_titles),
                self.config.dedup_lookback_hours,
            )

            for i, article in enumerate(articles_to_process, 1):
                title = article.get("title", "<no title>")
                link = article.get("link", "")
                source = article.get("source", "unknown")

                logger.info(
                    "[%d/%d] Processing: %s",
                    i,
                    len(articles_to_process),
                    title[:70],
                )

                # -- Step 3: Semantic-duplicate filter --
                is_dup = await check_semantic_duplicate(
                    title, recent_titles, self.config
                )
                if is_dup:
                    logger.info("  ⊘ Skipped (semantic duplicate)")
                    self.db.mark_processed(link=link, title=title, source=source)
                    stats["articles_skipped_duplicate"] += 1
                    continue

                # -- Step 4: AI Scoring (clickbait / factuality) --
                evaluation = await self.evaluator.evaluate(article)
                logger.info(
                    "  🔍 AI Score — clickbait=%d, factuality=%d, approved=%s",
                    evaluation.clickbait_score,
                    evaluation.factuality_score,
                    evaluation.is_approved,
                )

                if not evaluation.is_approved:
                    logger.info("  ⊘ Skipped (clickbait/low factuality)")
                    self.db.mark_processed(link=link, title=title, source=source)
                    stats["articles_skipped_clickbait"] += 1
                    continue

                # -- Step 5: Summarize + Publish --
                success = await self.process_article(article)
                if success:
                    self.db.mark_processed(link=link, title=title, source=source)
                    recent_titles.append(title)
                    stats["articles_processed"] += 1
                else:
                    stats["articles_failed"] += 1

                # Throttle between articles
                if i < len(articles_to_process):
                    await asyncio.sleep(3)

            # -- Summary --
            db_stats = self.db.get_stats()
            logger.info(
                "═══ Run complete ═══  "
                "found=%d | new=%d | published=%d | dup_skip=%d | "
                "clickbait_skip=%d | failed=%d | DB total=%d",
                stats["articles_found"],
                stats["articles_new"],
                stats["articles_processed"],
                stats["articles_skipped_duplicate"],
                stats["articles_skipped_clickbait"],
                stats["articles_failed"],
                db_stats["total"],
            )

        finally:
            await self.telegram.close()
            await self.image_extractor.close()

        return stats


def run_cli():
    """CLI entry point for Flux-Titan."""
    print("═══════════════════════════════════════════")
    print("  Flux-Titan v0.2 — AI Newsroom Pipeline  ")
    print("═══════════════════════════════════════════")
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
