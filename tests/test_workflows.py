from backend.workflows import compile_investigation_graph
from backend.workflows.builder import PIPELINE_NODES
from backend.workflows.phase1 import PHASE1_NODE_ORDER
from backend.workflows.registry import NodeRegistry


def test_pipeline_topology_defined() -> None:
    assert "research_node" in PIPELINE_NODES
    assert PIPELINE_NODES[-1] == "generate_report_node"


def test_phase1_node_order() -> None:
    assert PHASE1_NODE_ORDER == ("bootstrap", "research_node", "persist_artifact")


def test_bootstrap_graph_compiles_without_registry() -> None:
    graph = compile_investigation_graph()
    assert graph is not None


def test_empty_registry_uses_bootstrap() -> None:
    registry = NodeRegistry()
    assert registry.names() == []
