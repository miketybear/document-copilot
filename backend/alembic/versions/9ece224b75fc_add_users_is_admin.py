"""add users is_admin

Revision ID: 9ece224b75fc
Revises: d3d015a6276a
Create Date: 2026-08-07 12:19:52.264602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ece224b75fc'
down_revision: Union[str, Sequence[str], None] = 'd3d015a6276a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate also proposed dropping the hand-written HNSW/GIN indexes on document_chunks
    # (they aren't declared in the SQLAlchemy models) — removed from this migration; only the
    # users.is_admin column is a real, intentional change.
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_admin')
