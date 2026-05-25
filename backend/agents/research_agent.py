from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING

from backend.core.exceptions import ExternalServiceError
from backend.core.logging import get_logger
from backend.schemas.research import ThreatResearch
from backend.utils.cve import extract_cve_id

if TYPE_CHECKING:
    from backend.services.providers.base_provider import ThreatIntelProvider
    from backend.services.providers.models import ProviderResult

logger = get_logger(__name__)


class ResearchAgent:
    """
    Autonomous CVE intelligence retrieval agent.

    Orchestrates provider calls, normalizes responses, and returns ThreatResearch.
    """

    def __init__(self, providers: list[ThreatIntelProvider]) -> None:
        self._providers = providers

    async def research(self, query: str) -> ThreatResearch:
        from backend.services.intelligence_normalizer import merge_provider_results

        cve_id = extract_cve_id(query)
        logger.info("research_agent_start cve=%s", cve_id)

        results = await self._fetch_all(cve_id)
        nvd_result = next((r for r in results if r.source == "nvd"), None)

        if nvd_result is None or not nvd_result.success:
            error = nvd_result.error if nvd_result else "NVD provider not configured"
            logger.error("research_agent_failed cve=%s error=%s", cve_id, error)
            raise ExternalServiceError(
                "Failed to retrieve required NVD intelligence",
                details={"cve_id": cve_id, "error": error},
            )

        research = merge_provider_results(cve_id=cve_id, query=query, results=results)
        logger.info(
            "research_agent_complete cve=%s sources=%s kev=%s",
            cve_id,
            research.data_sources,
            research.known_exploited,
        )
        return research

    async def _fetch_all(self, cve_id: str) -> list["ProviderResult"]:
        from backend.services.providers.models import ProviderResult

        tasks = [provider.fetch(cve_id) for provider in self._providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        normalized: list[ProviderResult] = []
        for provider, result in zip(self._providers, results, strict=True):
            if isinstance(result, Exception):
                logger.warning(
                    "provider=%s cve=%s exception=%s",
                    provider.name,
                    cve_id,
                    result,
                )
                normalized.append(
                    ProviderResult(
                        source=provider.name,
                        success=False,
                        cve_id=cve_id,
                        error=str(result),
                    )
                )
            else:
                normalized.append(result)
        return normalized
