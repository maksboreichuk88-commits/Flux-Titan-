"""
RSS feed parsing module.
Supports multiple sources with parallel loading.
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
    RSS feed parser with multiple source support.
    Uses asyncio for parallel loading.
    """

    def __init__(self, feeds: tuple):
        """
        Parser initialization.
        
        Args:
            feeds: tuple of dictionaries with RSS feed info
        """
        self.feeds = feeds
        logger.info(f"RSS parser initialized with {len(feeds)} sources")

    async def fetch_feed(self, feed_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Download a single RSS feed.
        
        Args:
            feed_info: dictionary with name, url, icon
            
        Returns:
            List of articles
        """
        name = feed_info["name"]
        url = feed_info["url"]
        icon = feed_info.get("icon", "📰")
        
        try:
            logger.debug(f"Loading RSS: {name}")
            
            # feedparser is synchronous, wrap in thread
            loop = asyncio.get_running_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            
            # Check for parsing errors
            if feed.bozo:
                logger.warning(f"RSS warning [{name}]: {feed.bozo_exception}")
            
            articles = []
            for entry in feed.entries[:10]:  # Take only last 10
                article = {
                    "title": self._clean_text(entry.get("title", "No Title")),
                    "link": entry.get("link", ""),
                    "summary": self._clean_html(entry.get("summary", "")),
                    "published": self._parse_date(entry.get("published")),
                    "author": entry.get("author", ""),
                    "source": name,
                    "source_icon": icon,
                }
                
                # Extract content if available
                if hasattr(entry, "content") and entry.content:
                    article["content"] = self._clean_html(
                        entry.content[0].get("value", "")
                    )
                else:
                    article["content"] = article["summary"]
                
                articles.append(article)
            
            logger.info(f"✓ {name}: loaded {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"✗ {name}: load error - {e}")
            return []

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """
        Parallel download of all RSS feeds.
        
        Returns:
            Aggregated list of articles, sorted by date
        """
        logger.info(f"Loading {len(self.feeds)} RSS feeds...")
        
        # Start all tasks in parallel
        tasks = [self.fetch_feed(feed) for feed in self.feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        all_articles = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task error: {result}")
            elif isinstance(result, list):
                all_articles.extend(result)
        
        # Sort by date (newest first)
        all_articles.sort(
            key=lambda x: x.get("published") or datetime.min,
            reverse=True
        )
        
        logger.info(f"Total loaded {len(all_articles)} articles from {len(self.feeds)} sources")
        return all_articles

    @staticmethod
    def _clean_html(text: str) -> str:
        """Remove HTML tags and clean text."""
        if not text:
            return ""
        
        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        # Decode HTML entities
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
        
        # Limit length
        return clean[:2000]

    @staticmethod
    def _clean_text(text: str) -> str:
        """Basic text cleaning."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse date from various formats."""
        if not date_str:
            return datetime.now()
        
        # feedparser usually provides parsed time tuple
        try:
            from time import mktime
            import feedparser
            parsed = feedparser._parse_date(date_str)
            if parsed:
                return datetime.fromtimestamp(mktime(parsed))
        except Exception:
            pass
        
        return datetime.now()
