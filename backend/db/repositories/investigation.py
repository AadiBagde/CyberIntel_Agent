from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import NotFoundError
from backend.db.models.investigation import InvestigationORM
from backend.schemas.deduplication import DeduplicationResult
from backend.schemas.enums import InvestigationStatus, QueryType
from backend.schemas.investigation import InvestigationRecord
from backend.schemas.research import ThreatAssessment, ThreatResearch, ValidationResult, parse_threat_assessment


class InvestigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        investigation_id: UUID,
        trace_id: str,
        query: str,
        query_type: QueryType,
        status: InvestigationStatus = InvestigationStatus.QUEUED,
    ) -> InvestigationORM:
        row = InvestigationORM(
            id=investigation_id,
            trace_id=trace_id,
            query=query,
            query_type=query_type,
            status=status,
            memory_context=[],
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id(self, investigation_id: UUID) -> InvestigationORM:
        result = await self._session.execute(
            select(InvestigationORM).where(InvestigationORM.id == investigation_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(
                f"Investigation {investigation_id} not found",
                details={"investigation_id": str(investigation_id)},
            )
        return row

    async def update_status(
        self,
        investigation_id: UUID,
        status: InvestigationStatus,
        *,
        error_message: str | None = None,
    ) -> InvestigationORM:
        row = await self.get_by_id(investigation_id)
        row.status = status
        if error_message is not None:
            row.error_message = error_message
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def save_research(
        self,
        investigation_id: UUID,
        *,
        research: ThreatResearch,
        status: InvestigationStatus,
    ) -> InvestigationORM:
        row = await self.get_by_id(investigation_id)
        row.research = research.model_dump(mode="json")
        row.status = status
        row.error_message = None
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def save_assessment(
        self,
        investigation_id: UUID,
        *,
        assessment: ThreatAssessment,
        status: InvestigationStatus,
    ) -> InvestigationORM:
        row = await self.get_by_id(investigation_id)
        row.assessment = assessment.model_dump(mode="json")
        row.status = status
        row.error_message = None
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def find_completed_by_fingerprint(
        self,
        fingerprint: str,
        *,
        exclude_investigation_id: UUID,
    ) -> InvestigationORM | None:
        result = await self._session.execute(
            select(InvestigationORM)
            .where(
                InvestigationORM.fingerprint == fingerprint,
                InvestigationORM.status == InvestigationStatus.COMPLETED,
                InvestigationORM.id != exclude_investigation_id,
            )
            .order_by(InvestigationORM.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_deduplication(
        self,
        investigation_id: UUID,
        *,
        fingerprint: str,
        normalized_query: str,
        deduplication: DeduplicationResult,
        status: InvestigationStatus,
    ) -> InvestigationORM:
        row = await self.get_by_id(investigation_id)
        row.fingerprint = fingerprint
        row.normalized_query = normalized_query
        row.deduplication = deduplication.model_dump(mode="json")
        row.status = status
        row.error_message = None
        await self._session.flush()
        await self._session.refresh(row)
        return row

    @staticmethod
    def to_record(row: InvestigationORM) -> InvestigationRecord:
        research = ThreatResearch.model_validate(row.research) if row.research else None
        assessment = parse_threat_assessment(row.assessment) if row.assessment else None
        validation = ValidationResult.model_validate(row.validation) if row.validation else None
        deduplication = (
            DeduplicationResult.model_validate(row.deduplication) if row.deduplication else None
        )
        return InvestigationRecord(
            id=row.id,
            trace_id=row.trace_id,
            query=row.query,
            query_type=row.query_type,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
            research=research,
            assessment=assessment,
            validation=validation,
            deduplication=deduplication,
            fingerprint=row.fingerprint,
            normalized_query=row.normalized_query,
            memory_context=row.memory_context or [],
            report_path=row.report_path,
            error_message=row.error_message,
        )
