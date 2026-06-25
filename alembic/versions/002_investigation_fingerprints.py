"""Add investigation fingerprint and deduplication metadata.

Revision ID: 002
Revises: 001
Create Date: 2026-06-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("investigations", sa.Column("fingerprint", sa.String(64), nullable=True))
    op.add_column("investigations", sa.Column("normalized_query", sa.String(512), nullable=True))
    op.add_column(
        "investigations",
        sa.Column("deduplication", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_investigations_fingerprint", "investigations", ["fingerprint"])
    op.create_index("ix_investigations_normalized_query", "investigations", ["normalized_query"])


def downgrade() -> None:
    op.drop_index("ix_investigations_normalized_query", table_name="investigations")
    op.drop_index("ix_investigations_fingerprint", table_name="investigations")
    op.drop_column("investigations", "deduplication")
    op.drop_column("investigations", "normalized_query")
    op.drop_column("investigations", "fingerprint")
