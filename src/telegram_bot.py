"""
Модуль отправки сообщений в Telegram.
Поддерживает отправку текста с изображениями.
"""

import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger("NewsBot.Telegram")


class TelegramPoster:
    """
    Отправка сообщений в Telegram-канал.
    Использует HTTP API для простоты и надежности.
    """

    def __init__(self, token: str, channel_id: str):
        """
        Инициализация Telegram бота.
        
        Args:
            token: токен бота от @BotFather
            channel_id: ID канала (@username или числовой ID)
        """
        self.token = token
        self.channel_id = channel_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Telegram бот инициализирован для канала: {channel_id}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Ленивая инициализация HTTP клиента."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def test_connection(self) -> bool:
        """
        Проверка подключения к Telegram API.
        
        Returns:
            True если подключение успешно
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/getMe")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_info = data["result"]
                    logger.info(f"✓ Бот подключен: @{bot_info['username']}")
                    return True
            
            logger.error(f"✗ Ошибка подключения к Telegram: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"✗ Неожиданная ошибка: {e}")
            return False

    async def post(
        self,
        text: str,
        image_url: Optional[str] = None,
        disable_preview: bool = False
    ) -> bool:
        """
        Отправка поста в канал.
        
        Args:
            text: текст сообщения (HTML)
            image_url: URL изображения (опционально)
            disable_preview: отключить превью ссылок
            
        Returns:
            True если отправка успешна
        """
        try:
            if image_url:
                # Отправляем с изображением
                success = await self._send_with_image(text, image_url)
                if success:
                    return True
                # Если не удалось с изображением, пробуем без
                logger.warning("Не удалось отправить с изображением, пробуем без")
            
            # Отправляем только текст
            return await self._send_text(text, disable_preview)
            
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            return False

    async def _send_text(self, text: str, disable_preview: bool = False) -> bool:
        """
        Отправка текстового сообщения.
        
        Args:
            text: текст сообщения
            disable_preview: отключить превью
            
        Returns:
            True если успешно
        """
        try:
            client = await self._get_client()
            
            # Проверяем длину сообщения
            if len(text) > 4096:
                text = text[:4000] + "\n\n<i>... (сообщение обрезано)</i>"
                logger.warning("Сообщение было обрезано из-за лимита")
            
            data = {
                "chat_id": self.channel_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_preview
            }
            
            response = await client.post(f"{self.base_url}/sendMessage", json=data)
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка отправки текста: {e}")
            return False

    async def _send_with_image(self, text: str, image_url: str) -> bool:
        """
        Отправка сообщения с изображением.
        
        Args:
            text: текст (caption)
            image_url: URL изображения
            
        Returns:
            True если успешно
        """
        try:
            client = await self._get_client()
            
            # Telegram ограничивает caption до 1024 символов
            caption = text[:1024] if len(text) > 1024 else text
            
            data = {
                "chat_id": self.channel_id,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML"
            }
            
            response = await client.post(f"{self.base_url}/sendPhoto", json=data)
            
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Ошибка отправки фото: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.warning(f"Не удалось загрузить изображение: {e}")
            return False

    async def close(self):
        """Закрытие HTTP клиента."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("Telegram сессия закрыта")
