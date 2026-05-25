from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from backend.workflows.state import InvestigationGraphState

GraphNodeFn = Callable[[InvestigationGraphState], Awaitable[InvestigationGraphState]]


@dataclass
class NodeRegistry:
    """
    Registry for LangGraph node implementations.

    Phase 0 defines topology only; node callables are registered in Phase 1+.
    """

    _nodes: dict[str, GraphNodeFn] = field(default_factory=dict)

    def register(self, name: str, fn: GraphNodeFn) -> None:
        if name in self._nodes:
            raise ValueError(f"Node '{name}' is already registered")
        self._nodes[name] = fn

    def get(self, name: str) -> GraphNodeFn | None:
        return self._nodes.get(name)

    def names(self) -> list[str]:
        return list(self._nodes.keys())


def get_default_registry() -> NodeRegistry:
    return NodeRegistry()
