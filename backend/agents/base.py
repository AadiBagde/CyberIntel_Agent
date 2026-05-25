from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.workflows.state import InvestigationGraphState


@dataclass(frozen=True)
class AgentContext:
    """Shared runtime context passed to agent nodes."""

    trace_id: str
    investigation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentNode(ABC):
    """Contract for LangGraph-compatible agent nodes (implemented in later phases)."""

    name: str

    @abstractmethod
    async def run(self, state: InvestigationGraphState) -> InvestigationGraphState:
        """Execute agent logic and return updated graph state."""
