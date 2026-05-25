from uuid import UUID

from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.enums import InvestigationStatus
from backend.schemas.research import ThreatResearch
from backend.workflows.state import InvestigationGraphState


def create_persist_node(repo: InvestigationRepository):
    async def persist_node(state: InvestigationGraphState) -> InvestigationGraphState:
        investigation_id = UUID(state["investigation_id"])
        research: ThreatResearch | None = state.get("research")

        if research is None:
            await repo.update_status(
                investigation_id,
                InvestigationStatus.FAILED,
                error_message="Research artifact missing after pipeline",
            )
            state["status"] = InvestigationStatus.FAILED
            return state

        await repo.save_research(
            investigation_id,
            research=research,
            status=InvestigationStatus.COMPLETED,
        )
        state["status"] = InvestigationStatus.COMPLETED
        return state

    return persist_node
