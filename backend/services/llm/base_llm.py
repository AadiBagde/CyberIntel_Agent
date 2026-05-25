from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from backend.core.config import Settings
from backend.core.exceptions import CyberIntelError

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(CyberIntelError):
    """Base error for LLM providers."""

    pass


class LLMRateLimitError(LLMProviderError):
    """Rate limit exceeded (HTTP 429) for LLM provider."""

    pass


class LLMTransientError(LLMProviderError):
    """Transient failures (HTTP 5xx, timeouts, network issues)."""

    pass


class LLMValidationError(LLMProviderError):
    """Response validation failed against the requested schema."""

    pass


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the LLM provider with application settings.

        Args:
            settings: The application settings module.
        """
        self._settings = settings

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        response_schema: Type[T] | None = None,
        timeout: float | None = None,
    ) -> str | T:
        """
        Generate content using the LLM.

        Args:
            prompt: The main user prompt.
            system_instruction: Optional system instruction/context.
            temperature: Sampling temperature (0.0 to 1.0).
            response_schema: Optional Pydantic model for structured JSON output.
            timeout: Optional custom timeout in seconds (falls back to default settings).

        Returns:
            The raw text response from the LLM, or a validated instance of the response_schema.

        Raises:
            LLMProviderError: If the request fails, times out, is rate limited,
                             or fails response schema validation.
        """
        pass
