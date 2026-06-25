from uuid import UUID

from backend.agents.deduplication_agent import DeduplicationAgent
from backend.core.logging import get_logger
from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.enums import InvestigationStatus
from backend.workflows.state import InvestigationGraphState

logger = get_logger(__name__)


def create_deduplicate_node(agent: DeduplicationAgent, repo: InvestigationRepository):
    async def deduplicate_node(state: InvestigationGraphState) -> InvestigationGraphState:
        investigation_id_str = state["investigation_id"]
        investigation_id = UUID(investigation_id_str)

        logger.info(
            "event=dedup_node_started investigation_id=%s",
            investigation_id_str,
        )

        await repo.update_status(investigation_id, InvestigationStatus.DEDUPLICATING)
        state["status"] = InvestigationStatus.DEDUPLICATING

        state = await agent.run(state)

        deduplication = state.get("deduplication")
        if deduplication is None:
            error_msg = "Deduplication result missing after agent run."
            logger.error(
                "deduplicate_node_failed investigation_id=%s reason=%s",
                investigation_id_str,
                error_msg,
            )
            await repo.update_status(
                investigation_id,
                InvestigationStatus.FAILED,
                error_message=error_msg,
            )
            state["status"] = InvestigationStatus.FAILED
            state["errors"] = state.get("errors", []) + [error_msg]
            return state

        if deduplication.is_duplicate:
            logger.info(
                "event=dedup_node_match investigation_id=%s matched_investigation_id=%s "
                "similarity=%.2f",
                investigation_id_str,
                deduplication.matched_investigation_id,
                deduplication.similarity_score,
            )

        logger.info(
            "event=dedup_node_completed investigation_id=%s is_duplicate=%s",
            investigation_id_str,
            deduplication.is_duplicate,
        )
        return state

    return deduplicate_node
