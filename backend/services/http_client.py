import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.config import Settings
from backend.core.exceptions import ExternalServiceError
from backend.core.logging import get_logger

logger = get_logger(__name__)


class ResilientHttpClient:
    """Shared async HTTP client with retries for threat intel providers."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.http_timeout_seconds),
            follow_redirects=True,
        )

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client

    async def close(self) -> None:
        await self._client.aclose()

    async def get_json(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        provider: str,
    ) -> dict:
        attempt_settings = self._settings

        @retry(
            reraise=True,
            stop=stop_after_attempt(attempt_settings.http_max_retries),
            wait=wait_exponential(
                multiplier=attempt_settings.http_retry_backoff_seconds,
                min=attempt_settings.http_retry_backoff_seconds,
                max=30,
            ),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        )
        async def _request() -> dict:
            response = await self._client.get(url, params=params, headers=headers)
            if response.status_code == 429:
                logger.warning("provider=%s rate_limited url=%s", provider, url)
                raise ExternalServiceError(
                    f"{provider} rate limit exceeded",
                    details={"status_code": 429, "url": url},
                )
            if response.status_code >= 500:
                raise ExternalServiceError(
                    f"{provider} upstream error",
                    details={"status_code": response.status_code, "url": url},
                )
            if response.status_code >= 400:
                raise ExternalServiceError(
                    f"{provider} request failed",
                    details={
                        "status_code": response.status_code,
                        "url": url,
                        "body": response.text[:500],
                    },
                )
            data = response.json()
            if not isinstance(data, dict):
                raise ExternalServiceError(
                    f"{provider} returned non-object JSON",
                    details={"url": url},
                )
            return data

        try:
            return await _request()
        except httpx.TimeoutException as exc:
            logger.error("provider=%s timeout url=%s", provider, url)
            raise ExternalServiceError(
                f"{provider} request timed out",
                details={"url": url},
            ) from exc
        except httpx.NetworkError as exc:
            logger.error("provider=%s network_error url=%s", provider, url)
            raise ExternalServiceError(
                f"{provider} network error",
                details={"url": url},
            ) from exc
