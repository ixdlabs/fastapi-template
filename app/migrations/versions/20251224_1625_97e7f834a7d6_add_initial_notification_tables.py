"""
Add initial notification tables

Revision ID: 97e7f834a7d6
Revises: 62063851dee2
Create Date: 2025-12-24 16:25:26.420367
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "97e7f834a7d6"
down_revision: Union[str, Sequence[str], None] = "62063851dee2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sa.Enum("PENDING", "SENT", "FAILED", name="notificationstatus").create(op.get_bind())
    sa.Enum("EMAIL", "SMS", "INAPP", name="notificationchannel").create(op.get_bind())
    sa.Enum("CUSTOM", "WELCOME", name="notificationtype").create(op.get_bind())
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "type", postgresql.ENUM("CUSTOM", "WELCOME", name="notificationtype", create_type=False), nullable=False
        ),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "notification_delivery",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("notification_id", sa.UUID(), nullable=False),
        sa.Column(
            "channel",
            postgresql.ENUM("EMAIL", "SMS", "INAPP", name="notificationchannel", create_type=False),
            nullable=False,
        ),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("PENDING", "SENT", "FAILED", name="notificationstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("failure_message", sa.String(), nullable=True),
        sa.Column("provider_ref", sa.String(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notification_delivery")
    op.drop_table("notifications")
    sa.Enum("CUSTOM", "WELCOME", name="notificationtype").drop(op.get_bind())
    sa.Enum("EMAIL", "SMS", "INAPP", name="notificationchannel").drop(op.get_bind())
    sa.Enum("PENDING", "SENT", "FAILED", name="notificationstatus").drop(op.get_bind())
