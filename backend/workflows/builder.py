"""
Investigation workflow topology for LangGraph.

Phase 0: compiles a minimal bootstrap graph (no agent nodes).
Phase 1+: register node implementations via `NodeRegistry` and call
`build_investigation_graph(registry)` to wire the full pipeline.
"""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.workflows.registry import NodeRegistry, get_default_registry
from backend.workflows.state import InvestigationGraphState

PIPELINE_NODES: tuple[str, ...] = (
    "research_node",
    "deduplicate_node",
    "analyze_node",
    "validate_node",
    "persist_memory_node",
    "generate_report_node",
)


async def bootstrap_state(state: InvestigationGraphState) -> InvestigationGraphState:
    """Infrastructure node: normalizes state before agent nodes (Phase 1+)."""
    return state


def build_graph_with_order(
    registry: NodeRegistry,
    node_order: tuple[str, ...],
) -> StateGraph:
    graph: StateGraph = StateGraph(InvestigationGraphState)
    for node_name in node_order:
        fn = registry.get(node_name)
        if fn is None:
            raise ValueError(f"Missing handler for node '{node_name}'")
        graph.add_node(node_name, fn)

    graph.set_entry_point(node_order[0])
    for current, nxt in zip(node_order, node_order[1:], strict=False):
        graph.add_edge(current, nxt)
    graph.add_edge(node_order[-1], END)
    return graph


def build_investigation_graph(
    registry: NodeRegistry | None = None,
) -> StateGraph:
    reg = registry or get_default_registry()
    registered = tuple(name for name in PIPELINE_NODES if name in reg.names())

    if not registered:
        graph: StateGraph = StateGraph(InvestigationGraphState)
        graph.add_node("bootstrap", bootstrap_state)
        graph.set_entry_point("bootstrap")
        graph.add_edge("bootstrap", END)
        return graph

    return build_graph_with_order(reg, registered)


def compile_investigation_graph(
    registry: NodeRegistry | None = None,
) -> CompiledStateGraph:
    return build_investigation_graph(registry).compile()
