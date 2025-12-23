"""
audit log model

Revision ID: 4b36299df787
Revises: 8fe065d4a4de
Create Date: 2025-12-23 11:08:53.402695
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4b36299df787"
down_revision: Union[str, Sequence[str], None] = "8fe065d4a4de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("actor_type", sa.Enum("USER", "SYSTEM", "ANONYMOUS", name="actortype"), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource", sa.String(), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("changed_value", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("request_ip_address", sa.String(), nullable=True),
        sa.Column("request_user_agent", sa.String(), nullable=True),
        sa.Column("request_method", sa.String(), nullable=True),
        sa.Column("request_url", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
