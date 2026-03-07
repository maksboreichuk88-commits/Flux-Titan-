"""
Module for extracting images from articles.
Parses og:image and other meta tags.
"""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urljoin

import httpx

logger = logging.getLogger("NewsBot.ImageExtractor")


class ImageExtractor:
    """
    Extracts og:image and other images from web pages.
    Uses httpx for asynchronous requests.
    """

    # Patterns for image search
    OG_IMAGE_PATTERNS = [
        # og:image (primary)
        re.compile(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            re.IGNORECASE
        ),
        re.compile(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            re.IGNORECASE
        ),
        # twitter:image
        re.compile(
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            re.IGNORECASE
        ),
        re.compile(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
            re.IGNORECASE
        ),
    ]
    
    # Headers to mimic a browser
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, timeout: float = 15.0):
        """
        Extractor initialization.
        
        Args:
            timeout: request timeout in seconds
        """
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.HEADERS,
            )
        return self._client

    async def extract(self, url: str) -> Optional[str]:
        """
        Extract og:image from the given URL.
        
        Args:
            url: page URL to parse
            
        Returns:
            Image URL or None
        """
        try:
            client = await self._get_client()
            
            # Load only the beginning of the page (enough for meta tags)
            response = await client.get(
                url,
                headers={"Range": "bytes=0-50000"}  # First 50KB
            )
            response.raise_for_status()
            
            html = response.text
            
            # Search for image using patterns
            for pattern in self.OG_IMAGE_PATTERNS:
                match = pattern.search(html)
                if match:
                    image_url = match.group(1)
                    
                    # Преобразуем относительные URL в абсолютные
                    if not image_url.startswith(("http://", "https://")):
                        image_url = urljoin(url, image_url)
                    
                    # Validate that the URL is likely an image                    if self._is_valid_image_url(image_url):
                        return image_url
            
            logger.debug(f"og:image not found for {url[:50]}...")
            return None
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code}: {url[:50]}...")
            return None
        except httpx.TimeoutException:
            logger.warning(f"Download timeout: {url[:50]}...")
            return None
        except Exception as e:
            logger.warning(f"Image extraction error: {e}")
            return None

    @staticmethod
    def _is_valid_image_url(url: str) -> bool:
        """Check if the URL likely points to an image."""
        if not url or len(url) < 10:
            return False
        
        # Check extensions or known CDNs
        valid_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp")
        valid_domains = ("imgur", "cloudinary", "wp.com", "medium.com", "cdn")
        
        url_lower = url.lower()
        
        # Check extensions
        if any(url_lower.endswith(ext) or f"{ext}?" in url_lower for ext in valid_extensions):
            return True
        
        # Check known CDNs
        if any(domain in url_lower for domain in valid_domains):
            return True
        
        # If URL looks like an image (contains image/img/photo etc.)
        if any(keyword in url_lower for keyword in ("image", "img", "photo", "media", "upload")):
            return True
        
        return False

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
