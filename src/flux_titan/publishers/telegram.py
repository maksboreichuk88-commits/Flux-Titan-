"""
Telegram message publishing module.
Supports sending text with images.
Network calls wrapped with tenacity retry.
"""

import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

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
        Check both bot authentication and access to the target chat.

        Returns:
            True if the bot can reach Telegram and the configured chat
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/getMe")

            if response.status_code != 200 or not response.json().get("ok"):
                logger.error("Telegram connection error: %s", response.text)
                return False

            bot_info = response.json()["result"]
            logger.info("Bot connected: @%s", bot_info["username"])

            chat_response = await client.get(
                f"{self.base_url}/getChat",
                params={"chat_id": self.channel_id},
            )
            if chat_response.status_code == 200 and chat_response.json().get("ok"):
                return True

            logger.error("Telegram chat access error: %s", chat_response.text)
            return False

        except Exception as e:
            logger.error("Unexpected Telegram error: %s", e)
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
                success = await self._send_with_image(text, image_url)
                if success:
                    return True
                logger.warning("Failed to send with image, trying text only")

            return await self._send_text(text, disable_preview)

        except Exception as e:
            logger.error("Posting error: %s", e)
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _send_text(self, text: str, disable_preview: bool = False) -> bool:
        """
        Send a text message (with retry).

        Args:
            text: message text
            disable_preview: disable preview

        Returns:
            True if successful
        """
        try:
            client = await self._get_client()

            if len(text) > 4096:
                text = text[:4000] + "\n\n<i>... (message truncated)</i>"
                logger.warning("Message was truncated due to length limit")

            data = {
                "chat_id": self.channel_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_preview,
            }

            response = await client.post(f"{self.base_url}/sendMessage", json=data)

            if response.status_code == 200:
                return True

            logger.error("API Error: %s - %s", response.status_code, response.text)
            return False

        except httpx.TransportError as e:
            logger.error("Transport error (will retry): %s", e)
            raise  # let tenacity handle it
        except Exception as e:
            logger.error("Text send error: %s", e)
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _send_with_image(self, text: str, image_url: str) -> bool:
        """
        Send a message with an image (with retry).

        Args:
            text: caption text
            image_url: image URL

        Returns:
            True if successful
        """
        try:
            client = await self._get_client()

            caption = text[:1024] if len(text) > 1024 else text

            data = {
                "chat_id": self.channel_id,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML",
            }

            response = await client.post(f"{self.base_url}/sendPhoto", json=data)

            if response.status_code == 200:
                return True

            logger.warning("Photo send error: %s - %s", response.status_code, response.text)
            return False

        except httpx.TransportError as e:
            logger.warning("Transport error sending photo (will retry): %s", e)
            raise
        except Exception as e:
            logger.warning("Could not load image: %s", e)
            return False

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("Telegram session closed")
