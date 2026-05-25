from abc import ABC, abstractmethod

import httpx

from backend.core.config import Settings
from backend.core.logging import get_logger
from backend.services.providers.models import ProviderResult

logger = get_logger(__name__)


class ThreatIntelProvider(ABC):
    """Contract for async threat intelligence providers."""

    name: str

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    @abstractmethod
    async def fetch(self, cve_id: str) -> ProviderResult:
        """Retrieve and normalize intelligence for a CVE."""

    def _log_latency(self, cve_id: str, elapsed_ms: float, *, success: bool) -> None:
        logger.info(
            "provider=%s cve=%s success=%s latency_ms=%.2f",
            self.name,
            cve_id,
            success,
            elapsed_ms,
        )
