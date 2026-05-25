import re

from backend.schemas.enums import QueryType

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)


def classify_query(query: str) -> QueryType:
    normalized = query.strip()
    if CVE_PATTERN.match(normalized):
        return QueryType.CVE
    lowered = normalized.lower()
    if "apt" in lowered or "group" in lowered or "actor" in lowered:
        return QueryType.THREAT_ACTOR
    if any(token in lowered for token in ("ransomware", "trojan", "backdoor", "malware", "worm")):
        return QueryType.MALWARE
    return QueryType.UNKNOWN
