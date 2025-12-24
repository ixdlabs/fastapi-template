"""
Rename user verification table to user action

Revision ID: 572387925aee
Revises: 7571cbcca1dc
Create Date: 2025-12-24 11:08:21.655436
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "572387925aee"
down_revision: Union[str, Sequence[str], None] = "7571cbcca1dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sa.Enum("PENDING", "COMPLETED", "OBSELETE", name="useractionstate").create(op.get_bind())
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
            postgresql.ENUM("PENDING", "COMPLETED", "OBSELETE", name="useractionstate", create_type=False),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("hashed_token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.drop_table("user_email_verifications")
    sa.Enum("PENDING", "VERIFIED", "OBSELETE", name="useremailverificationstate").drop(op.get_bind())


def downgrade() -> None:
    sa.Enum("PENDING", "VERIFIED", "OBSELETE", name="useremailverificationstate").create(op.get_bind())
    op.create_table(
        "user_email_verifications",
        sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            "state",
            postgresql.ENUM("PENDING", "VERIFIED", "OBSELETE", name="useremailverificationstate", create_type=False),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("email", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("hashed_verification_token", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("expires_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("user_email_verifications_pkey")),
    )
    op.drop_table("user_actions")
    sa.Enum("EMAIL_VERIFICATION", "PASSWORD_RESET", name="useractiontype").drop(op.get_bind())
    sa.Enum("PENDING", "COMPLETED", "OBSELETE", name="useractionstate").drop(op.get_bind())
