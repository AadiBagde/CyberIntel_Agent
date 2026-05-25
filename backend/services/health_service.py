from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import Settings
from backend.memory.vector_store import QdrantVectorStore


@dataclass(frozen=True)
class HealthStatus:
    status: str
    app: str
    environment: str
    postgres: str
    qdrant: str
    version: str


class HealthService:
    def __init__(
        self,
        settings: Settings,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._settings = settings
        self._vector_store = vector_store

    async def check(self, session: AsyncSession) -> HealthStatus:
        postgres_status = "ok"
        try:
            await session.execute(text("SELECT 1"))
        except Exception:
            postgres_status = "unavailable"

        qdrant_status = "ok" if await self._vector_store.health_check() else "unavailable"
        overall = "ok" if postgres_status == "ok" and qdrant_status == "ok" else "degraded"

        return HealthStatus(
            status=overall,
            app=self._settings.app_name,
            environment=self._settings.app_env.value,
            postgres=postgres_status,
            qdrant=qdrant_status,
            version="0.1.0",
        )
