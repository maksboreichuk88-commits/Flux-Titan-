"""
Module for resolving article images through a lightweight fallback chain.

Current and intended order:
1. Prefer the original article image from page metadata
2. Add a public image source fallback later
3. Keep generated images as a future last resort
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, Sequence
from urllib.parse import urljoin

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger("NewsBot.ImageExtractor")


OG_IMAGE_PATTERNS = [
    re.compile(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        re.IGNORECASE,
    ),
]


@dataclass
class ImageLookupContext:
    """Mutable context shared by image lookup strategies."""

    article_url: str
    title: str = ""
    source: str = ""
    article: Mapping[str, Any] = field(default_factory=dict)
    html: Optional[str] = None


class ImageStrategy(Protocol):
    """Small contract for ordered image lookup strategies."""

    name: str

    async def resolve(
        self,
        context: ImageLookupContext,
        client: httpx.AsyncClient,
    ) -> Optional[str]:
        """Return an image URL or None."""


class ArticleMetadataImageStrategy:
    """
    Prefer the original article image exposed through page metadata.

    This is the first strategy in the chain. Future strategies can add:
    1. a public image source fallback
    2. a generated-image fallback as a last resort
    """

    name = "article_metadata"

    def __init__(self, patterns: Sequence[re.Pattern[str]] | None = None):
        self.patterns = tuple(patterns or OG_IMAGE_PATTERNS)

    async def resolve(
        self,
        context: ImageLookupContext,
        client: httpx.AsyncClient,
    ) -> Optional[str]:
        html = await self._load_article_html(context, client)
        if not html:
            return None

        for pattern in self.patterns:
            match = pattern.search(html)
            if not match:
                continue

            image_url = match.group(1)
            if not image_url.startswith(("http://", "https://")):
                image_url = urljoin(context.article_url, image_url)

            if ImageExtractor._is_valid_image_url(image_url):
                return image_url

        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _fetch_html_with_retry(self, context: ImageLookupContext, client: httpx.AsyncClient) -> httpx.Response:
        """Fetch HTML with explicit retry rules for transit and status errors."""
        response = await client.get(
            context.article_url,
            headers={"Range": "bytes=0-50000"},
        )
        
        # We explicitly want to retry on 403 (Cloudflare challenge often transient or rotates IP/headers), 502, 503, 504
        if response.status_code in (403, 502, 503, 504):
            response.raise_for_status() # this will throw HTTPStatusError and trigger tenacity retry
            
        return response

    async def _load_article_html(
        self,
        context: ImageLookupContext,
        client: httpx.AsyncClient,
    ) -> Optional[str]:
        if context.html is not None:
            return context.html or None

        try:
            response = await self._fetch_html_with_retry(context, client)
            # Raise for any other 4xx/5xx that wasn't retried
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "HTTP error %s while loading image candidates: %s",
                exc.response.status_code,
                _short_url(context.article_url),
            )
            context.html = ""
            return None
        except httpx.TimeoutException:
            logger.warning(
                "Image candidate fetch timeout: %s",
                _short_url(context.article_url),
            )
            context.html = ""
            return None
        except Exception as exc:
            logger.warning(
                "Image candidate fetch error for %s: %s",
                _short_url(context.article_url),
                exc,
            )
            context.html = ""
            return None

        context.html = response.text
        return context.html


def _short_url(url: str) -> str:
    if len(url) <= 50:
        return url
    return f"{url[:50]}..."


class ImageExtractor:
    """
    Resolve images through an ordered fallback chain.

    Current active order:
    1. Original article image from page metadata

    Planned future order:
    2. Public image source fallback
    3. Generated image fallback as a last resort
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }

    def __init__(
        self,
        timeout: float = 15.0,
        strategies: Sequence[ImageStrategy] | None = None,
    ):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self.strategies = list(strategies or [ArticleMetadataImageStrategy()])

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of the shared HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.HEADERS,
            )
        return self._client

    async def resolve(self, article: Mapping[str, Any]) -> Optional[str]:
        """
        Resolve an image URL for an article through the ordered strategy chain.
        """
        article_url = str(article.get("link", "")).strip()
        if not article_url:
            logger.debug("Image resolution skipped because article link is missing")
            return None

        context = ImageLookupContext(
            article_url=article_url,
            title=str(article.get("title", "")),
            source=str(article.get("source", "")),
            article=article,
        )
        client = await self._get_client()

        for strategy in self.strategies:
            try:
                image_url = await strategy.resolve(context, client)
            except Exception as exc:
                logger.warning(
                    "Image strategy %s failed for %s: %s",
                    strategy.name,
                    _short_url(article_url),
                    exc,
                )
                continue

            if image_url:
                logger.debug(
                    "Image resolved using strategy %s for %s",
                    strategy.name,
                    _short_url(article_url),
                )
                return image_url

        logger.debug("Image fallback chain found no image for %s", _short_url(article_url))
        return None

    async def extract(self, url: str) -> Optional[str]:
        """
        Backward-compatible wrapper around resolve().
        """
        return await self.resolve({"link": url})

    @staticmethod
    def _is_valid_image_url(url: str) -> bool:
        """Check whether a URL is likely to point to an image."""
        if not url or len(url) < 10:
            return False

        valid_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp")
        valid_domains = ("imgur", "cloudinary", "wp.com", "medium.com", "cdn")
        url_lower = url.lower()

        if any(url_lower.endswith(ext) or f"{ext}?" in url_lower for ext in valid_extensions):
            return True

        if any(domain in url_lower for domain in valid_domains):
            return True

        if any(keyword in url_lower for keyword in ("image", "img", "photo", "media", "upload")):
            return True

        return False

    async def close(self):
        """Close the shared HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
