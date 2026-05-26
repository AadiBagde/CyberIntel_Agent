from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.analysis_agent import ThreatAnalysisAgent
from backend.agents.research_agent import ResearchAgent
from backend.db.repositories.investigation import InvestigationRepository
from backend.workflows.builder import build_graph_with_order
from backend.workflows.nodes.analyze import create_analyze_node
from backend.workflows.nodes.bootstrap import create_bootstrap_node
from backend.workflows.nodes.persist import create_persist_node
from backend.workflows.nodes.research import create_research_node
from backend.workflows.registry import NodeRegistry

PHASE2_NODE_ORDER: tuple[str, ...] = ("bootstrap", "research_node", "analyze_node", "persist_artifact")


def create_phase2_registry(
    session: AsyncSession,
    research_agent: ResearchAgent,
    analysis_agent: ThreatAnalysisAgent,
) -> NodeRegistry:
    repo = InvestigationRepository(session)
    registry = NodeRegistry()
    registry.register("bootstrap", create_bootstrap_node(repo))
    registry.register("research_node", create_research_node(research_agent, repo))
    registry.register("analyze_node", create_analyze_node(analysis_agent, repo))
    registry.register("persist_artifact", create_persist_node(repo))
    return registry


def compile_phase2_graph(
    session: AsyncSession,
    research_agent: ResearchAgent,
    analysis_agent: ThreatAnalysisAgent,
) -> CompiledStateGraph:
    registry = create_phase2_registry(session, research_agent, analysis_agent)
    return build_graph_with_order(registry, PHASE2_NODE_ORDER).compile()
