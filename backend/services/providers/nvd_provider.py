import time
from datetime import datetime

from backend.core.logging import get_logger
from backend.services.http_client import ResilientHttpClient
from backend.services.providers.base_provider import ThreatIntelProvider
from backend.services.providers.models import ProviderResult

logger = get_logger(__name__)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _extract_cvss(metrics: dict) -> tuple[float | None, str | None]:
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key) or []
        if not entries:
            continue
        cvss_data = entries[0].get("cvssData") or {}
        score = cvss_data.get("baseScore")
        severity = cvss_data.get("baseSeverity")
        if score is not None:
            return float(score), str(severity) if severity else None
    return None, None


def _extract_cwes(weaknesses: list) -> list[str]:
    cwes: list[str] = []
    for weakness in weaknesses or []:
        for desc in weakness.get("description") or []:
            value = desc.get("value")
            if value and value.startswith("CWE-"):
                cwes.append(value)
    return sorted(set(cwes))


def _extract_products(configurations: list) -> list[str]:
    products: list[str] = []
    for config in configurations or []:
        for node in config.get("nodes") or []:
            for match in node.get("cpeMatch") or []:
                criteria = match.get("criteria") or match.get("cpe23Uri")
                if criteria:
                    products.append(criteria)
    return sorted(set(products))[:50]


def _extract_references(refs: list) -> list[str]:
    urls: list[str] = []
    for ref in refs or []:
        url = ref.get("url")
        if url:
            urls.append(url)
    return sorted(set(urls))


def parse_nvd_response(cve_id: str, payload: dict) -> ProviderResult:
    vulnerabilities = payload.get("vulnerabilities") or []
    if not vulnerabilities:
        return ProviderResult(
            source="nvd",
            success=False,
            cve_id=cve_id,
            error="CVE not found in NVD",
        )

    cve_block = vulnerabilities[0].get("cve") or {}
    descriptions = cve_block.get("descriptions") or []
    summary = next(
        (d.get("value", "") for d in descriptions if d.get("lang") == "en"),
        descriptions[0].get("value", "") if descriptions else "",
    )

    metrics = cve_block.get("metrics") or {}
    cvss_score, severity = _extract_cvss(metrics)

    return ProviderResult(
        source="nvd",
        success=True,
        cve_id=cve_id,
        summary=summary or None,
        cvss_score=cvss_score,
        severity=severity,
        affected_products=_extract_products(vulnerabilities[0].get("configurations") or []),
        references=_extract_references(cve_block.get("references") or []),
        cwe=_extract_cwes(cve_block.get("weaknesses") or []),
        published_date=_parse_iso_datetime(cve_block.get("published")),
        last_modified_date=_parse_iso_datetime(cve_block.get("lastModified")),
    )


class NvdProvider(ThreatIntelProvider):
    name = "nvd"

    def __init__(self, http: ResilientHttpClient, settings) -> None:
        super().__init__(http.client, settings)
        self._http = http
        self._settings = settings

    async def fetch(self, cve_id: str) -> ProviderResult:
        start = time.perf_counter()
        headers: dict[str, str] = {}
        if self._settings.nvd_api_key:
            headers["apiKey"] = self._settings.nvd_api_key

        try:
            payload = await self._http.get_json(
                self._settings.nvd_api_base_url,
                params={"cveId": cve_id},
                headers=headers,
                provider=self.name,
            )
            result = parse_nvd_response(cve_id, payload)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._log_latency(cve_id, elapsed_ms, success=False)
            logger.error("provider=nvd cve=%s error=%s", cve_id, exc)
            return ProviderResult(
                source="nvd",
                success=False,
                cve_id=cve_id,
                error=str(exc),
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        self._log_latency(cve_id, elapsed_ms, success=result.success)
        return result
