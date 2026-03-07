"""
Abstract base classes for summarizers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

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
