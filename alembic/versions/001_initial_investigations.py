"""Initial investigations table

Revision ID: 001
Revises:
Create Date: 2026-05-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("query", sa.String(512), nullable=False),
        sa.Column(
            "query_type",
            sa.Enum(
                "cve",
                "malware",
                "threat_actor",
                "unknown",
                name="query_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "researching",
                "deduplicating",
                "analyzing",
                "validating",
                "persisting",
                "reporting",
                "completed",
                "failed",
                name="investigation_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("research", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("assessment", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("memory_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("report_path", sa.String(1024), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_investigations_trace_id", "investigations", ["trace_id"])
    op.create_index("ix_investigations_query", "investigations", ["query"])
    op.create_index("ix_investigations_status", "investigations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_investigations_status", table_name="investigations")
    op.drop_index("ix_investigations_query", table_name="investigations")
    op.drop_index("ix_investigations_trace_id", table_name="investigations")
    op.drop_table("investigations")
