"""
Add initial user and user action tables

Revision ID: 62063851dee2
Revises:
Create Date: 2025-12-24 16:24:26.457688
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "62063851dee2"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sa.Enum("PENDING", "COMPLETED", "OBSELETE", name="useractionstate").create(op.get_bind())
    sa.Enum("EMAIL_VERIFICATION", "PASSWORD_RESET", name="useractiontype").create(op.get_bind())
    sa.Enum("ADMIN", "CUSTOMER", name="usertype").create(op.get_bind())
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
            postgresql.ENUM("PENDING", "COMPLETED", "OBSELETE", name="useractionstate", create_type=False),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("hashed_token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("type", postgresql.ENUM("ADMIN", "CUSTOMER", name="usertype", create_type=False), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("user_actions")
    sa.Enum("ADMIN", "CUSTOMER", name="usertype").drop(op.get_bind())
    sa.Enum("EMAIL_VERIFICATION", "PASSWORD_RESET", name="useractiontype").drop(op.get_bind())
    sa.Enum("PENDING", "COMPLETED", "OBSELETE", name="useractionstate").drop(op.get_bind())
