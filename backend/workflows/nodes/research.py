from backend.agents.research_agent import ResearchAgent
from backend.core.logging import get_logger
from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.enums import InvestigationStatus
from backend.workflows.state import InvestigationGraphState

logger = get_logger(__name__)


def create_research_node(agent: ResearchAgent, repo: InvestigationRepository):
    async def research_node(state: InvestigationGraphState) -> InvestigationGraphState:
        investigation_id = state["investigation_id"]
        query = state["query"]
        logger.info("research_node_start investigation_id=%s", investigation_id)

        research = await agent.research(query)
        state["research"] = research
        state["status"] = InvestigationStatus.RESEARCHING
        logger.info(
            "research_node_complete investigation_id=%s cve=%s sources=%s",
            investigation_id,
            research.cve_id,
            research.data_sources,
        )
        return state

    return research_node
