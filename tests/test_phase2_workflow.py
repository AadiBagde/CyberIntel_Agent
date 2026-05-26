import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest

from sqlalchemy.ext.asyncio import AsyncSession
from backend.agents.analysis_agent import ThreatAnalysisAgent
from backend.agents.research_agent import ResearchAgent
from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.enums import InvestigationStatus, QueryType, SeverityLevel
from backend.schemas.research import ThreatAssessment, ThreatResearch
from backend.services.llm.base_llm import LLMProviderError
from backend.workflows.phase2 import compile_phase2_graph
from backend.workflows.state import InvestigationGraphState


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
    )


@pytest.fixture
def mock_assessment() -> ThreatAssessment:
    return ThreatAssessment(
        severity=SeverityLevel.CRITICAL,
        confidence=95,
        reasoning="Backdoor allows remote code execution in critical systems.",
        remediation=["Downgrade XZ Utils to 5.4"],
    )


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    return session


@pytest.mark.asyncio
async def test_phase2_workflow_success(
    mock_session: AsyncSession,
    mock_research: ThreatResearch,
    mock_assessment: ThreatAssessment,
) -> None:
    # Setup mocks
    mock_research_agent = MagicMock(spec=ResearchAgent)
    mock_research_agent.research = AsyncMock(return_value=mock_research)

    mock_analysis_agent = MagicMock(spec=ThreatAnalysisAgent)
    mock_analysis_agent.analyze = AsyncMock(return_value=mock_assessment)

    # Use a dummy repo injected via patch or we can let compile_phase2_graph use the mocked session.
    # We will mock the repository directly to verify persistence behavior.
    graph = compile_phase2_graph(mock_session, mock_research_agent, mock_analysis_agent)
    
    # We will override the nodes in the compiled graph to use a mock repo to assert calls.
    # A cleaner way is to mock the InvestigationRepository methods directly on the class.
    pass

    investigation_id = uuid.uuid4()
    
    initial_state: InvestigationGraphState = {
        "investigation_id": str(investigation_id),
        "trace_id": "trace-123",
        "query": "CVE-2024-3094",
        "query_type": QueryType.CVE,
        "status": InvestigationStatus.QUEUED,
        "memory_context": [],
        "errors": [],
        "metadata": {},
    }

    # Execute graph
    # To mock the repo calls safely, we patch InvestigationRepository
    with pytest.MonkeyPatch.context() as m:
        mock_repo = MagicMock(spec=InvestigationRepository)
        mock_repo.update_status = AsyncMock()
        mock_repo.save_research = AsyncMock()
        mock_repo.save_assessment = AsyncMock()
        
        m.setattr("backend.workflows.phase2.InvestigationRepository", lambda s: mock_repo)
        
        # Recompile graph with the patched repo
        graph = compile_phase2_graph(mock_session, mock_research_agent, mock_analysis_agent)
        final_state = await graph.ainvoke(initial_state)

        # Assertions
        assert final_state["status"] == InvestigationStatus.COMPLETED
        assert "research" in final_state
        assert "assessment" in final_state
        assert final_state["assessment"].confidence == 95

        # Verify transitions & persistence
        mock_research_agent.research.assert_called_once_with("CVE-2024-3094")
        mock_analysis_agent.analyze.assert_called_once_with(mock_research)
        mock_repo.save_research.assert_called_once()
        mock_repo.save_assessment.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_node_missing_research() -> None:
    mock_analysis_agent = MagicMock(spec=ThreatAnalysisAgent)
    mock_repo = MagicMock(spec=InvestigationRepository)
    mock_repo.update_status = AsyncMock()
    
    from backend.workflows.nodes.analyze import create_analyze_node
    analyze_node = create_analyze_node(mock_analysis_agent, mock_repo)
    
    investigation_id = uuid.uuid4()
    initial_state: InvestigationGraphState = {
        "investigation_id": str(investigation_id),
        "trace_id": "trace-123",
        "query": "CVE-2024-3094",
        "query_type": QueryType.CVE,
        "status": InvestigationStatus.QUEUED,
        # "research" is explicitly omitted
    }

    final_state = await analyze_node(initial_state)

    assert final_state["status"] == InvestigationStatus.FAILED
    assert "errors" in final_state
    assert "Research data missing" in final_state["errors"][-1]
    
    mock_repo.update_status.assert_called()


@pytest.mark.asyncio
async def test_phase2_workflow_analyze_failure(
    mock_session: AsyncSession,
    mock_research: ThreatResearch,
) -> None:
    mock_research_agent = MagicMock(spec=ResearchAgent)
    mock_research_agent.research = AsyncMock(return_value=mock_research)
    
    mock_analysis_agent = MagicMock(spec=ThreatAnalysisAgent)
    mock_analysis_agent.analyze = AsyncMock(side_effect=LLMProviderError("LLM Failure"))
    
    investigation_id = uuid.uuid4()
    initial_state: InvestigationGraphState = {
        "investigation_id": str(investigation_id),
        "trace_id": "trace-123",
        "query": "CVE-2024-3094",
        "query_type": QueryType.CVE,
        "status": InvestigationStatus.QUEUED,
    }

    with pytest.MonkeyPatch.context() as m:
        mock_repo = MagicMock(spec=InvestigationRepository)
        mock_repo.update_status = AsyncMock()
        mock_repo.save_research = AsyncMock()
        mock_repo.save_assessment = AsyncMock()
        m.setattr("backend.workflows.phase2.InvestigationRepository", lambda s: mock_repo)
        
        graph = compile_phase2_graph(mock_session, mock_research_agent, mock_analysis_agent)
        final_state = await graph.ainvoke(initial_state)

        assert final_state["status"] == InvestigationStatus.FAILED
        assert "errors" in final_state
        assert any("Analysis agent failed" in err for err in final_state["errors"])
        
        # It still persists research because research succeeded
        mock_repo.save_research.assert_called_once()
        mock_repo.save_assessment.assert_not_called()
