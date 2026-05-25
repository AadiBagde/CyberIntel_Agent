import pytest
from pydantic import ValidationError

from backend.schemas.enums import InvestigationStatus, SeverityLevel
from backend.schemas.investigation import InvestigationRequest
from backend.schemas.research import ThreatAssessment, ThreatResearch, ValidationResult


def test_investigation_request_strips_query() -> None:
    req = InvestigationRequest(query="  CVE-2024-3094  ")
    assert req.query == "CVE-2024-3094"


def test_investigation_request_rejects_empty_query() -> None:
    with pytest.raises(ValidationError):
        InvestigationRequest(query="   ")


def test_threat_research_cvss_bounds() -> None:
    with pytest.raises(ValidationError):
        ThreatResearch(cve_id="CVE-2024-3094", query="CVE-2024-3094", cvss_score=11.0)


def test_threat_assessment_confidence_bounds() -> None:
    assessment = ThreatAssessment(
        severity=SeverityLevel.HIGH,
        confidence=85,
        reasoning="KEV listed; critical supply chain risk.",
    )
    assert assessment.confidence == 85

    # Out of bounds confidence (low)
    with pytest.raises(ValidationError):
        ThreatAssessment(
            severity=SeverityLevel.HIGH,
            confidence=-1,
            reasoning="Reason",
        )

    # Out of bounds confidence (high)
    with pytest.raises(ValidationError):
        ThreatAssessment(
            severity=SeverityLevel.HIGH,
            confidence=101,
            reasoning="Reason",
        )


def test_threat_assessment_strict_types() -> None:
    # Under strict typing, confidence must be an integer, not a string
    with pytest.raises(ValidationError):
        ThreatAssessment(
            severity=SeverityLevel.HIGH,
            confidence="85",  # String instead of int
            reasoning="Reason",
        )

    # Reasoning must be a string, not an integer
    with pytest.raises(ValidationError):
        ThreatAssessment(
            severity=SeverityLevel.HIGH,
            confidence=85,
            reasoning=123,  # Int instead of string
        )


def test_threat_assessment_extra_fields() -> None:
    # extra="forbid" raises ValidationError when unrecognized fields are provided
    with pytest.raises(ValidationError):
        ThreatAssessment(
            severity=SeverityLevel.HIGH,
            confidence=85,
            reasoning="Reason",
            unknown_field="not allowed",
        )


def test_validation_result_model() -> None:
    result = ValidationResult(valid=False, confidence_adjustment=-15)
    assert result.valid is False
    assert result.confidence_adjustment == -15


def test_investigation_status_enum() -> None:
    assert InvestigationStatus.QUEUED.value == "queued"
