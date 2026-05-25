import time
from typing import ClassVar

from backend.core.logging import get_logger
from backend.services.http_client import ResilientHttpClient
from backend.services.providers.base_provider import ThreatIntelProvider
from backend.services.providers.models import ProviderResult

logger = get_logger(__name__)

KEV_CACHE_TTL_SECONDS = 3600


def parse_kev_catalog(payload: dict) -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    for entry in payload.get("vulnerabilities") or []:
        cve_id = (entry.get("cveID") or "").strip().upper()
        if cve_id:
            catalog[cve_id] = entry
    return catalog


class CisaKevProvider(ThreatIntelProvider):
    name = "cisa_kev"

    _catalog: ClassVar[dict[str, dict] | None] = None
    _catalog_loaded_at: ClassVar[float | None] = None

    def __init__(self, http: ResilientHttpClient, settings) -> None:
        super().__init__(http.client, settings)
        self._http = http
        self._settings = settings

    async def _load_catalog(self) -> dict[str, dict]:
        now = time.time()
        if (
            CisaKevProvider._catalog is not None
            and CisaKevProvider._catalog_loaded_at is not None
            and (now - CisaKevProvider._catalog_loaded_at) < KEV_CACHE_TTL_SECONDS
        ):
            return CisaKevProvider._catalog

        payload = await self._http.get_json(
            self._settings.cisa_kev_url,
            provider=self.name,
        )
        CisaKevProvider._catalog = parse_kev_catalog(payload)
        CisaKevProvider._catalog_loaded_at = now
        logger.info("provider=cisa_kev catalog_loaded entries=%s", len(CisaKevProvider._catalog))
        return CisaKevProvider._catalog

    async def fetch(self, cve_id: str) -> ProviderResult:
        start = time.perf_counter()
        try:
            catalog = await self._load_catalog()
            entry = catalog.get(cve_id)
            known_exploited = entry is not None
            summary = None
            if entry:
                summary = entry.get("vulnerabilityName") or entry.get("shortDescription")

            result = ProviderResult(
                source="cisa_kev",
                success=True,
                cve_id=cve_id,
                known_exploited=known_exploited,
                exploit_available=known_exploited,
                summary=summary,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._log_latency(cve_id, elapsed_ms, success=False)
            logger.warning("provider=cisa_kev cve=%s degraded error=%s", cve_id, exc)
            return ProviderResult(
                source="cisa_kev",
                success=False,
                cve_id=cve_id,
                error=str(exc),
                known_exploited=False,
                exploit_available=False,
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        self._log_latency(cve_id, elapsed_ms, success=result.success)
        return result
