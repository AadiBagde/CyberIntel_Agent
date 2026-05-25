import pytest

from backend.core.exceptions import ValidationError
from backend.utils.cve import extract_cve_id, is_valid_cve_format, normalize_cve_id


def test_normalize_cve_id() -> None:
    assert normalize_cve_id("cve-2024-3094") == "CVE-2024-3094"


def test_is_valid_cve_format() -> None:
    assert is_valid_cve_format("CVE-2024-3094")
    assert not is_valid_cve_format("CVE-24-3094")


def test_extract_cve_from_query() -> None:
    assert extract_cve_id("xz backdoor CVE-2024-3094") == "CVE-2024-3094"


def test_extract_cve_rejects_missing() -> None:
    with pytest.raises(ValidationError):
        extract_cve_id("apt28 campaign")


def test_extract_cve_rejects_malformed() -> None:
    with pytest.raises(ValidationError):
        extract_cve_id("CVE-2024-")
