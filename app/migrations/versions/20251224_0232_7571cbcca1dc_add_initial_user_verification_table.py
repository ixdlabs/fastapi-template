"""
Add initial user verification table

Revision ID: 7571cbcca1dc
Revises: fa64084ba04d
Create Date: 2025-12-24 02:32:30.700965
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7571cbcca1dc"
down_revision: Union[str, Sequence[str], None] = "fa64084ba04d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sa.Enum("PENDING", "VERIFIED", "OBSELETE", name="useremailverificationstate").create(op.get_bind())
    op.create_table(
        "user_email_verifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "state",
            postgresql.ENUM("PENDING", "VERIFIED", "OBSELETE", name="useremailverificationstate", create_type=False),
            nullable=False,
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_verification_token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("user_email_verifications")
    sa.Enum("PENDING", "VERIFIED", "OBSELETE", name="useremailverificationstate").drop(op.get_bind())
