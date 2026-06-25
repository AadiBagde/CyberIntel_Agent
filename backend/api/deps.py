from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.research_agent import ResearchAgent
from backend.core.config import Settings, get_settings
from backend.db.session import get_db_session
from backend.memory.vector_store import QdrantVectorStore
from backend.services.health_service import HealthService
from backend.services.http_client import ResilientHttpClient
from backend.services.investigation_service import InvestigationService
from backend.services.providers.factory import build_research_agent


async def get_settings_dep() -> Settings:
    return get_settings()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_http_client(request: Request) -> ResilientHttpClient:
    client: ResilientHttpClient = request.app.state.http_client
    return client


def get_research_agent(
    http: ResilientHttpClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings_dep),
) -> ResearchAgent:
    return build_research_agent(http, settings)


from backend.services.llm.gemini_provider import GeminiProvider
from backend.agents.analysis_agent import ThreatAnalysisAgent
from backend.agents.deduplication_agent import DeduplicationAgent
from backend.services.deduplication_service import DeduplicationService


def get_analysis_agent(
    settings: Settings = Depends(get_settings_dep),
    request: Request = Request,
) -> ThreatAnalysisAgent:
    client = request.app.state.http_client.client
    llm = GeminiProvider(settings=settings, client=client)
    return ThreatAnalysisAgent(llm_provider=llm)


def get_deduplication_agent(
    session: AsyncSession = Depends(get_db),
) -> DeduplicationAgent:
    service = DeduplicationService(session)
    return DeduplicationAgent(service)


def get_investigation_service(
    session: AsyncSession = Depends(get_db),
    research_agent: ResearchAgent = Depends(get_research_agent),
    deduplication_agent: DeduplicationAgent = Depends(get_deduplication_agent),
    analysis_agent: ThreatAnalysisAgent = Depends(get_analysis_agent),
) -> InvestigationService:
    return InvestigationService(
        session=session,
        research_agent=research_agent,
        deduplication_agent=deduplication_agent,
        analysis_agent=analysis_agent,
    )


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    return QdrantVectorStore()


def get_trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", "")


def get_health_service(
    settings: Settings = Depends(get_settings_dep),
    vector_store: QdrantVectorStore = Depends(get_vector_store),
) -> HealthService:
    return HealthService(settings=settings, vector_store=vector_store)
