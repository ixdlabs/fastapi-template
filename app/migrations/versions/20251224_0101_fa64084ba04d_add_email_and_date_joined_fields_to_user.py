"""
Add email and date_joined fields to user

Revision ID: fa64084ba04d
Revises: 326c0d33e8c5
Create Date: 2025-12-24 01:01:24.840204
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fa64084ba04d"
down_revision: Union[str, Sequence[str], None] = "326c0d33e8c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("joined_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE users SET joined_at = created_at WHERE joined_at IS NULL")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("joined_at", nullable=False)
        batch_op.create_unique_constraint("uq_users_email", ["email"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")
        batch_op.drop_column("joined_at")
        batch_op.drop_column("email")
