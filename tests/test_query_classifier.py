from backend.schemas.enums import QueryType
from backend.utils.query_classifier import classify_query


def test_classify_cve() -> None:
    assert classify_query("CVE-2024-3094") == QueryType.CVE


def test_classify_malware_hint() -> None:
    assert classify_query("xz backdoor malware") == QueryType.MALWARE


def test_classify_unknown() -> None:
    assert classify_query("suspicious activity on edge devices") == QueryType.UNKNOWN
