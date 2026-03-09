from unittest.mock import patch

import pytest

from flux_titan.cli import NewsBot
from flux_titan.config import Config


@pytest.fixture
def mock_config():
    return Config(
        telegram_token="fake_token",
        channel_id="@test_channel",
        gemini_api_key="fake_gemini",
        database_path=":memory:",
    )


@pytest.mark.asyncio
async def test_newsbot_full_cycle_success(mock_config):
    with patch("flux_titan.feeds.RSSParser.fetch_all") as mock_fetch, \
         patch("flux_titan.image_extractor.ImageExtractor.resolve") as mock_resolve, \
         patch("flux_titan.summarizers.gemini.GeminiSummarizer.summarize") as mock_summarize, \
         patch("flux_titan.publishers.telegram.TelegramPoster.post") as mock_post, \
         patch("flux_titan.publishers.telegram.TelegramPoster.test_connection") as mock_conn:

        mock_conn.return_value = True
        mock_fetch.return_value = [
            {"title": "New Tech", "link": "https://tech.com/1", "source": "Tech"}
        ]
        mock_resolve.return_value = "https://tech.com/img.jpg"
        mock_summarize.return_value = "<b>Summary</b>"
        mock_post.return_value = True

        bot = NewsBot(mock_config)
        stats = await bot.run()

        assert stats["articles_found"] == 1
        assert stats["articles_processed"] == 1
        assert stats["articles_failed"] == 0

        mock_fetch.assert_called_once()
        mock_summarize.assert_called_once()
        mock_post.assert_called_once_with(text="<b>Summary</b>", image_url="https://tech.com/img.jpg")

        stats_second = await bot.run()
        assert stats_second["articles_new"] == 0
        assert stats_second["articles_processed"] == 0


@pytest.mark.asyncio
async def test_newsbot_summarization_failure(mock_config):
    with patch("flux_titan.feeds.RSSParser.fetch_all") as mock_fetch, \
         patch("flux_titan.image_extractor.ImageExtractor.resolve") as mock_resolve, \
         patch("flux_titan.summarizers.gemini.GeminiSummarizer.summarize") as mock_summarize, \
         patch("flux_titan.publishers.telegram.TelegramPoster.test_connection") as mock_conn:

        mock_conn.return_value = True
        mock_fetch.return_value = [{"title": "Fail", "link": "https://fail.com"}]
        mock_resolve.return_value = None
        mock_summarize.return_value = None

        bot = NewsBot(mock_config)
        stats = await bot.run()

        assert stats["articles_processed"] == 0
        assert stats["articles_failed"] == 1


def test_newsbot_uses_openai_compatible_backend():
    config = Config(
        telegram_token="fake_token",
        channel_id="@test_channel",
        ai_provider="openai_compatible",
        ai_provider_input="openai_compatible",
        openai_api_key="openai_key",
        openai_model="gpt-test",
        openai_base_url="https://example.com/v1",
    )

    with patch("flux_titan.cli.Database"), \
         patch("flux_titan.cli.RSSParser"), \
         patch("flux_titan.cli.ImageExtractor"), \
         patch("flux_titan.cli.TelegramPoster"), \
         patch("flux_titan.cli.OpenAISummarizer") as mock_openai:
        NewsBot(config)

    mock_openai.assert_called_once_with(
        api_key="openai_key",
        model="gpt-test",
        base_url="https://example.com/v1",
    )


def test_newsbot_routes_kimi_alias_through_compat_wrapper():
    config = Config(
        telegram_token="fake_token",
        channel_id="@test_channel",
        ai_provider="openai_compatible",
        ai_provider_input="kimi",
        openai_api_key="kimi_key",
        openai_model="moonshotai/kimi-k2.5",
        openai_base_url="https://integrate.api.nvidia.com/v1",
    )

    with patch("flux_titan.cli.Database"), \
         patch("flux_titan.cli.RSSParser"), \
         patch("flux_titan.cli.ImageExtractor"), \
         patch("flux_titan.cli.TelegramPoster"), \
         patch("flux_titan.cli.KimiSummarizer") as mock_kimi:
        NewsBot(config)

    mock_kimi.assert_called_once_with(
        api_key="kimi_key",
        model="moonshotai/kimi-k2.5",
        base_url="https://integrate.api.nvidia.com/v1",
    )
