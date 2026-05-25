from backend.services.providers.cisa_provider import parse_kev_catalog


def test_parse_kev_catalog_indexes_by_cve() -> None:
    payload = {
        "vulnerabilities": [
            {
                "cveID": "CVE-2024-3094",
                "vulnerabilityName": "XZ Utils Backdoor",
            }
        ]
    }
    catalog = parse_kev_catalog(payload)
    assert "CVE-2024-3094" in catalog
    assert catalog["CVE-2024-3094"]["vulnerabilityName"] == "XZ Utils Backdoor"
