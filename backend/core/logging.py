import logging
import sys
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from backend.core.config import get_settings

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
investigation_id_var: ContextVar[str | None] = ContextVar("investigation_id", default=None)


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get() or "-"
        record.investigation_id = investigation_id_var.get() or "-"
        return True


def setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | trace=%(trace_id)s | inv=%(investigation_id)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(TraceContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if settings.is_production else logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_trace_id() -> str:
    return str(uuid4())


def bind_trace_context(
    *,
    trace_id: str | None = None,
    investigation_id: str | None = None,
) -> dict[str, Any]:
    tokens: dict[str, Any] = {}
    if trace_id is not None:
        tokens["trace_id"] = trace_id_var.set(trace_id)
    if investigation_id is not None:
        tokens["investigation_id"] = investigation_id_var.set(investigation_id)
    return tokens


def reset_trace_context(tokens: dict[str, Any]) -> None:
    if "trace_id" in tokens:
        trace_id_var.reset(tokens["trace_id"])
    if "investigation_id" in tokens:
        investigation_id_var.reset(tokens["investigation_id"])
