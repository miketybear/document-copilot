"""add tool_source citations

Revision ID: 7ef450398b93
Revises: 4dcaf666b40e
Create Date: 2026-08-03 15:49:02.036274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7ef450398b93'
down_revision: Union[str, Sequence[str], None] = '4dcaf666b40e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate also proposed dropping the hand-written HNSW/GIN indexes on document_chunks
    # (they aren't declared in the SQLAlchemy models) — removed from this migration; only the
    # message_citations changes are real, intentional changes.
    # Unlike a column added via CREATE TABLE, ADD COLUMN doesn't implicitly create a new enum
    # type — it must exist first.
    postgresql.ENUM('document', 'tool_source', name='citation_kind').create(op.get_bind(), checkfirst=True)
    op.add_column('message_citations', sa.Column('citation_kind', sa.Enum('document', 'tool_source', name='citation_kind'), server_default='document', nullable=False))
    op.add_column('message_citations', sa.Column('tool_source', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.alter_column('message_citations', 'chunk_id',
               existing_type=sa.UUID(),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('message_citations', 'chunk_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('message_citations', 'tool_source')
    op.drop_column('message_citations', 'citation_kind')

    sa.Enum(name='citation_kind').drop(op.get_bind(), checkfirst=True)
