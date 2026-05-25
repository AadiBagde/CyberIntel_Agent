from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.agents.analysis_agent import ThreatAnalysisAgent
from backend.schemas.enums import SeverityLevel
from backend.schemas.research import ThreatResearch, ThreatAssessment
from backend.services.llm.base_llm import BaseLLMProvider, LLMValidationError


@pytest.fixture
def mock_research() -> ThreatResearch:
    return ThreatResearch(
        cve_id="CVE-2024-3094",
        query="CVE-2024-3094",
        summary="Malicious backdoor in XZ Utils.",
        cvss_score=10.0,
        severity="critical",
        exploit_available=True,
        known_exploited=True,
        affected_products=["XZ Utils 5.6.0", "XZ Utils 5.6.1"],
        references=["https://nvd.nist.gov/vuln/detail/CVE-2024-3094"],
        cwe=["CWE-506"],
        data_sources=["nvd", "cisa_kev"],
    )


@pytest.fixture
def mock_assessment() -> ThreatAssessment:
    return ThreatAssessment(
        severity=SeverityLevel.CRITICAL,
        confidence=95,
        reasoning="Backdoor allows remote code execution in critical systems. Exploit public and active.",
        remediation=["Downgrade XZ Utils to 5.4", "Check system logs for unusual SSH activity"],
        uncertainty_notes=["Check exact downstream distributions affected."],
        attack_path=["SSH authentication bypass via modified liblzma code."],
    )


@pytest.mark.asyncio
async def test_threat_analysis_agent_success(
    mock_research: ThreatResearch,
    mock_assessment: ThreatAssessment,
) -> None:
    """Test successful threat assessment generation."""
    mock_llm = MagicMock(spec=BaseLLMProvider)
    mock_llm.generate = AsyncMock(return_value=mock_assessment)

    agent = ThreatAnalysisAgent(llm_provider=mock_llm)
    result = await agent.analyze(mock_research)

    assert isinstance(result, ThreatAssessment)
    assert result.severity == SeverityLevel.CRITICAL
    assert result.confidence == 95
    assert "Backdoor allows remote code execution" in result.reasoning
    assert len(result.remediation) == 2

    # Verify LLM provider was called with correct parameters
    mock_llm.generate.assert_called_once()
    kwargs = mock_llm.generate.call_args[1]
    assert kwargs["response_schema"] == ThreatAssessment
    assert kwargs["temperature"] == 0.0
    assert "CVE-2024-3094" in kwargs["prompt"]


@pytest.mark.asyncio
async def test_threat_analysis_agent_retry_on_validation_failure(
    mock_research: ThreatResearch,
    mock_assessment: ThreatAssessment,
) -> None:
    """Test that the agent retries when LLMValidationError occurs and succeeds on retry."""
    mock_llm = MagicMock(spec=BaseLLMProvider)
    
    # First call raises validation error (e.g. malformed JSON), second call succeeds
    mock_llm.generate = AsyncMock(
        side_effect=[
            LLMValidationError("Malformed JSON response from model"),
            mock_assessment,
        ]
    )

    agent = ThreatAnalysisAgent(llm_provider=mock_llm, max_retries=3)
    result = await agent.analyze(mock_research)

    assert isinstance(result, ThreatAssessment)
    assert result.confidence == 95
    assert mock_llm.generate.call_count == 2


@pytest.mark.asyncio
async def test_threat_analysis_agent_max_retries_exhausted(
    mock_research: ThreatResearch,
) -> None:
    """Test that agent escalates error when max retries for validation fail."""
    mock_llm = MagicMock(spec=BaseLLMProvider)
    mock_llm.generate = AsyncMock(
        side_effect=LLMValidationError("Invalid schema match")
    )

    agent = ThreatAnalysisAgent(llm_provider=mock_llm, max_retries=3)
    
    with pytest.raises(LLMValidationError, match="Invalid schema match"):
        await agent.analyze(mock_research)

    assert mock_llm.generate.call_count == 3
