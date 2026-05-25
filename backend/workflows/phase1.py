from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.research_agent import ResearchAgent
from backend.db.repositories.investigation import InvestigationRepository
from backend.workflows.builder import build_graph_with_order
from backend.workflows.nodes.bootstrap import create_bootstrap_node
from backend.workflows.nodes.persist import create_persist_node
from backend.workflows.nodes.research import create_research_node
from backend.workflows.registry import NodeRegistry

PHASE1_NODE_ORDER: tuple[str, ...] = ("bootstrap", "research", "persist_artifact")


def create_phase1_registry(
    session: AsyncSession,
    research_agent: ResearchAgent,
) -> NodeRegistry:
    repo = InvestigationRepository(session)
    registry = NodeRegistry()
    registry.register("bootstrap", create_bootstrap_node(repo))
    registry.register("research", create_research_node(research_agent, repo))
    registry.register("persist_artifact", create_persist_node(repo))
    return registry


def compile_phase1_graph(
    session: AsyncSession,
    research_agent: ResearchAgent,
) -> CompiledStateGraph:
    registry = create_phase1_registry(session, research_agent)
    return build_graph_with_order(registry, PHASE1_NODE_ORDER).compile()
