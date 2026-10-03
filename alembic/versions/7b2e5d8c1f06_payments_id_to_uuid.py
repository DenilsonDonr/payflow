"""change payments.id from varchar to uuid

Revision ID: 7b2e5d8c1f06
Revises: c3f1a9d2b7e4
Create Date: 2026-10-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7b2e5d8c1f06'
down_revision: Union[str, Sequence[str], None] = 'c3f1a9d2b7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The application always treated the id as a UUID; a native uuid column makes the database
    # reject malformed ids. USING is required because Postgres has no implicit varchar -> uuid cast
    # and fails if any existing row holds a non-UUID string.
    op.execute("ALTER TABLE payments ALTER COLUMN id TYPE uuid USING id::uuid")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE payments ALTER COLUMN id TYPE varchar USING id::text")
