"""add user_id to payments

Revision ID: c3f1a9d2b7e4
Revises: eb638f1f9107
Create Date: 2026-09-17 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid

# revision identifiers, used by Alembic.
revision: str = 'c3f1a9d2b7e4'
down_revision: Union[str, Sequence[str], None] = 'eb638f1f9107'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing rows have no owner and are disposable dev data; clearing them lets user_id be NOT NULL.
    op.execute("DELETE FROM payments")

    # No foreign key to users: payments and auth are meant to become independent services,
    # each with its own database. For now the client sends user_id in the request body;
    # once authentication is in place it will come from the authenticated token.
    op.add_column("payments", sa.Column("user_id", Uuid(), nullable=False))
    op.create_index("ix_payments_user_id", "payments", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_column("payments", "user_id")
