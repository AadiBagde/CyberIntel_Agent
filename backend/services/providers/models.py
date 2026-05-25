from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProviderResult(BaseModel):
    """Normalized partial intelligence from a single provider."""

    model_config = ConfigDict(extra="forbid")

    source: str
    success: bool
    cve_id: str
    error: str | None = None
    summary: str | None = None
    cvss_score: float | None = Field(default=None, ge=0.0, le=10.0)
    severity: str | None = None
    exploit_available: bool | None = None
    known_exploited: bool | None = None
    affected_products: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    cwe: list[str] = Field(default_factory=list)
    published_date: datetime | None = None
    last_modified_date: datetime | None = None
