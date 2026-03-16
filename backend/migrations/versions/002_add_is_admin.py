"""add is_admin to inspectors

Revision ID: 002
Revises: 001
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'inspectors',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    op.drop_column('inspectors', 'is_admin')
