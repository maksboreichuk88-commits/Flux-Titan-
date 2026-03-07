"""
Summarization module using OpenAI API.
Converts news into "Business Insights" format.
"""

import logging
from typing import Optional, Dict, Any

from openai import OpenAI
from .base import BaseSummarizer

logger = logging.getLogger("NewsBot.Summarizer.OpenAI")


class OpenAISummarizer(BaseSummarizer):
    """
    Summarizes articles using OpenAI API (GPT models).
    Generates professional content for a Telegram channel.
    """

    SYSTEM_INSTRUCTION = """You are an editor of a technology and business Telegram news channel.
Your task is to turn news into concise, informative, and engaging posts.

RULES:
• Write in RUSSIAN language
• Use only Telegram HTML: <b>bold</b>, <i>italic</i>, <a href="url">link</a>
• DO NOT use Markdown (**, ##, ```)
• Be concise but informative
• Use emojis appropriately
• Focus on the essence: what happened and why it matters"""

    SUMMARIZE_PROMPT = """Convert this news item into a Telegram channel post.

**POST STRUCTURE:**
1. {source_icon} <b>Engaging Headline</b> (max 10 words)
2. Empty line
3. Core essence (2-3 sentences, 50-80 words)
4. Why it matters (1-2 sentences)
5. Empty line
6. 2-3 relevant hashtags (#AI #Tech #Business)
7. 🔗 <a href="{link}">Read full article</a>

**STYLE:**
• Professional but lively
• Specific numbers and facts
• No fluff or clichés

---
**SOURCE:** {source}
**TITLE:** {title}
**AUTHOR:** {author}
**CONTENT:** {content}
---

Write the post (HTML only, no explanations):"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        OpenAI client initialization.
        
        Args:
            api_key: OpenAI API key
            model: GPT model name
        """
        self.api_key = api_key
        self.model_name = model
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"OpenAI summarizer initialized with model: {self.model_name}")

    async def summarize(self, article: Dict[str, Any]) -> Optional[str]:
        """
        Asynchronous article summarization using OpenAI.
        
        Args:
            article: dictionary with article data
            
        Returns:
            Prepared Telegram post or None
        """
        try:
            prompt = self.SUMMARIZE_PROMPT.format(
                source=article.get("source", "Unknown"),
                source_icon=article.get("source_icon", "📰"),
                title=article.get("title", ""),
                author=article.get("author", "Редакция"),
                content=article.get("content", article.get("summary", ""))[:3000],
                link=article.get("link", ""),
            )
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            result = response.choices[0].message.content
            
            if result:
                # Clean potential markdown artifacts
                result = self._clean_response(result)
                return result.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"OpenAI summarization error: {e}")
            return None

    @staticmethod
    def _clean_response(text: str) -> str:
        """Clean markdown artifacts from the response."""
        import re
        
        # Remove code blocks if present
        text = re.sub(r'^```html?\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()
