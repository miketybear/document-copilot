"""add hybrid search rpc functions

Revision ID: 72b7224321fb
Revises: 4e7320c767ec
Create Date: 2026-07-25 17:35:58.370741

"""
from typing import Sequence, Union

from alembic import op

from app.config import settings

# revision identifiers, used by Alembic.
revision: str = '72b7224321fb'
down_revision: Union[str, Sequence[str], None] = '4e7320c767ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EMBEDDING_DIM = settings.azure_openai_embedding_dimensions


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"""
        CREATE FUNCTION search_chunks_semantic(query_embedding vector({_EMBEDDING_DIM}), match_count int)
        RETURNS TABLE (
            id uuid,
            document_id uuid,
            chunk_index int,
            heading_path text[],
            chunk_text text,
            token_count int,
            distance float
        )
        LANGUAGE sql STABLE SECURITY INVOKER AS $$
            SELECT dc.id, dc.document_id, dc.chunk_index, dc.heading_path, dc.chunk_text, dc.token_count,
                   dc.embedding <=> query_embedding AS distance
            FROM document_chunks dc
            JOIN source_documents sd ON sd.id = dc.document_id
            WHERE sd.status = 'current'
            ORDER BY dc.embedding <=> query_embedding
            LIMIT match_count
        $$
    """)

    op.execute("""
        CREATE FUNCTION search_chunks_fulltext(query_text text, match_count int)
        RETURNS TABLE (
            id uuid,
            document_id uuid,
            chunk_index int,
            heading_path text[],
            chunk_text text,
            token_count int,
            rank float
        )
        LANGUAGE sql STABLE SECURITY INVOKER AS $$
            SELECT dc.id, dc.document_id, dc.chunk_index, dc.heading_path, dc.chunk_text, dc.token_count,
                   ts_rank(dc.search_vector, plainto_tsquery('english', query_text)) AS rank
            FROM document_chunks dc
            JOIN source_documents sd ON sd.id = dc.document_id
            WHERE sd.status = 'current'
              AND dc.search_vector @@ plainto_tsquery('english', query_text)
            ORDER BY rank DESC
            LIMIT match_count
        $$
    """)

    op.execute("GRANT EXECUTE ON FUNCTION search_chunks_semantic(vector, int) TO authenticated")
    op.execute("GRANT EXECUTE ON FUNCTION search_chunks_fulltext(text, int) TO authenticated")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP FUNCTION IF EXISTS search_chunks_semantic(vector, int)")
    op.execute("DROP FUNCTION IF EXISTS search_chunks_fulltext(text, int)")
