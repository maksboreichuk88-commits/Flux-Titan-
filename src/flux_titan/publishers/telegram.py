"""
Telegram message publishing module.
Supports sending text with images.
"""

import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger("NewsBot.Telegram")


class TelegramPoster:
    """
    Sends messages to a Telegram channel.
    Uses HTTP API for simplicity and reliability.
    """

    def __init__(self, token: str, channel_id: str):
        """
        Telegram bot initialization.
        
        Args:
            token: bot token from @BotFather
            channel_id: channel ID (@username or numeric ID)
        """
        self.token = token
        self.channel_id = channel_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Telegram bot initialized for channel: {channel_id}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def test_connection(self) -> bool:
        """
        Check connection to Telegram API.
        
        Returns:
            True if connection is successful
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/getMe")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_info = data["result"]
                    logger.info(f"✓ Bot connected: @{bot_info['username']}")
                    return True
            
            logger.error(f"✗ Telegram connection error: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")
            return False

    async def post(
        self,
        text: str,
        image_url: Optional[str] = None,
        disable_preview: bool = False
    ) -> bool:
        """
        Post content to the channel.
        
        Args:
            text: message text (HTML)
            image_url: image URL (optional)
            disable_preview: disable link preview
            
        Returns:
            True if posting was successful
        """
        try:
            if image_url:
                # Отправляем с изображением
                success = await self._send_with_image(text, image_url)
                if success:
                    return True
                # If image send failed, try text only
                logger.warning("Failed to send with image, trying text only")
            
            # Send text only
            return await self._send_text(text, disable_preview)
            
        except Exception as e:
            logger.error(f"Posting error: {e}")
            return False

    async def _send_text(self, text: str, disable_preview: bool = False) -> bool:
        """
        Send a text message.
        
        Args:
            text: message text
            disable_preview: disable preview
            
        Returns:
            True if successful
        """
        try:
            client = await self._get_client()
            
            # Check message length
            if len(text) > 4096:
                text = text[:4000] + "\n\n<i>... (message truncated)</i>"
                logger.warning("Message was truncated due to length limit")
            
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
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Text send error: {e}")
            return False

    async def _send_with_image(self, text: str, image_url: str) -> bool:
        """
        Send a message with an image.
        
        Args:
            text: caption text
            image_url: image URL
            
        Returns:
            True if successful
        """
        try:
            client = await self._get_client()
            
            # Telegram limits caption to 1024 characters
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
                logger.warning(f"Photo send error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.warning(f"Could not load image: {e}")
            return False

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("Telegram session closed")
