"""
Модуль извлечения изображений из статей.
Парсит og:image и другие мета-теги.
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
    Извлекает og:image и другие изображения из веб-страниц.
    Использует httpx для асинхронных запросов.
    """

    # Паттерны для поиска изображений
    OG_IMAGE_PATTERNS = [
        # og:image (основной)
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
    
    # Заголовки для имитации браузера
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
        Инициализация экстрактора.
        
        Args:
            timeout: таймаут запроса в секундах
        """
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Ленивая инициализация HTTP клиента."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.HEADERS,
            )
        return self._client

    async def extract(self, url: str) -> Optional[str]:
        """
        Извлечение og:image из URL страницы.
        
        Args:
            url: URL страницы для парсинга
            
        Returns:
            URL изображения или None
        """
        try:
            client = await self._get_client()
            
            # Загружаем только начало страницы (достаточно для мета-тегов)
            response = await client.get(
                url,
                headers={"Range": "bytes=0-50000"}  # Первые 50KB
            )
            response.raise_for_status()
            
            html = response.text
            
            # Ищем изображение по паттернам
            for pattern in self.OG_IMAGE_PATTERNS:
                match = pattern.search(html)
                if match:
                    image_url = match.group(1)
                    
                    # Преобразуем относительные URL в абсолютные
                    if not image_url.startswith(("http://", "https://")):
                        image_url = urljoin(url, image_url)
                    
                    # Проверяем, что URL валидный
                    if self._is_valid_image_url(image_url):
                        return image_url
            
            logger.debug(f"og:image не найден для {url[:50]}...")
            return None
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP ошибка {e.response.status_code}: {url[:50]}...")
            return None
        except httpx.TimeoutException:
            logger.warning(f"Таймаут при загрузке: {url[:50]}...")
            return None
        except Exception as e:
            logger.warning(f"Ошибка извлечения изображения: {e}")
            return None

    @staticmethod
    def _is_valid_image_url(url: str) -> bool:
        """Проверка валидности URL изображения."""
        if not url or len(url) < 10:
            return False
        
        # Проверяем расширение или известные CDN
        valid_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp")
        valid_domains = ("imgur", "cloudinary", "wp.com", "medium.com", "cdn")
        
        url_lower = url.lower()
        
        # Проверяем расширение
        if any(url_lower.endswith(ext) or f"{ext}?" in url_lower for ext in valid_extensions):
            return True
        
        # Проверяем известные CDN
        if any(domain in url_lower for domain in valid_domains):
            return True
        
        # Если URL похож на изображение (содержит image/img/photo и т.д.)
        if any(keyword in url_lower for keyword in ("image", "img", "photo", "media", "upload")):
            return True
        
        return False

    async def close(self):
        """Закрытие HTTP клиента."""
        if self._client:
            await self._client.aclose()
            self._client = None
