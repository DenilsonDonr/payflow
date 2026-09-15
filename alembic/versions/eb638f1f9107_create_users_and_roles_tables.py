"""create users and roles tables

Revision ID: eb638f1f9107
Revises: a80c0d84edbb
Create Date: 2026-09-14 22:24:01.727543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid

# revision identifiers, used by Alembic.
revision: str = 'eb638f1f9107'
down_revision: Union[str, Sequence[str], None] = 'a80c0d84edbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    roles = op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    actions = op.create_table(
        "actions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    role_permissions = op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("action_id", sa.Integer, sa.ForeignKey("actions.id"), primary_key=True),
        sa.Column("permission", sa.String, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", Uuid(), primary_key=True),
        sa.Column("email", sa.String, nullable=False),
        sa.Column("password_hash", sa.String, nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Case-insensitive: "Ana@x.com" and "ana@x.com" are the same account.
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    # Without a role no user can be created (users.role_id is NOT NULL), so the catalog ships here.
    op.bulk_insert(roles, [{"id": 1, "name": "client"}])
    op.bulk_insert(actions, [{"id": 1, "name": "payments"}])
    op.bulk_insert(
        role_permissions,
        [
            {"role_id": 1, "action_id": 1, "permission": "view"},
            {"role_id": 1, "action_id": 1, "permission": "create"},
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_users_email_lower", table_name="users")
    op.drop_table("users")
    op.drop_table("role_permissions")
    op.drop_table("actions")
    op.drop_table("roles")
