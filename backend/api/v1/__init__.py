from fastapi import APIRouter

from backend.api.v1 import health, investigations

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(investigations.router)
