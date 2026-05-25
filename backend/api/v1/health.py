from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_health_service
from backend.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    session: AsyncSession = Depends(get_db),
    service: HealthService = Depends(get_health_service),
) -> dict:
    status = await service.check(session)
    return asdict(status)
