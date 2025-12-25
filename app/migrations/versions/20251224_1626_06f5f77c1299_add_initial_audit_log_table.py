"""
Add initial audit log table

Revision ID: 06f5f77c1299
Revises: 97e7f834a7d6
Create Date: 2025-12-24 16:26:20.787667
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "06f5f77c1299"
down_revision: Union[str, Sequence[str], None] = "97e7f834a7d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sa.Enum("USER", "SYSTEM", "ANONYMOUS", name="actortype").create(op.get_bind())
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column(
            "actor_type",
            postgresql.ENUM("USER", "SYSTEM", "ANONYMOUS", name="actortype", create_type=False),
            nullable=False,
        ),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("changed_value", sa.JSON(), nullable=True),
        sa.Column("trace_id", sa.String(), nullable=True),
        sa.Column("request_ip_address", sa.String(), nullable=True),
        sa.Column("request_user_agent", sa.String(), nullable=True),
        sa.Column("request_method", sa.String(), nullable=True),
        sa.Column("request_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    sa.Enum("USER", "SYSTEM", "ANONYMOUS", name="actortype").drop(op.get_bind())
