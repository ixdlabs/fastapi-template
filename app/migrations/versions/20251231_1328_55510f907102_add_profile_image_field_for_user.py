"""
Add profile image field for user

Revision ID: 55510f907102
Revises: 5b51196b0a2c
Create Date: 2025-12-31 13:28:33.534107
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy_file.types


revision = "55510f907102"
down_revision = "5b51196b0a2c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_picture", sqlalchemy_file.types.ImageField(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_picture")
