from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import get_logger
from backend.db.repositories.investigation import InvestigationRepository
from backend.schemas.deduplication import (
    EXACT_MATCH_THRESHOLD,
    DeduplicationMethod,
    DeduplicationResult,
)
from backend.schemas.enums import InvestigationStatus
from backend.schemas.research import ThreatAssessment, ThreatResearch, parse_threat_assessment
from backend.utils.cve import extract_cve_id, normalize_cve_id

logger = get_logger(__name__)


@dataclass(frozen=True)
class MatchedIntelligence:
    """Prior investigation artifacts reused on duplicate detection."""

    research: ThreatResearch | None
    assessment: ThreatAssessment | None


class DeduplicationService:
    """PostgreSQL-backed duplicate detection for investigations (Phase 3)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = InvestigationRepository(session)

    def normalize_query(self, query: str) -> str:
        """Normalize a CVE query to a canonical form for comparison."""
        return normalize_cve_id(extract_cve_id(query))

    def create_fingerprint(self, *, normalized_query: str, research: ThreatResearch) -> str:
        """Build a stable SHA-256 fingerprint from normalized query and CVE id."""
        cve_id = normalize_cve_id(research.cve_id)
        payload = f"{normalized_query}:{cve_id}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def compare_existing(
        self,
        *,
        fingerprint: str,
        exclude_investigation_id: UUID,
    ) -> tuple[UUID | None, float]:
        """
        Find a prior completed investigation with the same fingerprint.

        Returns the matched investigation id and similarity score (1.0 for exact match).
        """
        row = await self._repo.find_completed_by_fingerprint(
            fingerprint,
            exclude_investigation_id=exclude_investigation_id,
        )
        if row is None:
            return None, 0.0
        return row.id, 1.0

    async def check_duplicate(
        self,
        *,
        query: str,
        research: ThreatResearch,
        investigation_id: UUID,
    ) -> DeduplicationResult:
        """
        Determine whether this investigation duplicates prior intelligence.

        On database errors, returns a safe non-duplicate fallback so the pipeline continues.
        """
        normalized = self.normalize_query(query)
        fingerprint = self.create_fingerprint(normalized_query=normalized, research=research)

        try:
            matched_id, score = await self.compare_existing(
                fingerprint=fingerprint,
                exclude_investigation_id=investigation_id,
            )
        except Exception as exc:
            logger.warning(
                "event=dedup_fallback investigation_id=%s error=%s",
                investigation_id,
                exc,
            )
            return DeduplicationResult(
                is_duplicate=False,
                similarity_score=0.0,
                reason="Deduplication lookup failed; continuing pipeline",
                method=DeduplicationMethod.FALLBACK,
            )

        if matched_id is None or score < EXACT_MATCH_THRESHOLD:
            return DeduplicationResult(
                is_duplicate=False,
                similarity_score=score,
                reason="No prior completed investigation with matching fingerprint",
                method=DeduplicationMethod.NONE,
            )

        return DeduplicationResult(
            is_duplicate=True,
            similarity_score=score,
            matched_investigation_id=str(matched_id),
            reason=f"Exact fingerprint match with prior investigation {matched_id}",
            method=DeduplicationMethod.EXACT_MATCH,
        )

    async def load_matched_intelligence(
        self,
        matched_investigation_id: UUID,
    ) -> MatchedIntelligence:
        """Load research and assessment from a prior completed investigation."""
        row = await self._repo.get_by_id(matched_investigation_id)
        if row.status != InvestigationStatus.COMPLETED:
            logger.warning(
                "event=dedup_reuse_incomplete matched_investigation_id=%s status=%s",
                matched_investigation_id,
                row.status,
            )
            return MatchedIntelligence(research=None, assessment=None)

        research = ThreatResearch.model_validate(row.research) if row.research else None
        assessment = parse_threat_assessment(row.assessment) if row.assessment else None
        return MatchedIntelligence(research=research, assessment=assessment)
