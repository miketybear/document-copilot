"""add group_code filter to hybrid search rpc functions

Revision ID: 3d7e1c9b5a42
Revises: 8f2b6a4d9c13
Create Date: 2026-07-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

from app.config import settings

# revision identifiers, used by Alembic.
revision: str = '3d7e1c9b5a42'
down_revision: Union[str, Sequence[str], None] = '8f2b6a4d9c13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EMBEDDING_DIM = settings.azure_openai_embedding_dimensions


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old (vector, int) / (text, int) signatures explicitly rather than relying on
    # CREATE OR REPLACE to widen the parameter list in place — safer to verify statically than
    # to assume it keeps the same function OID instead of leaving an orphaned overload behind.
    op.execute("DROP FUNCTION IF EXISTS search_chunks_semantic(vector, int)")
    op.execute("DROP FUNCTION IF EXISTS search_chunks_fulltext(text, int)")

    op.execute(f"""
        CREATE FUNCTION search_chunks_semantic(
            query_embedding vector({_EMBEDDING_DIM}), match_count int, group_code text DEFAULT NULL
        )
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
              AND (
                group_code IS NULL
                OR sd.group_id IN (
                  SELECT dg.id FROM document_groups dg WHERE dg.group_code ILIKE '%' || group_code || '%'
                )
              )
            ORDER BY dc.embedding <=> query_embedding
            LIMIT match_count
        $$
    """)

    op.execute("""
        CREATE FUNCTION search_chunks_fulltext(
            query_text text, match_count int, group_code text DEFAULT NULL
        )
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
              AND (
                group_code IS NULL
                OR sd.group_id IN (
                  SELECT dg.id FROM document_groups dg WHERE dg.group_code ILIKE '%' || group_code || '%'
                )
              )
            ORDER BY rank DESC
            LIMIT match_count
        $$
    """)

    op.execute("GRANT EXECUTE ON FUNCTION search_chunks_semantic(vector, int, text) TO authenticated")
    op.execute("GRANT EXECUTE ON FUNCTION search_chunks_fulltext(text, int, text) TO authenticated")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP FUNCTION IF EXISTS search_chunks_semantic(vector, int, text)")
    op.execute("DROP FUNCTION IF EXISTS search_chunks_fulltext(text, int, text)")

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
