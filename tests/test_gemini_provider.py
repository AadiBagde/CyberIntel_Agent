import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel, Field

from backend.core.config import Settings
from backend.services.llm.base_llm import (
    LLMProviderError,
    LLMRateLimitError,
    LLMTransientError,
    LLMValidationError,
)
from backend.services.llm.gemini_provider import GeminiProvider, pydantic_to_gemini_schema


# Test schemas for testing structured output and schema conversion
class NestedModel(BaseModel):
    name: str
    value: int


class SimpleTestModel(BaseModel):
    text_field: str = Field(description="A text field")
    number_field: float
    integer_field: int
    boolean_field: bool
    list_field: list[str]
    nested_field: NestedModel
    optional_field: str | None = None


class MockResponse:
    """Mock for httpx.Response."""

    def __init__(self, status_code: int, json_data: dict, text: str | None = None) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or json.dumps(json_data)

    def json(self) -> dict:
        return self._json_data


def test_pydantic_to_gemini_schema_conversion() -> None:
    """Test translating a Pydantic schema to Gemini format."""
    schema = SimpleTestModel.model_json_schema()
    gemini_schema = pydantic_to_gemini_schema(schema)

    # Assert basic structure
    assert gemini_schema["type"] == "OBJECT"
    assert "text_field" in gemini_schema["properties"]

    # Assert type translations
    assert gemini_schema["properties"]["text_field"]["type"] == "STRING"
    assert gemini_schema["properties"]["text_field"]["description"] == "A text field"
    assert gemini_schema["properties"]["number_field"]["type"] == "NUMBER"
    assert gemini_schema["properties"]["integer_field"]["type"] == "INTEGER"
    assert gemini_schema["properties"]["boolean_field"]["type"] == "BOOLEAN"

    # Assert list/array
    assert gemini_schema["properties"]["list_field"]["type"] == "ARRAY"
    assert gemini_schema["properties"]["list_field"]["items"]["type"] == "STRING"

    # Assert nested object reference resolution
    assert gemini_schema["properties"]["nested_field"]["type"] == "OBJECT"
    assert gemini_schema["properties"]["nested_field"]["properties"]["name"]["type"] == "STRING"
    assert gemini_schema["properties"]["nested_field"]["properties"]["value"]["type"] == "INTEGER"

    # Assert optional field (anyOf/oneOf resolution)
    assert gemini_schema["properties"]["optional_field"]["type"] == "STRING"
    assert gemini_schema["properties"]["optional_field"].get("nullable") is True


def test_gemini_provider_initialization() -> None:
    """Test provider setup and API key validation."""
    settings = Settings(GOOGLE_API_KEY="test-api-key", LLM_MODEL="gemini-1.5-flash")
    provider = GeminiProvider(settings=settings)
    assert provider.model_name == "gemini-1.5-flash"
    assert provider._api_key == "test-api-key"

    # Test key missing error
    settings_missing = Settings(GOOGLE_API_KEY=None)
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(LLMProviderError, match="Google API key is not configured"):
            GeminiProvider(settings=settings_missing)

    # Test fallback model if OpenAI model is passed
    settings_openai_model = Settings(GOOGLE_API_KEY="key", LLM_MODEL="gpt-4o-mini")
    provider_openai = GeminiProvider(settings=settings_openai_model)
    assert provider_openai.model_name == "gemini-1.5-flash"


@pytest.mark.asyncio
async def test_gemini_provider_generate_text_success() -> None:
    """Test generating unstructured text response successfully."""
    settings = Settings(GOOGLE_API_KEY="test-key", HTTP_TIMEOUT_SECONDS=10.0)
    mock_client = MagicMock(spec=httpx.AsyncClient)

    mock_resp = MockResponse(
        status_code=200,
        json_data={
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Hello, this is a response from Gemini."}]
                    },
                    "finishReason": "STOP",
                }
            ]
        },
    )
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = GeminiProvider(settings=settings, client=mock_client)
    res = await provider.generate("Say hello")

    assert res == "Hello, this is a response from Gemini."
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_provider_generate_structured_success() -> None:
    """Test generating structured response validated against a Pydantic schema."""
    settings = Settings(GOOGLE_API_KEY="test-key")
    mock_client = MagicMock(spec=httpx.AsyncClient)

    json_payload = {
        "text_field": "Hello!",
        "number_field": 12.34,
        "integer_field": 42,
        "boolean_field": True,
        "list_field": ["a", "b"],
        "nested_field": {"name": "subname", "value": 100},
        "optional_field": "present",
    }
    mock_resp = MockResponse(
        status_code=200,
        json_data={
            "candidates": [
                {
                    "content": {"parts": [{"text": json.dumps(json_payload)}]},
                    "finishReason": "STOP",
                }
            ]
        },
    )
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = GeminiProvider(settings=settings, client=mock_client)
    res = await provider.generate("Generate payload", response_schema=SimpleTestModel)

    assert isinstance(res, SimpleTestModel)
    assert res.text_field == "Hello!"
    assert res.number_field == 12.34
    assert res.integer_field == 42
    assert res.boolean_field is True
    assert res.nested_field.name == "subname"
    assert res.optional_field == "present"


@pytest.mark.asyncio
async def test_gemini_provider_rate_limit_error() -> None:
    """Test handling of HTTP 429 rate limit error."""
    settings = Settings(GOOGLE_API_KEY="test-key", HTTP_MAX_RETRIES=1)
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_resp = MockResponse(status_code=429, json_data={"error": "Rate limit exceeded"})
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = GeminiProvider(settings=settings, client=mock_client)
    with pytest.raises(LLMRateLimitError):
        await provider.generate("Fail me")


@pytest.mark.asyncio
async def test_gemini_provider_server_error() -> None:
    """Test handling of HTTP 5xx server error."""
    settings = Settings(GOOGLE_API_KEY="test-key", HTTP_MAX_RETRIES=1)
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_resp = MockResponse(status_code=503, json_data={"error": "Service unavailable"})
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = GeminiProvider(settings=settings, client=mock_client)
    with pytest.raises(LLMTransientError):
        await provider.generate("Fail me")


@pytest.mark.asyncio
async def test_gemini_provider_client_error() -> None:
    """Test handling of HTTP 400/403/etc client errors."""
    settings = Settings(GOOGLE_API_KEY="test-key", HTTP_MAX_RETRIES=1)
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_resp = MockResponse(status_code=400, json_data={"error": "Invalid argument"})
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = GeminiProvider(settings=settings, client=mock_client)
    with pytest.raises(LLMProviderError, match="Gemini client request failed"):
        await provider.generate("Fail me")


@pytest.mark.asyncio
async def test_gemini_provider_validation_failure() -> None:
    """Test handling of response validation failure against Pydantic schema."""
    settings = Settings(GOOGLE_API_KEY="test-key")
    mock_client = MagicMock(spec=httpx.AsyncClient)

    # Invalid JSON string
    mock_resp_invalid_json = MockResponse(
        status_code=200,
        json_data={
            "candidates": [
                {
                    "content": {"parts": [{"text": "{invalid json"}]},
                    "finishReason": "STOP",
                }
            ]
        },
    )
    mock_client.post = AsyncMock(return_value=mock_resp_invalid_json)

    provider = GeminiProvider(settings=settings, client=mock_client)
    with pytest.raises(LLMValidationError, match="Failed to decode Gemini response as JSON"):
        await provider.generate("Generate payload", response_schema=SimpleTestModel)

    # JSON matches but has missing fields
    mock_resp_missing_fields = MockResponse(
        status_code=200,
        json_data={
            "candidates": [
                {
                    "content": {"parts": [{"text": json.dumps({"text_field": "only this"})}]},
                    "finishReason": "STOP",
                }
            ]
        },
    )
    mock_client.post = AsyncMock(return_value=mock_resp_missing_fields)
    with pytest.raises(LLMValidationError, match="Gemini response did not match the expected schema"):
        await provider.generate("Generate payload", response_schema=SimpleTestModel)


@pytest.mark.asyncio
async def test_gemini_provider_retries_transient_failures() -> None:
    """Test that transient failures trigger retries and succeed if resolved."""
    settings = Settings(
        GOOGLE_API_KEY="test-key",
        HTTP_MAX_RETRIES=3,
        HTTP_RETRY_BACKOFF_SECONDS=0.01,  # Fast retries for testing
    )
    mock_client = MagicMock(spec=httpx.AsyncClient)

    # First attempt: 503, Second attempt: Timeout, Third attempt: 200 Success
    resp_503 = MockResponse(status_code=503, json_data={"error": "Service unavailable"})
    resp_success = MockResponse(
        status_code=200,
        json_data={
            "candidates": [
                {
                    "content": {"parts": [{"text": "Succeeded finally!"}]},
                    "finishReason": "STOP",
                }
            ]
        },
    )

    mock_client.post = AsyncMock(side_effect=[resp_503, httpx.TimeoutException("Timeout"), resp_success])

    provider = GeminiProvider(settings=settings, client=mock_client)
    res = await provider.generate("Try until success")

    assert res == "Succeeded finally!"
    assert mock_client.post.call_count == 3
