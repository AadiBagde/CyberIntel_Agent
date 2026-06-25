from uuid import UUID

from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.deduplication import DeduplicationResult
from backend.schemas.enums import InvestigationStatus
from backend.schemas.research import ThreatAssessment, ThreatResearch
from backend.workflows.state import InvestigationGraphState


def create_persist_node(repo: InvestigationRepository):
    async def persist_node(state: InvestigationGraphState) -> InvestigationGraphState:
        investigation_id = UUID(state["investigation_id"])
        research: ThreatResearch | None = state.get("research")
        assessment: ThreatAssessment | None = state.get("assessment")
        deduplication: DeduplicationResult | None = state.get("deduplication")
        fingerprint: str | None = state.get("fingerprint")
        normalized_query: str | None = state.get("normalized_query")

        if research is None:
            await repo.update_status(
                investigation_id,
                InvestigationStatus.FAILED,
                error_message="Research artifact missing after pipeline",
            )
            state["status"] = InvestigationStatus.FAILED
            return state

        final_status = state.get("status")
        if final_status != InvestigationStatus.FAILED:
            final_status = InvestigationStatus.COMPLETED

        await repo.save_research(
            investigation_id,
            research=research,
            status=InvestigationStatus.PERSISTING if assessment else final_status,
        )

        if deduplication is not None and fingerprint and normalized_query:
            await repo.save_deduplication(
                investigation_id,
                fingerprint=fingerprint,
                normalized_query=normalized_query,
                deduplication=deduplication,
                status=InvestigationStatus.PERSISTING if assessment else final_status,
            )

        if assessment:
            await repo.save_assessment(
                investigation_id,
                assessment=assessment,
                status=final_status,
            )
        elif final_status != InvestigationStatus.FAILED:
            await repo.update_status(investigation_id, final_status)

        state["status"] = final_status
        return state

    return persist_node
