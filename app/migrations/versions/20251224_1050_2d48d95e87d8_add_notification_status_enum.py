"""
add notification status enum

Revision ID: 2d48d95e87d8
Revises: 7571cbcca1dc
Create Date: 2025-12-24 10:50:14.808389
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa  # noqa: F401
from alembic_postgresql_enum import TableReference


revision: str = "2d48d95e87d8"
down_revision: Union[str, Sequence[str], None] = "7571cbcca1dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.sync_enum_values(
        enum_schema="public",
        enum_name="notificationstatus",
        new_values=["PENDING", "SENT", "FAILED"],
        affected_columns=[
            TableReference(table_schema="public", table_name="notification_delivery", column_name="status")
        ],
        enum_values_to_rename=[],
    )


def downgrade() -> None:
    op.sync_enum_values(
        enum_schema="public",
        enum_name="notificationstatus",
        new_values=["PENDING", "SENT", "FAILED", "READ"],
        affected_columns=[
            TableReference(table_schema="public", table_name="notification_delivery", column_name="status")
        ],
        enum_values_to_rename=[],
    )
