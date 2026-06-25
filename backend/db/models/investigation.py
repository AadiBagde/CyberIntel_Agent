from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.schemas.enums import InvestigationStatus, QueryType


class InvestigationORM(Base):
    __tablename__ = "investigations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    query_type: Mapped[QueryType] = mapped_column(
        Enum(QueryType, name="query_type", native_enum=False),
        nullable=False,
        default=QueryType.UNKNOWN,
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, name="investigation_status", native_enum=False),
        nullable=False,
        default=InvestigationStatus.QUEUED,
        index=True,
    )
    research: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    assessment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    normalized_query: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    deduplication: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    memory_context: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    report_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
