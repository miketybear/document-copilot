"""add mcp connection disabled_tools

Revision ID: d3d015a6276a
Revises: 7ef450398b93
Create Date: 2026-08-04 17:16:21.705088

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3d015a6276a'
down_revision: Union[str, Sequence[str], None] = '7ef450398b93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate also proposed dropping the hand-written HNSW/GIN indexes on document_chunks
    # (they aren't declared in the SQLAlchemy models) — removed from this migration; only the
    # mcp_connections.disabled_tools column is a real, intentional change.
    op.add_column('mcp_connections', sa.Column('disabled_tools', postgresql.ARRAY(sa.String()), server_default='{}', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('mcp_connections', 'disabled_tools')
