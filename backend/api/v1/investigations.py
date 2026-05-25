from uuid import UUID

from fastapi import APIRouter, Depends, Request

from backend.api.deps import get_investigation_service, get_trace_id
from backend.schemas.investigation import (
    InvestigationRequest,
    InvestigationResponse,
)
from backend.services.investigation_service import InvestigationService

router = APIRouter(tags=["investigations"])


@router.post("/investigate", response_model=InvestigationResponse)
async def investigate(
    body: InvestigationRequest,
    request: Request,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationResponse:
    trace_id = get_trace_id(request) or getattr(request.state, "trace_id", "")
    return await service.run_investigation(body, trace_id=trace_id)


@router.get("/investigation/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: UUID,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationResponse:
    record = await service.get_investigation(investigation_id)
    return InvestigationResponse(investigation=record)
