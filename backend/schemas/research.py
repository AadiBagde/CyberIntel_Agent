from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.enums import SeverityLevel, ValidationSeverity


class ThreatResearch(BaseModel):
    """Structured output from the research stage."""

    model_config = ConfigDict(extra="forbid")

    cve_id: str
    query: str
    summary: str = ""
    cvss_score: float | None = Field(default=None, ge=0.0, le=10.0)
    severity: str | None = None
    exploit_available: bool = False
    known_exploited: bool = False
    affected_products: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    cwe: list[str] = Field(default_factory=list)
    published_date: datetime | None = None
    last_modified_date: datetime | None = None
    data_sources: list[str] = Field(default_factory=list)


class ThreatAssessment(BaseModel):
    """Structured output from threat analysis (Phase 2+)."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    severity: SeverityLevel = SeverityLevel.UNKNOWN
    confidence: int = Field(default=0, ge=0, le=100)
    reasoning: str = ""
    remediation: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    attack_path: list[str] = Field(default_factory=list)


def parse_threat_assessment(data: object) -> ThreatAssessment:
    """Parse assessment from JSONB/dict with enum coercion for database round-trips."""
    return ThreatAssessment.model_validate(data, strict=False)


class ValidationIssue(BaseModel):
    field: str | None = None
    issue: str
    severity: ValidationSeverity = ValidationSeverity.ERROR


class ValidationResult(BaseModel):
    """Structured output from validation (Phase 4+)."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    confidence_adjustment: int = Field(default=0, ge=-100, le=100)
    corrected_fields: dict[str, str] = Field(default_factory=dict)
