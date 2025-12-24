"""
Add user type for users

Revision ID: 326c0d33e8c5
Revises: a9dbf1469664
Create Date: 2025-12-24 00:37:55.168106
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "326c0d33e8c5"
down_revision: Union[str, Sequence[str], None] = "a9dbf1469664"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sa.Enum("ADMIN", "CUSTOMER", name="usertype").create(op.get_bind())
    op.add_column(
        "users",
        sa.Column(
            "type",
            postgresql.ENUM("ADMIN", "CUSTOMER", name="usertype", create_type=False),
            nullable=False,
            server_default="CUSTOMER",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "type")
    sa.Enum("ADMIN", "CUSTOMER", name="usertype").drop(op.get_bind())
