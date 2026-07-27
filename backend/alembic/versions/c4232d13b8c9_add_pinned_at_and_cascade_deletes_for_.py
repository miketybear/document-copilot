"""add pinned_at and cascade deletes for chat threads

Revision ID: c4232d13b8c9
Revises: 2e38ec6221b3
Create Date: 2026-07-27 14:34:07.113710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4232d13b8c9'
down_revision: Union[str, Sequence[str], None] = '2e38ec6221b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate also proposed dropping the hand-written HNSW/GIN indexes on document_chunks
    # (they aren't declared in the SQLAlchemy models) — removed from this migration; only the
    # cascade-delete FKs and the new column are real, intentional changes.
    op.drop_constraint(op.f('chat_messages_thread_id_fkey'), 'chat_messages', type_='foreignkey')
    op.create_foreign_key(None, 'chat_messages', 'chat_threads', ['thread_id'], ['id'], ondelete='CASCADE')
    op.add_column('chat_threads', sa.Column('pinned_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_constraint(op.f('message_citations_message_id_fkey'), 'message_citations', type_='foreignkey')
    op.create_foreign_key(None, 'message_citations', 'chat_messages', ['message_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'message_citations', type_='foreignkey')
    op.create_foreign_key(op.f('message_citations_message_id_fkey'), 'message_citations', 'chat_messages', ['message_id'], ['id'])
    op.drop_column('chat_threads', 'pinned_at')
    op.drop_constraint(None, 'chat_messages', type_='foreignkey')
    op.create_foreign_key(op.f('chat_messages_thread_id_fkey'), 'chat_messages', 'chat_threads', ['thread_id'], ['id'])
