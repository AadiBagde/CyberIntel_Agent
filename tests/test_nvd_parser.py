import json
from pathlib import Path

from backend.services.providers.nvd_provider import parse_nvd_response

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_nvd_response_extracts_fields() -> None:
    payload = json.loads((FIXTURES / "nvd_cve_2024_3094.json").read_text(encoding="utf-8"))
    result = parse_nvd_response("CVE-2024-3094", payload)

    assert result.success is True
    assert result.cve_id == "CVE-2024-3094"
    assert result.cvss_score == 10.0
    assert result.severity == "CRITICAL"
    assert "CWE-506" in result.cwe
    assert result.affected_products
    assert "https://example.com/advisory" in result.references
    assert result.summary is not None and "xz" in result.summary.lower()


def test_parse_nvd_response_not_found() -> None:
    result = parse_nvd_response("CVE-2024-9999", {"vulnerabilities": []})
    assert result.success is False
    assert result.error is not None
