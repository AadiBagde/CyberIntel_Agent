from unittest.mock import AsyncMock

import pytest

from backend.agents.research_agent import ResearchAgent
from backend.core.exceptions import ExternalServiceError
from backend.services.providers.models import ProviderResult


class _StubProvider:
    def __init__(self, name: str, result: ProviderResult) -> None:
        self.name = name
        self._result = result

    async def fetch(self, cve_id: str) -> ProviderResult:
        return self._result.model_copy(update={"cve_id": cve_id})


@pytest.mark.asyncio
async def test_research_agent_merges_providers() -> None:
    nvd = _StubProvider(
        "nvd",
        ProviderResult(
            source="nvd",
            success=True,
            cve_id="CVE-2024-3094",
            summary="Test summary",
            cvss_score=9.8,
            severity="CRITICAL",
        ),
    )
    cisa = _StubProvider(
        "cisa_kev",
        ProviderResult(
            source="cisa_kev",
            success=True,
            cve_id="CVE-2024-3094",
            known_exploited=True,
            exploit_available=True,
        ),
    )
    agent = ResearchAgent([nvd, cisa])
    research = await agent.research("CVE-2024-3094")

    assert research.cve_id == "CVE-2024-3094"
    assert research.known_exploited is True
    assert "nvd" in research.data_sources


@pytest.mark.asyncio
async def test_research_agent_fails_when_nvd_unavailable() -> None:
    nvd = _StubProvider(
        "nvd",
        ProviderResult(
            source="nvd",
            success=False,
            cve_id="CVE-2024-3094",
            error="upstream error",
        ),
    )
    agent = ResearchAgent([nvd])
    with pytest.raises(ExternalServiceError):
        await agent.research("CVE-2024-3094")
