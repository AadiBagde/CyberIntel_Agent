from typing import Any, TypedDict

from backend.schemas.enums import InvestigationStatus, QueryType
from backend.schemas.research import ThreatAssessment, ThreatResearch, ValidationResult


class InvestigationGraphState(TypedDict, total=False):
    """
    LangGraph state for the investigation pipeline.

    Extended in later phases as nodes populate structured outputs.
    """

    investigation_id: str
    trace_id: str
    query: str
    query_type: QueryType
    status: InvestigationStatus
    research: ThreatResearch
    assessment: ThreatAssessment
    validation: ValidationResult
    memory_context: list[str]
    errors: list[str]
    metadata: dict[str, Any]
