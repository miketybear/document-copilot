"""add document_groups

Revision ID: 8f2b6a4d9c13
Revises: c4232d13b8c9
Create Date: 2026-07-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8f2b6a4d9c13'
down_revision: Union[str, Sequence[str], None] = 'c4232d13b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'document_groups',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('group_code', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_code'),
    )

    op.add_column('source_documents', sa.Column('group_id', sa.UUID(), nullable=True))
    op.add_column('source_documents', sa.Column('doc_role', sa.String(), nullable=True))
    op.create_foreign_key(
        op.f('source_documents_group_id_fkey'), 'source_documents', 'document_groups', ['group_id'], ['id']
    )
    op.create_index(op.f('ix_source_documents_group_id'), 'source_documents', ['group_id'], unique=False)

    # --- Row-Level Security (hand-written, matches source_documents/document_chunks policy) ---
    op.execute("ALTER TABLE document_groups ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY document_groups_authenticated_read ON document_groups "
        "FOR SELECT USING (auth.role() = 'authenticated')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # RLS policy is dropped implicitly by DROP TABLE below.

    op.drop_index(op.f('ix_source_documents_group_id'), table_name='source_documents')
    op.drop_constraint(op.f('source_documents_group_id_fkey'), 'source_documents', type_='foreignkey')
    op.drop_column('source_documents', 'doc_role')
    op.drop_column('source_documents', 'group_id')
    op.drop_table('document_groups')
