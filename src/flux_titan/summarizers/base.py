"""
Abstract base classes for summarizers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from tenacity import retry, stop_after_attempt, wait_exponential


def summarizer_retry(func):
    """Shared retry decorator for all summarizer network calls."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )(func)


class BaseSummarizer(ABC):
    """
    Abstract interface for AI summarizer providers.
    """
    
    @abstractmethod
    async def summarize(self, article: Dict[str, Any]) -> Optional[str]:
        """
        Summarize an article for publishing.
        
        Args:
            article: dict containing title, link, content, source, etc.
            
        Returns:
            Formatted text string or None if failed.
        """
        pass
