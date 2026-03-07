import os
import yaml
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Load .env file (for local development)
load_dotenv()

logger = logging.getLogger("NewsBot.Config")

# Predefined RSS feeds
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
    Immutable application configuration.
    All secrets are loaded from environment variables.
    """
    
    # Required parameters
    telegram_token: str
    channel_id: str
    
    # Optional parameters with default values
    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    database_path: str = "processed.db"
    feeds_config_path: str = "feeds.yaml"
    max_articles_per_run: int = 5
    rss_feeds: tuple = field(default_factory=lambda: tuple(DEFAULT_RSS_FEEDS))
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Factory method to create configuration from env variables.
        
        Raises:
            ValueError: if required variables are missing
        """
        telegram_token = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        channel_id = os.getenv("CHANNEL_ID")
        ai_provider = os.getenv("AI_PROVIDER", "gemini").lower()
        
        gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Validation of required variables
        missing = []
        if not telegram_token:
            missing.append("TELEGRAM_BOT_TOKEN or TG_TOKEN")
        if not channel_id:
            missing.append("CHANNEL_ID")
            
        if ai_provider == "gemini" and not gemini_api_key:
            missing.append("GEMINI_API_KEY (required for Gemini)")
        elif ai_provider == "openai" and not openai_api_key:
            missing.append("OPENAI_API_KEY (required for OpenAI)")
        elif ai_provider not in ("gemini", "openai"):
            raise ValueError(f"Unsupported AI_PROVIDER: {ai_provider}. Must be 'gemini' or 'openai'.")
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        
        # 1. Start with hardcoded defaults
        rss_feeds = list(DEFAULT_RSS_FEEDS)
        
        # 2. Add feeds from YAML file if exists
        feeds_config_path = os.getenv("FEEDS_CONFIG_PATH", "feeds.yaml")
        if os.path.exists(feeds_config_path):
            yaml_feeds = cls._load_feeds_from_yaml(feeds_config_path)
            rss_feeds.extend(yaml_feeds)
            logger.info(f"Loaded {len(yaml_feeds)} feeds from {feeds_config_path}")
        
        # 3. Add feeds from CUSTOM_RSS_FEEDS (backward compatibility)
        custom_feeds = os.getenv("CUSTOM_RSS_FEEDS")
        if custom_feeds:
            # Format: "Name1|URL1,Name2|URL2"
            env_feeds_count = 0
            for feed_str in custom_feeds.split(","):
                parts = feed_str.strip().split("|")
                if len(parts) >= 2:
                    rss_feeds.append({
                        "name": parts[0].strip(),
                        "url": parts[1].strip(),
                        "icon": parts[2].strip() if len(parts) > 2 else "📰"
                    })
                    env_feeds_count += 1
            if env_feeds_count > 0:
                logger.info(f"Loaded {env_feeds_count} feeds from CUSTOM_RSS_FEEDS")
        
        return cls(
            telegram_token=telegram_token,
            channel_id=channel_id,
            ai_provider=ai_provider,
            gemini_api_key=gemini_api_key,
            gemini_model=os.getenv("GEMINI_MODEL", cls.gemini_model),
            openai_api_key=openai_api_key,
            openai_model=os.getenv("OPENAI_MODEL", cls.openai_model),
            database_path=os.getenv("DATABASE_PATH", cls.database_path),
            feeds_config_path=feeds_config_path,
            max_articles_per_run=int(
                os.getenv("MAX_ARTICLES_PER_RUN", str(cls.max_articles_per_run))
            ),
            rss_feeds=tuple(rss_feeds),
        )

    @staticmethod
    def _load_feeds_from_yaml(path: str) -> List[Dict[str, str]]:
        """Loads feeds from a YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not data or "feeds" not in data:
                    return []
                
                valid_feeds = []
                for entry in data["feeds"]:
                    if "name" in entry and "url" in entry:
                        valid_feeds.append({
                            "name": str(entry["name"]),
                            "url": str(entry["url"]),
                            "icon": str(entry.get("icon", "📰"))
                        })
                return valid_feeds
        except Exception as e:
            logger.error(f"Error loading YAML feeds from {path}: {e}")
            return []
