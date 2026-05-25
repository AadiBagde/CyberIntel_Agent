from enum import Enum


class QueryType(str, Enum):
    CVE = "cve"
    MALWARE = "malware"
    THREAT_ACTOR = "threat_actor"
    UNKNOWN = "unknown"


class InvestigationStatus(str, Enum):
    QUEUED = "queued"
    RESEARCHING = "researching"
    DEDUPLICATING = "deduplicating"
    ANALYZING = "analyzing"
    VALIDATING = "validating"
    PERSISTING = "persisting"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
