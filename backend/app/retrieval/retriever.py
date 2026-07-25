from supabase import AsyncClient

from app.embeddings import embed_query
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import search_fulltext, search_semantic
from app.retrieval.types import SourcePassage

CANDIDATE_POOL_SIZE = 20

_PASSAGE_SELECT = "*, source_documents(title, document_type, department, version, effective_date)"


async def search_documents(client: AsyncClient, query: str, k: int = 10) -> list[SourcePassage]:
    """The main hybrid-search bounded tool: embeds the query, runs semantic + full-text
    search, fuses the two ranked lists with RRF, and returns the top-k passages."""
    query_embedding = embed_query(query)

    semantic_results = await search_semantic(client, query_embedding, match_count=CANDIDATE_POOL_SIZE)
    fulltext_results = await search_fulltext(client, query, match_count=CANDIDATE_POOL_SIZE)

    rankings = [
        [row["id"] for row in semantic_results],
        [row["id"] for row in fulltext_results],
    ]
    fused_ids = reciprocal_rank_fusion(rankings)[:k]

    return await _fetch_passages(client, fused_ids)


async def read_chunk(client: AsyncClient, chunk_id: str) -> SourcePassage | None:
    passages = await _fetch_passages(client, [chunk_id])
    return passages[0] if passages else None


async def read_surrounding_chunks(
    client: AsyncClient, chunk_id: str, before: int = 1, after: int = 1
) -> list[SourcePassage]:
    anchor = await read_chunk(client, chunk_id)
    if anchor is None:
        return []

    response = (
        await client.table("document_chunks")
        .select(_PASSAGE_SELECT)
        .eq("document_id", anchor.document_id)
        .gte("chunk_index", anchor.chunk_index - before)
        .lte("chunk_index", anchor.chunk_index + after)
        .order("chunk_index")
        .execute()
    )
    return [_row_to_passage(row) for row in response.data]


async def _fetch_passages(client: AsyncClient, chunk_ids: list[str]) -> list[SourcePassage]:
    if not chunk_ids:
        return []

    response = await client.table("document_chunks").select(_PASSAGE_SELECT).in_("id", chunk_ids).execute()
    by_id = {row["id"]: _row_to_passage(row) for row in response.data}
    return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]


def _row_to_passage(row: dict) -> SourcePassage:
    doc = row["source_documents"]
    return SourcePassage(
        chunk_id=row["id"],
        document_id=row["document_id"],
        document_title=doc["title"],
        document_type=doc["document_type"],
        department=doc["department"],
        version=doc["version"],
        effective_date=doc["effective_date"],
        chunk_index=row["chunk_index"],
        heading_path=row["heading_path"] or [],
        chunk_text=row["chunk_text"],
    )
