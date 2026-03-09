"""
Summarization module using Google Gemini API.
Converts news into "Business Insights" format.
Includes tenacity retry for resilience.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, GenerationConfig
from google.api_core import exceptions as google_exceptions
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseSummarizer

logger = logging.getLogger("NewsBot.Summarizer")


class GeminiSummarizer(BaseSummarizer):
    """
    Summarizes articles using Google Gemini API.
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

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """
        Gemini client initialization.
        
        Args:
            api_key: Google AI API key
            model: Gemini model name
        """
        self.api_key = api_key
        self.model_name = model
        self._model = None
        self._configure()

    def _configure(self) -> None:
        """Gemini API configuration."""
        try:
            genai.configure(api_key=self.api_key)
            
            # Safety settings (allow news content)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
            
            # Generation parameters
            generation_config = GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                max_output_tokens=1024,
            )
            
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config,
                safety_settings=safety_settings,
                system_instruction=self.SYSTEM_INSTRUCTION,
            )
            
            logger.info(f"Gemini model initialized: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Gemini initialization error: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _generate_sync(self, prompt: str) -> Optional[str]:
        """
        Synchronous generation (for running in thread pool).
        Wrapped with @retry for network resilience.
        
        Args:
            prompt: prepared prompt
            
        Returns:
            Generated text or None
        """
        try:
            response = self._model.generate_content(prompt)
            
            # Check if response is blocked
            if not response.parts:
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    logger.warning(f"Gemini blocked the response: {response.prompt_feedback.block_reason}")
                return None
            
            return response.text
            
        except google_exceptions.InvalidArgument as e:
            logger.error(f"Gemini: invalid argument - {e}")
            raise
        except google_exceptions.ResourceExhausted as e:
            logger.error(f"Gemini: quota exceeded - {e}")
            raise
        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Gemini API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected Gemini error: {e}")
            raise

    async def summarize(self, article: Dict[str, Any]) -> Optional[str]:
        """
        Asynchronous article summarization.
        
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
                content=article.get("content", article.get("summary", ""))[:1500],
                link=article.get("link", ""),
            )
            
            # Run synchronous Gemini in thread pool
            result = await asyncio.to_thread(self._generate_sync, prompt)
            
            if result:
                # Clean potential markdown artifacts
                result = self._clean_response(result)
                return result.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return None

    @staticmethod
    def _clean_response(text: str) -> str:
        """Clean markdown artifacts from the response."""
        import re
        
        # Remove code blocks if present
        text = re.sub(r'^```html?\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()
