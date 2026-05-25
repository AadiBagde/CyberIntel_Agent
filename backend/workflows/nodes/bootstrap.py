from uuid import UUID

from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.enums import InvestigationStatus
from backend.workflows.state import InvestigationGraphState


def create_bootstrap_node(repo: InvestigationRepository):
    async def bootstrap_node(state: InvestigationGraphState) -> InvestigationGraphState:
        investigation_id = UUID(state["investigation_id"])
        await repo.update_status(investigation_id, InvestigationStatus.RESEARCHING)
        state["status"] = InvestigationStatus.RESEARCHING
        state["errors"] = list(state.get("errors") or [])
        return state

    return bootstrap_node
