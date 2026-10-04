"""create outbox table

Revision ID: 9c4a1e7b5d32
Revises: 7b2e5d8c1f06
Create Date: 2026-10-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c4a1e7b5d32'
down_revision: Union[str, Sequence[str], None] = '7b2e5d8c1f06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Two identities on purpose: the bigserial id gives the relay a total publication order,
    # while event_id is the stable identity consumers use to deduplicate redeliveries.
    op.create_table(
        "outbox",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("event_id", Uuid(), nullable=False),
        sa.Column("aggregate_type", sa.Text, nullable=False),
        sa.Column("aggregate_id", Uuid(), nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.Text, server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer, server_default="0", nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_id", name="uq_outbox_event_id"),
        sa.CheckConstraint("status IN ('pending', 'published', 'failed')", name="ck_outbox_status"),
    )

    # Partial: the relay only ever scans pending rows, so published/failed rows
    # (the vast majority over time) stay out of the index and keep it small.
    op.create_index(
        "ix_outbox_pending",
        "outbox",
        ["available_at", "id"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index("ix_outbox_aggregate_id", "outbox", ["aggregate_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_outbox_aggregate_id", table_name="outbox")
    op.drop_index("ix_outbox_pending", table_name="outbox", postgresql_where=sa.text("status = 'pending'"))
    op.drop_table("outbox")
