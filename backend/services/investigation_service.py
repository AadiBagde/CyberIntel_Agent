from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.research_agent import ResearchAgent
from backend.core.exceptions import ExternalServiceError, ValidationError, WorkflowError
from backend.core.logging import bind_trace_context, get_logger, reset_trace_context
from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.enums import InvestigationStatus, QueryType
from backend.schemas.investigation import (
    InvestigationRecord,
    InvestigationRequest,
    InvestigationResponse,
)
from backend.utils.cve import InvalidCVEError, extract_cve_id
from backend.utils.ids import generate_investigation_id
from backend.workflows.phase1 import compile_phase1_graph
from backend.workflows.state import InvestigationGraphState

logger = get_logger(__name__)


class InvestigationService:
    def __init__(
        self,
        session: AsyncSession,
        research_agent: ResearchAgent,
    ) -> None:
        self._session = session
        self._repo = InvestigationRepository(session)
        self._research_agent = research_agent

    async def run_investigation(
        self,
        request: InvestigationRequest,
        *,
        trace_id: str,
    ) -> InvestigationResponse:
        if request.query_type is not None and request.query_type != QueryType.CVE:
            raise ValidationError(
                "Phase 1 supports CVE investigations only",
                details={"query_type": request.query_type.value},
            )

        cve_id = extract_cve_id(request.query)
        investigation_id = generate_investigation_id()

        tokens = bind_trace_context(trace_id=trace_id, investigation_id=str(investigation_id))
        try:
            await self._repo.create(
                investigation_id=investigation_id,
                trace_id=trace_id,
                query=request.query,
                query_type=QueryType.CVE,
                status=InvestigationStatus.QUEUED,
            )

            logger.info(
                "investigation_created id=%s cve=%s trace=%s",
                investigation_id,
                cve_id,
                trace_id,
            )

            initial_state: InvestigationGraphState = {
                "investigation_id": str(investigation_id),
                "trace_id": trace_id,
                "query": request.query,
                "query_type": QueryType.CVE,
                "status": InvestigationStatus.QUEUED,
                "errors": [],
                "metadata": dict(request.metadata),
            }

            graph = compile_phase1_graph(self._session, self._research_agent)
            try:
                final_state = await graph.ainvoke(initial_state)
            except (ExternalServiceError, InvalidCVEError):
                await self._repo.update_status(
                    investigation_id,
                    InvestigationStatus.FAILED,
                    error_message="Research pipeline failed",
                )
                raise
            except Exception as exc:
                await self._repo.update_status(
                    investigation_id,
                    InvestigationStatus.FAILED,
                    error_message=str(exc),
                )
                logger.exception("investigation_workflow_failed id=%s", investigation_id)
                raise WorkflowError(
                    "Investigation workflow failed",
                    details={"investigation_id": str(investigation_id)},
                ) from exc

            row = await self._repo.get_by_id(investigation_id)
            record = InvestigationRepository.to_record(row)

            if final_state.get("status") == InvestigationStatus.FAILED:
                raise WorkflowError(
                    "Investigation completed with failures",
                    details={"investigation_id": str(investigation_id)},
                )

            return InvestigationResponse(investigation=record)
        finally:
            reset_trace_context(tokens)

    async def get_investigation(self, investigation_id: UUID) -> InvestigationRecord:
        row = await self._repo.get_by_id(investigation_id)
        return InvestigationRepository.to_record(row)
