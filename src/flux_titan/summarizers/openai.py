"""
Summarization module using OpenAI-compatible APIs.
Converts news into Telegram-ready newsroom posts.
Includes tenacity retry for resilience.
"""

import logging
from typing import Optional, Dict, Any

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseSummarizer

logger = logging.getLogger("NewsBot.Summarizer.OpenAI")


class OpenAISummarizer(BaseSummarizer):
    """
    Summarizes articles using OpenAI-compatible chat completion APIs.
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

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "",
        provider_name: str = "OpenAI-compatible",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ):
        """
        OpenAI-compatible client initialization.
        
        Args:
            api_key: backend API key
            model: model name
            base_url: optional base URL for OpenAI-compatible backends
                      (set via OPENAI_BASE_URL env var for local LLMs, etc.)
        """
        self.api_key = api_key
        self.model_name = model
        self.base_url = base_url
        self.provider_name = provider_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.extra_body = extra_body

        client_kwargs: Dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = OpenAI(**client_kwargs)
        logger.info(
            "%s summarizer initialized — model: %s | base_url: %s",
            self.provider_name,
            self.model_name,
            self.base_url or "(default)",
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _completion_sync(self, request_kwargs: dict) -> Optional[str]:
        """Synchronous chat completion call with retry."""
        response = self.client.chat.completions.create(**request_kwargs)
        return response.choices[0].message.content

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

            request_kwargs: dict = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            if self.top_p is not None:
                request_kwargs["top_p"] = self.top_p
            if self.extra_body:
                request_kwargs["extra_body"] = self.extra_body

            import asyncio
            result = await asyncio.to_thread(self._completion_sync, request_kwargs)
            
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
