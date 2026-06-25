from uuid import UUID

from backend.agents.base import AgentNode
from backend.core.logging import get_logger
from backend.services.deduplication_service import DeduplicationService
from backend.workflows.state import InvestigationGraphState

logger = get_logger(__name__)


class DeduplicationAgent(AgentNode):
    """Detects duplicate investigations before expensive analysis."""

    name = "deduplication_agent"

    def __init__(self, service: DeduplicationService) -> None:
        self._service = service

    async def run(self, state: InvestigationGraphState) -> InvestigationGraphState:
        investigation_id = UUID(state["investigation_id"])
        query = state["query"]
        research = state.get("research")

        logger.info(
            "event=dedup_started investigation_id=%s query=%s",
            investigation_id,
            query,
        )

        if research is None:
            error_msg = "Research data missing; cannot perform deduplication."
            logger.error(
                "event=dedup_failed investigation_id=%s reason=%s",
                investigation_id,
                error_msg,
            )
            state["errors"] = state.get("errors", []) + [error_msg]
            return state

        normalized_query = self._service.normalize_query(query)
        fingerprint = self._service.create_fingerprint(
            normalized_query=normalized_query,
            research=research,
        )

        result = await self._service.check_duplicate(
            query=query,
            research=research,
            investigation_id=investigation_id,
        )

        state["deduplication"] = result
        state["normalized_query"] = normalized_query
        state["fingerprint"] = fingerprint

        if result.is_duplicate and result.matched_investigation_id:
            matched = await self._service.load_matched_intelligence(
                UUID(result.matched_investigation_id)
            )
            if matched.research is not None:
                state["research"] = matched.research
            if matched.assessment is not None:
                state["assessment"] = matched.assessment

            logger.info(
                "event=dedup_match_found investigation_id=%s matched_investigation_id=%s "
                "similarity=%.2f reused_research=%s reused_assessment=%s",
                investigation_id,
                result.matched_investigation_id,
                result.similarity_score,
                matched.research is not None,
                matched.assessment is not None,
            )
        else:
            logger.info(
                "event=dedup_unique investigation_id=%s fingerprint=%s",
                investigation_id,
                fingerprint[:12],
            )

        logger.info(
            "event=dedup_completed investigation_id=%s is_duplicate=%s method=%s",
            investigation_id,
            result.is_duplicate,
            result.method.value,
        )

        return state
