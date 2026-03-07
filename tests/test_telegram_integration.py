import pytest
import httpx
from unittest.mock import AsyncMock, patch
from flux_titan.publishers.telegram import TelegramPoster

@pytest.fixture
def telegram_poster():
    return TelegramPoster(token="fake_token", channel_id="@test_channel")

@pytest.mark.asyncio
async def test_telegram_send_text_success(telegram_poster):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(200, json={"ok": True})
        
        result = await telegram_poster.post("<b>Hello Test</b>")
        
        assert result is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["text"] == "<b>Hello Test</b>"
        assert kwargs["json"]["chat_id"] == "@test_channel"

@pytest.mark.asyncio
async def test_telegram_send_with_image_success(telegram_poster):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(200, json={"ok": True})
        
        result = await telegram_poster.post("Caption", image_url="https://example.com/img.jpg")
        
        assert result is True
        # Check call to sendPhoto
        assert "sendPhoto" in mock_post.call_args[0][0]
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["photo"] == "https://example.com/img.jpg"
        assert kwargs["json"]["caption"] == "Caption"

@pytest.mark.asyncio
async def test_telegram_send_truncated_text(telegram_poster):
    long_text = "A" * 5000
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(200, json={"ok": True})
        
        await telegram_poster.post(long_text)
        
        args, kwargs = mock_post.call_args
        sent_text = kwargs["json"]["text"]
        assert len(sent_text) <= 4096
        assert "... (message truncated)" in sent_text

@pytest.mark.asyncio
async def test_telegram_fallback_on_image_error(telegram_poster):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # First call (sendPhoto) fails, second call (sendMessage) succeeds
        mock_post.side_effect = [
            httpx.Response(400, text="Bad Request"),
            httpx.Response(200, json={"ok": True})
        ]
        
        result = await telegram_poster.post("Important News", image_url="http://bad.img")
        
        assert result is True
        assert mock_post.call_count == 2
        # Verify first call was photo, second was text
        assert "sendPhoto" in mock_post.call_args_list[0][0][0]
        assert "sendMessage" in mock_post.call_args_list[1][0][0]

@pytest.mark.asyncio
async def test_telegram_api_error(telegram_poster):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(500, text="Server Error")
        
        result = await telegram_poster.post("Failure")
        
        assert result is False


@pytest.mark.asyncio
async def test_telegram_retries_text_on_temporary_api_error(telegram_poster):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("flux_titan.publishers.telegram.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_post.side_effect = [
            httpx.Response(429, text="Too Many Requests"),
            httpx.Response(200, json={"ok": True}),
        ]

        result = await telegram_poster.post("Retry me")

        assert result is True
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()
