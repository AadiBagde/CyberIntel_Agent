from uuid import UUID

from backend.agents.analysis_agent import ThreatAnalysisAgent
from backend.core.logging import get_logger
from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.enums import InvestigationStatus
from backend.workflows.state import InvestigationGraphState
from backend.services.llm.base_llm import LLMProviderError

logger = get_logger(__name__)


def create_analyze_node(agent: ThreatAnalysisAgent, repo: InvestigationRepository):
    async def analyze_node(state: InvestigationGraphState) -> InvestigationGraphState:
        investigation_id_str = state["investigation_id"]
        investigation_id = UUID(investigation_id_str)
        research = state.get("research")

        logger.info("analyze_node_start investigation_id=%s", investigation_id_str)

        deduplication = state.get("deduplication")
        if deduplication is not None and deduplication.is_duplicate:
            logger.info(
                "analyze_node_skipped investigation_id=%s reason=duplicate matched=%s",
                investigation_id_str,
                deduplication.matched_investigation_id,
            )
            if state.get("assessment") is not None:
                state["status"] = InvestigationStatus.ANALYZING
            return state

        if not research:
            error_msg = "Research data missing; cannot perform analysis."
            logger.error("analyze_node_failed investigation_id=%s reason=%s", investigation_id_str, error_msg)
            await repo.update_status(
                investigation_id,
                InvestigationStatus.FAILED,
                error_message=error_msg,
            )
            state["status"] = InvestigationStatus.FAILED
            state["errors"] = state.get("errors", []) + [error_msg]
            return state

        # We're beginning the analysis phase
        await repo.update_status(investigation_id, InvestigationStatus.ANALYZING)
        state["status"] = InvestigationStatus.ANALYZING

        try:
            assessment = await agent.analyze(research)
            state["assessment"] = assessment
            logger.info(
                "analyze_node_complete investigation_id=%s severity=%s confidence=%d",
                investigation_id_str,
                assessment.severity,
                assessment.confidence,
            )
        except LLMProviderError as exc:
            error_msg = f"Analysis agent failed: {exc}"
            logger.error("analyze_node_failed investigation_id=%s reason=%s", investigation_id_str, error_msg)
            await repo.update_status(
                investigation_id,
                InvestigationStatus.FAILED,
                error_message=error_msg,
            )
            state["status"] = InvestigationStatus.FAILED
            state["errors"] = state.get("errors", []) + [error_msg]

        return state

    return analyze_node
