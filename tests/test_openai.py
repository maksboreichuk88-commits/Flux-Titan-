import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from flux_titan.summarizers.openai import OpenAISummarizer

@pytest.fixture
def openai_summarizer():
    return OpenAISummarizer(api_key="test_key", model="gpt-4o-mini")

@pytest.mark.asyncio
async def test_openai_summarize_success(openai_summarizer):
    # Mock the OpenAI client response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="<b>Test Summary</b>\n#AI\n<a href='http://link'>Read more</a>"))
    ]
    
    with patch.object(openai_summarizer.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        article = {
            "title": "Test Title",
            "link": "http://link",
            "content": "Test content for summarization.",
            "source": "Test Source",
            "source_icon": "🧪"
        }
        
        result = await openai_summarizer.summarize(article)
        
        assert result is not None
        assert "<b>Test Summary</b>" in result
        assert "http://link" in result
        mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_openai_summarize_failure(openai_summarizer):
    # Mock an exception
    with patch.object(openai_summarizer.client.chat.completions, 'create', side_effect=Exception("API Error")):
        article = {"title": "Test", "link": "http://test"}
        result = await openai_summarizer.summarize(article)
        assert result is None

def test_clean_response():
    input_text = "```html\n<b>Text</b>\n```"
    cleaned = OpenAISummarizer._clean_response(input_text)
    assert cleaned == "<b>Text</b>"


@pytest.mark.asyncio
async def test_openai_summarize_retries_on_temporary_error(openai_summarizer):
    class TemporaryRateLimitError(Exception):
        def __init__(self):
            self.status_code = 429
            super().__init__("rate limited")

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="<b>Retry Success</b>"))
    ]

    with patch.object(
        openai_summarizer.client.chat.completions,
        'create',
        side_effect=[TemporaryRateLimitError(), mock_response],
    ) as mock_create, patch('flux_titan.summarizers.openai.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        article = {"title": "Test", "link": "http://link"}
        result = await openai_summarizer.summarize(article)

        assert result == "<b>Retry Success</b>"
        assert mock_create.call_count == 2
        mock_sleep.assert_called_once()
