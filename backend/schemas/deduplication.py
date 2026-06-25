from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# Phase 3: exact fingerprint match requires full similarity.
EXACT_MATCH_THRESHOLD: float = 1.0
# Phase 5: semantic near-duplicate cutoff for Qdrant vector search.
VECTOR_SIMILARITY_THRESHOLD: float = 0.85


class DeduplicationMethod(str, Enum):
    """How duplicate detection was performed."""

    EXACT_FINGERPRINT = "exact_fingerprint"
    EXACT_MATCH = "exact_match"
    NORMALIZED_QUERY = "normalized_query"
    VECTOR_SIMILARITY = "vector_similarity"
    NONE = "none"
    FALLBACK = "fallback"


class DeduplicationResult(BaseModel):
    """Structured output from the deduplication stage."""

    model_config = ConfigDict(extra="forbid")

    is_duplicate: bool = False
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_investigation_id: str | None = None
    reason: str = ""
    method: DeduplicationMethod = DeduplicationMethod.NONE
