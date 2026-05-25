from backend.services.intelligence_normalizer import merge_provider_results
from backend.services.providers.models import ProviderResult


def test_merge_provider_results_combines_nvd_and_cisa() -> None:
    results = [
        ProviderResult(
            source="nvd",
            success=True,
            cve_id="CVE-2024-3094",
            summary="NVD summary",
            cvss_score=10.0,
            severity="CRITICAL",
            references=["https://nvd.example"],
            cwe=["CWE-506"],
            affected_products=["cpe:2.3:a:tukaani:xz:*:*:*:*:*:*:*"],
        ),
        ProviderResult(
            source="cisa_kev",
            success=True,
            cve_id="CVE-2024-3094",
            known_exploited=True,
            exploit_available=True,
            summary="KEV entry",
        ),
    ]

    research = merge_provider_results(
        cve_id="CVE-2024-3094",
        query="CVE-2024-3094",
        results=results,
    )

    assert research.cve_id == "CVE-2024-3094"
    assert research.known_exploited is True
    assert research.exploit_available is True
    assert research.cvss_score == 10.0
    assert "nvd" in research.data_sources
    assert "cisa_kev" in research.data_sources


def test_merge_without_cisa_still_produces_research() -> None:
    results = [
        ProviderResult(
            source="nvd",
            success=True,
            cve_id="CVE-2023-4863",
            summary="Heap buffer overflow",
            cvss_score=8.8,
            severity="HIGH",
        ),
        ProviderResult(
            source="cisa_kev",
            success=False,
            cve_id="CVE-2023-4863",
            error="timeout",
        ),
    ]

    research = merge_provider_results(
        cve_id="CVE-2023-4863",
        query="CVE-2023-4863",
        results=results,
    )

    assert research.known_exploited is False
    assert research.data_sources == ["nvd"]
