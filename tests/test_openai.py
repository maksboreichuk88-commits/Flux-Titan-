from unittest.mock import MagicMock, patch

import pytest

from flux_titan.summarizers.openai import OpenAISummarizer


@pytest.fixture
def openai_summarizer():
    return OpenAISummarizer(api_key="test_key", model="gpt-4o-mini")


def test_openai_client_init_with_base_url():
    with patch("flux_titan.summarizers.openai.OpenAI") as mock_openai:
        OpenAISummarizer(
            api_key="test_key",
            model="gpt-4o-mini",
            base_url="https://example.com/v1",
        )

    mock_openai.assert_called_once_with(
        api_key="test_key",
        base_url="https://example.com/v1",
    )


@pytest.mark.asyncio
async def test_openai_summarize_success(openai_summarizer):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="<b>Test Summary</b>\n#AI\n<a href='http://link'>Read more</a>"))
    ]

    with patch.object(
        openai_summarizer.client.chat.completions,
        "create",
        return_value=mock_response,
    ) as mock_create:
        article = {
            "title": "Test Title",
            "link": "http://link",
            "content": "Test content for summarization.",
            "source": "Test Source",
            "source_icon": "lab",
        }

        result = await openai_summarizer.summarize(article)

        assert result is not None
        assert "<b>Test Summary</b>" in result
        assert "http://link" in result
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_openai_summarize_failure(openai_summarizer):
    with patch.object(
        openai_summarizer.client.chat.completions,
        "create",
        side_effect=Exception("API Error"),
    ):
        article = {"title": "Test", "link": "http://test"}
        result = await openai_summarizer.summarize(article)
        assert result is None


def test_clean_response():
    input_text = "```html\n<b>Text</b>\n```"
    cleaned = OpenAISummarizer._clean_response(input_text)
    assert cleaned == "<b>Text</b>"
