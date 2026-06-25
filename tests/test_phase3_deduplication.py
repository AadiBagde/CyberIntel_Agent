import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.analysis_agent import ThreatAnalysisAgent
from backend.agents.deduplication_agent import DeduplicationAgent
from backend.agents.research_agent import ResearchAgent
from backend.db.models.investigation import InvestigationORM
from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.deduplication import DeduplicationMethod, DeduplicationResult
from backend.schemas.enums import InvestigationStatus, QueryType, SeverityLevel
from backend.schemas.research import ThreatAssessment, ThreatResearch
from backend.services.deduplication_service import DeduplicationService
from backend.services.llm.base_llm import LLMProviderError
from backend.workflows.phase3 import PHASE3_NODE_ORDER, compile_phase3_graph
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
    return MagicMock(spec=AsyncSession)


def test_phase3_node_order() -> None:
    assert PHASE3_NODE_ORDER == (
        "bootstrap",
        "research_node",
        "deduplicate_node",
        "analyze_node",
        "persist_artifact",
    )


@pytest.mark.asyncio
async def test_deduplication_service_new_investigation_not_duplicate(
    mock_research: ThreatResearch,
) -> None:
    service = DeduplicationService(session=MagicMock())
    service._repo = MagicMock()
    service._repo.find_completed_by_fingerprint = AsyncMock(return_value=None)

    investigation_id = uuid.uuid4()
    result = await service.check_duplicate(
        query="CVE-2024-3094",
        research=mock_research,
        investigation_id=investigation_id,
    )

    assert result.is_duplicate is False
    assert result.method == DeduplicationMethod.NONE
    assert result.similarity_score == 0.0


@pytest.mark.asyncio
async def test_deduplication_service_duplicate_cve(
    mock_research: ThreatResearch,
) -> None:
    service = DeduplicationService(session=MagicMock())
    matched_id = uuid.uuid4()
    matched_row = MagicMock(spec=InvestigationORM)
    matched_row.id = matched_id

    service._repo = MagicMock()
    service._repo.find_completed_by_fingerprint = AsyncMock(return_value=matched_row)

    result = await service.check_duplicate(
        query="CVE-2024-3094",
        research=mock_research,
        investigation_id=uuid.uuid4(),
    )

    assert result.is_duplicate is True
    assert result.method == DeduplicationMethod.EXACT_MATCH
    assert result.similarity_score == 1.0
    assert result.matched_investigation_id == str(matched_id)


@pytest.mark.asyncio
async def test_deduplication_service_database_failure_fallback(
    mock_research: ThreatResearch,
) -> None:
    service = DeduplicationService(session=MagicMock())
    service._repo = MagicMock()
    service._repo.find_completed_by_fingerprint = AsyncMock(
        side_effect=RuntimeError("database unavailable")
    )

    result = await service.check_duplicate(
        query="CVE-2024-3094",
        research=mock_research,
        investigation_id=uuid.uuid4(),
    )

    assert result.is_duplicate is False
    assert result.method == DeduplicationMethod.FALLBACK
    assert "continuing pipeline" in result.reason.lower()


@pytest.mark.asyncio
async def test_deduplication_service_normalize_and_fingerprint(
    mock_research: ThreatResearch,
) -> None:
    service = DeduplicationService(session=MagicMock())

    normalized = service.normalize_query("  cve-2024-3094  ")
    assert normalized == "CVE-2024-3094"

    fp1 = service.create_fingerprint(normalized_query=normalized, research=mock_research)
    fp2 = service.create_fingerprint(normalized_query=normalized, research=mock_research)
    assert fp1 == fp2
    assert len(fp1) == 64

    variants = ["CVE-2024-3094", "cve-2024-3094", "CVE 2024 3094"]
    fingerprints = [
        service.create_fingerprint(
            normalized_query=service.normalize_query(q),
            research=mock_research,
        )
        for q in variants
    ]
    assert len(set(fingerprints)) == 1


@pytest.mark.asyncio
async def test_deduplication_service_load_matched_intelligence(
    mock_research: ThreatResearch,
    mock_assessment: ThreatAssessment,
) -> None:
    matched_id = uuid.uuid4()
    matched_row = MagicMock(spec=InvestigationORM)
    matched_row.status = InvestigationStatus.COMPLETED
    matched_row.research = mock_research.model_dump(mode="json")
    matched_row.assessment = mock_assessment.model_dump(mode="json")

    service = DeduplicationService(session=MagicMock())
    service._repo = MagicMock()
    service._repo.get_by_id = AsyncMock(return_value=matched_row)

    matched = await service.load_matched_intelligence(matched_id)

    assert matched.research is not None
    assert matched.research.cve_id == "CVE-2024-3094"
    assert matched.assessment is not None
    assert matched.assessment.confidence == 95


@pytest.mark.asyncio
async def test_deduplication_agent_reuses_prior_intelligence(
    mock_research: ThreatResearch,
    mock_assessment: ThreatAssessment,
) -> None:
    matched_id = uuid.uuid4()
    matched_row = MagicMock(spec=InvestigationORM)
    matched_row.id = matched_id
    matched_row.status = InvestigationStatus.COMPLETED
    matched_row.research = mock_research.model_dump(mode="json")
    matched_row.assessment = mock_assessment.model_dump(mode="json")

    service = DeduplicationService(session=MagicMock())
    service._repo = MagicMock()
    service._repo.find_completed_by_fingerprint = AsyncMock(return_value=matched_row)
    service._repo.get_by_id = AsyncMock(return_value=matched_row)

    agent = DeduplicationAgent(service)
    investigation_id = uuid.uuid4()
    state: InvestigationGraphState = {
        "investigation_id": str(investigation_id),
        "trace_id": "trace-reuse",
        "query": "cve 2024 3094",
        "query_type": QueryType.CVE,
        "status": InvestigationStatus.RESEARCHING,
        "research": mock_research,
    }

    final_state = await agent.run(state)

    assert final_state["deduplication"].is_duplicate is True
    assert final_state["research"].cve_id == "CVE-2024-3094"
    assert final_state["assessment"] is not None
    assert final_state["assessment"].confidence == 95


@pytest.mark.asyncio
async def test_phase3_workflow_success(
    mock_session: AsyncSession,
    mock_research: ThreatResearch,
    mock_assessment: ThreatAssessment,
) -> None:
    mock_research_agent = MagicMock(spec=ResearchAgent)
    mock_research_agent.research = AsyncMock(return_value=mock_research)

    mock_analysis_agent = MagicMock(spec=ThreatAnalysisAgent)
    mock_analysis_agent.analyze = AsyncMock(return_value=mock_assessment)

    mock_dedup_agent = MagicMock(spec=DeduplicationAgent)
    mock_dedup_agent.run = AsyncMock(
        side_effect=lambda state: {
            **state,
            "deduplication": DeduplicationResult(
                is_duplicate=False,
                reason="No prior completed investigation with matching fingerprint",
                method=DeduplicationMethod.NONE,
            ),
            "fingerprint": "abc123",
            "normalized_query": "CVE-2024-3094",
        }
    )

    investigation_id = uuid.uuid4()
    initial_state: InvestigationGraphState = {
        "investigation_id": str(investigation_id),
        "trace_id": "trace-123",
        "query": "CVE-2024-3094",
        "query_type": QueryType.CVE,
        "status": InvestigationStatus.QUEUED,
        "errors": [],
        "metadata": {},
    }

    with pytest.MonkeyPatch.context() as m:
        mock_repo = MagicMock(spec=InvestigationRepository)
        mock_repo.update_status = AsyncMock()
        mock_repo.save_research = AsyncMock()
        mock_repo.save_assessment = AsyncMock()
        mock_repo.save_deduplication = AsyncMock()
        m.setattr("backend.workflows.phase3.InvestigationRepository", lambda s: mock_repo)

        graph = compile_phase3_graph(
            mock_session,
            mock_research_agent,
            mock_dedup_agent,
            mock_analysis_agent,
        )
        final_state = await graph.ainvoke(initial_state)

        assert final_state["status"] == InvestigationStatus.COMPLETED
        assert final_state["deduplication"].is_duplicate is False
        mock_research_agent.research.assert_called_once_with("CVE-2024-3094")
        mock_dedup_agent.run.assert_called_once()
        mock_analysis_agent.analyze.assert_called_once_with(mock_research)
        mock_repo.save_deduplication.assert_called_once()


@pytest.mark.asyncio
async def test_phase3_workflow_duplicate_skips_analysis(
    mock_session: AsyncSession,
    mock_research: ThreatResearch,
    mock_assessment: ThreatAssessment,
) -> None:
    matched_id = uuid.uuid4()
    mock_research_agent = MagicMock(spec=ResearchAgent)
    mock_research_agent.research = AsyncMock(return_value=mock_research)

    mock_analysis_agent = MagicMock(spec=ThreatAnalysisAgent)
    mock_analysis_agent.analyze = AsyncMock(return_value=mock_assessment)

    mock_dedup_agent = MagicMock(spec=DeduplicationAgent)
    mock_dedup_agent.run = AsyncMock(
        side_effect=lambda state: {
            **state,
            "deduplication": DeduplicationResult(
                is_duplicate=True,
                similarity_score=1.0,
                matched_investigation_id=str(matched_id),
                reason=f"Exact fingerprint match with prior investigation {matched_id}",
                method=DeduplicationMethod.EXACT_MATCH,
            ),
            "fingerprint": "abc123",
            "normalized_query": "CVE-2024-3094",
            "assessment": mock_assessment,
        }
    )

    investigation_id = uuid.uuid4()
    initial_state: InvestigationGraphState = {
        "investigation_id": str(investigation_id),
        "trace_id": "trace-456",
        "query": "CVE-2024-3094",
        "query_type": QueryType.CVE,
        "status": InvestigationStatus.QUEUED,
        "errors": [],
        "metadata": {},
    }

    with pytest.MonkeyPatch.context() as m:
        mock_repo = MagicMock(spec=InvestigationRepository)
        mock_repo.update_status = AsyncMock()
        mock_repo.save_research = AsyncMock()
        mock_repo.save_assessment = AsyncMock()
        mock_repo.save_deduplication = AsyncMock()
        m.setattr("backend.workflows.phase3.InvestigationRepository", lambda s: mock_repo)

        graph = compile_phase3_graph(
            mock_session,
            mock_research_agent,
            mock_dedup_agent,
            mock_analysis_agent,
        )
        final_state = await graph.ainvoke(initial_state)

        assert final_state["status"] == InvestigationStatus.COMPLETED
        assert final_state["deduplication"].is_duplicate is True
        mock_analysis_agent.analyze.assert_not_called()
        mock_repo.save_assessment.assert_called_once()


@pytest.mark.asyncio
async def test_phase3_workflow_analyze_failure_still_persists_research(
    mock_session: AsyncSession,
    mock_research: ThreatResearch,
) -> None:
    mock_research_agent = MagicMock(spec=ResearchAgent)
    mock_research_agent.research = AsyncMock(return_value=mock_research)

    mock_analysis_agent = MagicMock(spec=ThreatAnalysisAgent)
    mock_analysis_agent.analyze = AsyncMock(side_effect=LLMProviderError("LLM Failure"))

    mock_dedup_agent = MagicMock(spec=DeduplicationAgent)
    mock_dedup_agent.run = AsyncMock(
        side_effect=lambda state: {
            **state,
            "deduplication": DeduplicationResult(is_duplicate=False, method=DeduplicationMethod.NONE),
            "fingerprint": "abc123",
            "normalized_query": "CVE-2024-3094",
        }
    )

    investigation_id = uuid.uuid4()
    initial_state: InvestigationGraphState = {
        "investigation_id": str(investigation_id),
        "trace_id": "trace-789",
        "query": "CVE-2024-3094",
        "query_type": QueryType.CVE,
        "status": InvestigationStatus.QUEUED,
    }

    with pytest.MonkeyPatch.context() as m:
        mock_repo = MagicMock(spec=InvestigationRepository)
        mock_repo.update_status = AsyncMock()
        mock_repo.save_research = AsyncMock()
        mock_repo.save_assessment = AsyncMock()
        mock_repo.save_deduplication = AsyncMock()
        m.setattr("backend.workflows.phase3.InvestigationRepository", lambda s: mock_repo)

        graph = compile_phase3_graph(
            mock_session,
            mock_research_agent,
            mock_dedup_agent,
            mock_analysis_agent,
        )
        final_state = await graph.ainvoke(initial_state)

        assert final_state["status"] == InvestigationStatus.FAILED
        mock_repo.save_research.assert_called_once()
        mock_repo.save_assessment.assert_not_called()
