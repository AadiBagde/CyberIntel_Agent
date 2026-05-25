from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from backend.core.config import Settings, get_settings
from backend.core.exceptions import ExternalServiceError
from backend.core.logging import get_logger

logger = get_logger(__name__)


class VectorMemoryStore(ABC):
    """Abstraction for semantic investigation memory (Phase 5+)."""

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    @abstractmethod
    async def ensure_collection(self) -> None:
        pass

    @abstractmethod
    async def upsert_investigation(
        self,
        investigation_id: UUID,
        *,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        pass

    @abstractmethod
    async def search_similar(
        self,
        vector: list[float],
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        pass


class QdrantVectorStore(VectorMemoryStore):
    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        self._collection = cfg.qdrant_collection
        self._client = AsyncQdrantClient(url=cfg.qdrant_url)

    async def health_check(self) -> bool:
        try:
            await self._client.get_collections()
            return True
        except UnexpectedResponse as exc:
            logger.error("Qdrant health check failed: %s", exc)
            return False

    async def ensure_collection(self) -> None:
        raise NotImplementedError("Vector collection setup is implemented in Phase 5")

    async def upsert_investigation(
        self,
        investigation_id: UUID,
        *,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        raise NotImplementedError("Vector upsert is implemented in Phase 5")

    async def search_similar(
        self,
        vector: list[float],
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("Vector search is implemented in Phase 5")

    async def close(self) -> None:
        await self._client.close()
