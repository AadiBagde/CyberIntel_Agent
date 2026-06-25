import re

from backend.core.exceptions import ValidationError

CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
LOOSE_CVE_PATTERN = re.compile(r"CVE[-\s]*(\d{4})[-\s]*(\d{4,7})", re.IGNORECASE)
STRICT_CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)


class InvalidCVEError(ValidationError):
    """Raised when a CVE identifier is missing or malformed."""


def normalize_cve_id(value: str) -> str:
    """Normalize to uppercase CVE-YYYY-NNNN form."""
    return value.strip().upper()


def is_valid_cve_format(cve_id: str) -> bool:
    return bool(STRICT_CVE_PATTERN.match(normalize_cve_id(cve_id)))


def extract_cve_id(query: str) -> str:
    """
    Extract the first CVE identifier from a query string.

    Accepts hyphenated and space-separated forms, e.g.:
    CVE-2024-3094, cve-2024-3094, CVE 2024 3094

    Raises InvalidCVEError when no valid CVE is present.
    """
    stripped = query.strip()
    match = CVE_PATTERN.search(stripped)
    if match:
        cve_id = normalize_cve_id(match.group(0))
    else:
        loose = LOOSE_CVE_PATTERN.search(stripped)
        if not loose:
            raise InvalidCVEError(
                "Query must contain a valid CVE identifier (CVE-YYYY-NNNN)",
                details={"query": query},
            )
        cve_id = normalize_cve_id(f"CVE-{loose.group(1)}-{loose.group(2)}")

    if not is_valid_cve_format(cve_id):
        raise InvalidCVEError(
            "CVE identifier format is invalid",
            details={"cve_id": cve_id},
        )
    return cve_id
