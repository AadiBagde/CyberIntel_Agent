from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.enums import InvestigationStatus, QueryType, SeverityLevel
from backend.schemas.deduplication import DeduplicationResult
from backend.schemas.research import ThreatAssessment, ThreatResearch, ValidationResult


class InvestigationRequest(BaseModel):
    """API input for starting an investigation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(..., min_length=1, max_length=512)
    query_type: QueryType | None = Field(
        default=None,
        description="Optional hint; auto-detected when omitted",
    )
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        return value.strip()


class InvestigationRecord(BaseModel):
    """Canonical investigation aggregate returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trace_id: str
    query: str
    query_type: QueryType
    status: InvestigationStatus
    created_at: datetime
    updated_at: datetime
    research: ThreatResearch | None = None
    assessment: ThreatAssessment | None = None
    validation: ValidationResult | None = None
    deduplication: DeduplicationResult | None = None
    fingerprint: str | None = None
    normalized_query: str | None = None
    memory_context: list[str] = Field(default_factory=list)
    report_path: str | None = None
    error_message: str | None = None


class InvestigationCreatedResponse(BaseModel):
    id: UUID
    trace_id: str
    status: InvestigationStatus
    message: str


class InvestigationResponse(BaseModel):
    investigation: InvestigationRecord
