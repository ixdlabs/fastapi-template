"""
Add initial user action table

Revision ID: 5b51196b0a2c
Revises: f3569a676068
Create Date: 2025-12-25 14:29:41.387845
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "5b51196b0a2c"
down_revision = "f3569a676068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sa.Enum("PENDING", "COMPLETED", "OBSOLETE", name="useractionstate").create(op.get_bind())
    sa.Enum("EMAIL_VERIFICATION", "PASSWORD_RESET", name="useractiontype").create(op.get_bind())
    op.create_table(
        "user_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM("EMAIL_VERIFICATION", "PASSWORD_RESET", name="useractiontype", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "state",
            postgresql.ENUM("PENDING", "COMPLETED", "OBSOLETE", name="useractionstate", create_type=False),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("hashed_token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("user_actions")
    sa.Enum("EMAIL_VERIFICATION", "PASSWORD_RESET", name="useractiontype").drop(op.get_bind())
    sa.Enum("PENDING", "COMPLETED", "OBSOLETE", name="useractionstate").drop(op.get_bind())
