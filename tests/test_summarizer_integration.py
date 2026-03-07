import pytest
from unittest.mock import MagicMock, patch
from flux_titan.summarizers.gemini import GeminiSummarizer
from flux_titan.summarizers.openai import OpenAISummarizer

@pytest.fixture
def article():
    return {
        "title": "AI Revolution",
        "link": "https://example.com/ai",
        "content": "Artificial Intelligence is changing the world rapidly.",
        "source": "TechNews",
        "source_icon": "🤖"
    }

@pytest.mark.asyncio
async def test_gemini_summarizer_integration(article):
    # Mocking google.generativeai.GenerativeModel.generate_content
    with patch("google.generativeai.GenerativeModel.generate_content") as mock_gen:
        mock_response = MagicMock()
        mock_response.text = "<b>AI Transformation</b>\n\nAI is evolving.\n\n#AI #Tech\n<a href='https://example.com/ai'>Source</a>"
        mock_response.parts = [MagicMock()] # To pass the "not response.parts" check
        mock_gen.return_value = mock_response
        
        summarizer = GeminiSummarizer(api_key="fake_key")
        # We need to manually set the mock model since __init__ configures it
        summarizer._model = MagicMock()
        summarizer._model.generate_content.return_value = mock_response

        result = await summarizer.summarize(article)
        
        assert result is not None
        assert "AI Transformation" in result
        assert "#AI" in result
        assert article["link"] in result

@pytest.mark.asyncio
async def test_openai_summarizer_integration(article):
    # Mocking OpenAI client
    with patch("flux_titan.summarizers.openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="<b>OpenAI Insights</b>\n\nGPT is powerful.\n\n#OpenAI\n<a href='https://example.com/ai'>Source</a>"))
        ]
        mock_client.chat.completions.create.return_value = mock_completion
        
        summarizer = OpenAISummarizer(api_key="fake_key")
        result = await summarizer.summarize(article)
        
        assert result is not None
        assert "OpenAI Insights" in result
        assert "#OpenAI" in result
        assert article["link"] in result

def test_clean_response_markdown_artifacts():
    html_with_markdown = "```html\n<b>Hello</b>\n```"
    result = GeminiSummarizer._clean_response(html_with_markdown)
    assert result == "<b>Hello</b>"
    
    result_openai = OpenAISummarizer._clean_response(html_with_markdown)
    assert result_openai == "<b>Hello</b>"
