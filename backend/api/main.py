from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.exceptions import register_exception_handlers
from backend.api.middleware import RequestContextMiddleware
from backend.api.v1 import api_v1_router
from backend.core.config import get_settings
from backend.core.logging import setup_logging
from backend.db.session import close_db, init_db
from backend.memory.vector_store import QdrantVectorStore
from backend.services.http_client import ResilientHttpClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging()
    await init_db()
    app.state.vector_store = QdrantVectorStore()
    app.state.http_client = ResilientHttpClient(settings)
    yield
    await app.state.http_client.close()
    store: QdrantVectorStore = app.state.vector_store
    await store.close()
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Agentic cybersecurity investigation platform",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.get("/health", include_in_schema=False)
    async def root_health_redirect() -> dict:
        return {"status": "ok", "docs": "/docs", "api": settings.api_v1_prefix}

    return app


app = create_app()
