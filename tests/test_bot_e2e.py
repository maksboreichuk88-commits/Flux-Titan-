import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from flux_titan.cli import NewsBot
from flux_titan.config import Config

@pytest.fixture
def mock_config():
    return Config(
        telegram_token="fake_token",
        channel_id="@test_channel",
        gemini_api_key="fake_gemini",
        database_path=":memory:"  # Use in-memory SQLite for tests
    )

@pytest.mark.asyncio
async def test_newsbot_full_cycle_success(mock_config):
    # Mocking components
    with patch("flux_titan.feeds.RSSParser.fetch_all") as mock_fetch, \
         patch("flux_titan.image_extractor.ImageExtractor.extract") as mock_extract, \
         patch("flux_titan.summarizers.gemini.GeminiSummarizer.summarize") as mock_summarize, \
         patch("flux_titan.publishers.telegram.TelegramPoster.post") as mock_post, \
         patch("flux_titan.publishers.telegram.TelegramPoster.test_connection") as mock_conn:
        
        # Setup mocks
        mock_conn.return_value = True
        mock_fetch.return_value = [
            {"title": "New Tech", "link": "https://tech.com/1", "source": "Tech"}
        ]
        mock_extract.return_value = "https://tech.com/img.jpg"
        mock_summarize.return_value = "<b>Summary</b>"
        mock_post.return_value = True
        
        bot = NewsBot(mock_config)
        # Ensure we use the in-memory DB configured in fixture
        
        stats = await bot.run()
        
        # Verify stats
        assert stats["articles_found"] == 1
        assert stats["articles_processed"] == 1
        assert stats["articles_failed"] == 0
        
        # Verify calls
        mock_fetch.assert_called_once()
        mock_summarize.assert_called_once()
        mock_post.assert_called_once_with(text="<b>Summary</b>", image_url="https://tech.com/img.jpg")
        
        # Verify DB marks as processed (test second run)
        stats_second = await bot.run()
        assert stats_second["articles_new"] == 0
        assert stats_second["articles_processed"] == 0

@pytest.mark.asyncio
async def test_newsbot_summarization_failure(mock_config):
    with patch("flux_titan.feeds.RSSParser.fetch_all") as mock_fetch, \
         patch("flux_titan.summarizers.gemini.GeminiSummarizer.summarize") as mock_summarize, \
         patch("flux_titan.publishers.telegram.TelegramPoster.test_connection") as mock_conn:
        
        mock_conn.return_value = True
        mock_fetch.return_value = [{"title": "Fail", "link": "https://fail.com"}]
        mock_summarize.return_value = None # Failure
        
        bot = NewsBot(mock_config)
        stats = await bot.run()
        
        assert stats["articles_processed"] == 0
        assert stats["articles_failed"] == 1
