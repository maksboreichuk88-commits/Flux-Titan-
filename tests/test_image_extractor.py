import httpx
import pytest

from flux_titan.image_extractor import ImageExtractor


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200, url: str = "https://example.com/story"):
        self.text = text
        self.status_code = status_code
        self.url = url

    def raise_for_status(self):
        if self.status_code < 400:
            return

        request = httpx.Request("GET", self.url)
        response = httpx.Response(self.status_code, request=request, text=self.text)
        raise httpx.HTTPStatusError("request failed", request=request, response=response)


class DummyClient:
    def __init__(self, response: FakeResponse | None = None, exc: Exception | None = None):
        self.response = response or FakeResponse("")
        self.exc = exc
        self.calls = []

    async def get(self, url: str, headers=None):
        self.calls.append({"url": url, "headers": headers})
        if self.exc:
            raise self.exc
        return self.response

    async def aclose(self):
        return None


class DummyStrategy:
    def __init__(self, name: str, result: str | None = None, calls=None, exc: Exception | None = None):
        self.name = name
        self.result = result
        self.calls = calls if calls is not None else []
        self.exc = exc

    async def resolve(self, context, client):
        self.calls.append(self.name)
        if self.exc:
            raise self.exc
        return self.result


@pytest.mark.asyncio
async def test_resolve_returns_valid_og_image():
    extractor = ImageExtractor()
    extractor._client = DummyClient(
        FakeResponse('<meta property="og:image" content="https://example.com/cover.jpg">')
    )

    image_url = await extractor.resolve({"link": "https://example.com/story"})

    assert image_url == "https://example.com/cover.jpg"


@pytest.mark.asyncio
async def test_resolve_normalizes_relative_metadata_image_url():
    extractor = ImageExtractor()
    extractor._client = DummyClient(
        FakeResponse('<meta property="og:image" content="/images/cover.jpg">')
    )

    image_url = await extractor.resolve({"link": "https://example.com/story"})

    assert image_url == "https://example.com/images/cover.jpg"


@pytest.mark.asyncio
async def test_resolve_returns_none_for_invalid_metadata_candidate():
    extractor = ImageExtractor()
    extractor._client = DummyClient(
        FakeResponse('<meta property="og:image" content="https://example.com/file.txt">')
    )

    image_url = await extractor.resolve({"link": "https://example.com/story"})

    assert image_url is None


@pytest.mark.asyncio
async def test_resolve_uses_first_successful_strategy_in_order():
    calls = []
    extractor = ImageExtractor(
        strategies=[
            DummyStrategy("first", result=None, calls=calls),
            DummyStrategy("second", result="https://example.com/fallback.jpg", calls=calls),
            DummyStrategy("third", result="https://example.com/unused.jpg", calls=calls),
        ]
    )
    extractor._client = DummyClient()

    image_url = await extractor.resolve({"link": "https://example.com/story"})

    assert image_url == "https://example.com/fallback.jpg"
    assert calls == ["first", "second"]


@pytest.mark.asyncio
async def test_resolve_handles_timeout_without_raising():
    extractor = ImageExtractor()
    extractor._client = DummyClient(exc=httpx.TimeoutException("timeout"))

    image_url = await extractor.resolve({"link": "https://example.com/story"})

    assert image_url is None


@pytest.mark.asyncio
async def test_extract_wrapper_still_accepts_plain_url():
    extractor = ImageExtractor()
    extractor._client = DummyClient(
        FakeResponse('<meta property="og:image" content="https://example.com/cover.jpg">')
    )

    image_url = await extractor.extract("https://example.com/story")

    assert image_url == "https://example.com/cover.jpg"
