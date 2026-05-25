import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.core.logging import bind_trace_context, get_logger, new_trace_id, reset_trace_context

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = request.headers.get("X-Trace-Id") or new_trace_id()
        tokens = bind_trace_context(trace_id=trace_id)
        request.state.trace_id = trace_id

        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            logger.exception("Unhandled error path=%s", request.url.path)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            status_code = response.status_code if response is not None else 500
            logger.info(
                "request method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
            )
            reset_trace_context(tokens)
            if response is not None:
                response.headers["X-Trace-Id"] = trace_id
