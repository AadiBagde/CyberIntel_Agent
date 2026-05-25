from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.core.exceptions import (
    CyberIntelError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from backend.core.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": exc.message, "details": exc.details},
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(_request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": exc.message, "details": exc.details},
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_handler(
        _request: Request, exc: ExternalServiceError
    ) -> JSONResponse:
        logger.error("External service error: %s", exc.message, extra={"details": exc.details})
        return JSONResponse(
            status_code=503,
            content={"error": exc.message, "details": exc.details},
        )

    @app.exception_handler(CyberIntelError)
    async def cyberintel_handler(_request: Request, exc: CyberIntelError) -> JSONResponse:
        logger.error("Application error: %s", exc.message, extra={"details": exc.details})
        return JSONResponse(
            status_code=500,
            content={"error": exc.message, "details": exc.details},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        logger.exception("Unhandled exception trace_id=%s", trace_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "trace_id": trace_id,
            },
        )
