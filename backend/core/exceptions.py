from typing import Any


class CyberIntelError(Exception):
    """Base application error."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(CyberIntelError):
    """Resource not found."""


class ValidationError(CyberIntelError):
    """Domain validation failure."""


class DatabaseError(CyberIntelError):
    """Database operation failure."""


class WorkflowError(CyberIntelError):
    """LangGraph workflow execution failure."""


class ExternalServiceError(CyberIntelError):
    """Upstream intelligence or vector store failure."""
