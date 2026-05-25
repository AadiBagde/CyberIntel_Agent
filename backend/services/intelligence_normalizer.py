from backend.schemas.research import ThreatResearch
from backend.services.providers.models import ProviderResult


def merge_provider_results(
    *,
    cve_id: str,
    query: str,
    results: list[ProviderResult],
) -> ThreatResearch:
    """Merge normalized provider fragments into a single ThreatResearch artifact."""
    summary = ""
    cvss_score: float | None = None
    severity: str | None = None
    exploit_available = False
    known_exploited = False
    affected_products: list[str] = []
    references: list[str] = []
    cwe: list[str] = []
    published_date = None
    last_modified_date = None
    data_sources: list[str] = []

    nvd = next((r for r in results if r.source == "nvd" and r.success), None)
    cisa = next((r for r in results if r.source == "cisa_kev" and r.success), None)

    if nvd:
        data_sources.append("nvd")
        summary = nvd.summary or summary
        cvss_score = nvd.cvss_score
        severity = nvd.severity
        affected_products = list(nvd.affected_products)
        references = list(nvd.references)
        cwe = list(nvd.cwe)
        published_date = nvd.published_date
        last_modified_date = nvd.last_modified_date

    if cisa:
        data_sources.append("cisa_kev")
        known_exploited = bool(cisa.known_exploited)
        if cisa.exploit_available is not None:
            exploit_available = bool(cisa.exploit_available)
        if not summary and cisa.summary:
            summary = cisa.summary

    if nvd and not exploit_available:
        exploit_available = known_exploited

    if not summary:
        summary = f"No detailed summary available for {cve_id}."

    return ThreatResearch(
        cve_id=cve_id,
        query=query,
        summary=summary,
        cvss_score=cvss_score,
        severity=severity,
        exploit_available=exploit_available,
        known_exploited=known_exploited,
        affected_products=affected_products,
        references=references,
        cwe=cwe,
        published_date=published_date,
        last_modified_date=last_modified_date,
        data_sources=data_sources,
    )
