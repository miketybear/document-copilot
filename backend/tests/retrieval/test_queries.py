import uuid

import pytest

from app.config import settings
from app.database.supabase import get_service_role_client
from app.embeddings import embed_query
from app.retrieval.queries import search_fulltext, search_semantic
from app.retrieval.retriever import search_documents

pytestmark = pytest.mark.integration


async def _create_grouped_chunk(client, group_code: str, chunk_text: str) -> tuple[str, list[float]]:
    group = await client.table("document_groups").insert({"group_code": group_code, "title": group_code}).execute()
    group_id = group.data[0]["id"]

    doc = await (
        client.table("source_documents")
        .insert(
            {
                "title": f"doc-{uuid.uuid4()}",
                "document_type": "policy",
                "content_markdown": chunk_text,
                "group_id": group_id,
            }
        )
        .execute()
    )
    document_id = doc.data[0]["id"]

    embedding = [0.001] * settings.azure_openai_embedding_dimensions
    chunk = await (
        client.table("document_chunks")
        .insert({"document_id": document_id, "chunk_index": 0, "chunk_text": chunk_text, "embedding": embedding})
        .execute()
    )
    return chunk.data[0]["id"], embedding


async def test_fulltext_search_finds_relevant_chunk():
    client = await get_service_role_client()

    results = await search_fulltext(client, "safety transmitter maintenance", match_count=5)

    assert len(results) > 0


async def test_semantic_search_finds_relevant_chunk():
    client = await get_service_role_client()
    query_embedding = embed_query("How do I maintain a safety level transmitter?")

    results = await search_semantic(client, query_embedding, match_count=5)

    assert len(results) > 0


async def test_search_documents_returns_passages_from_the_right_document():
    client = await get_service_role_client()

    results = await search_documents(client, "How do I maintain a safety level transmitter?", k=5)

    assert len(results) > 0
    assert any("Safety Level Transmitter" in p.document_title for p in results)


async def test_search_semantic_scopes_to_group_code():
    client = await get_service_role_client()
    group_code = f"group-{uuid.uuid4()}"
    chunk_id, embedding = await _create_grouped_chunk(client, group_code, f"drilling contract clause {uuid.uuid4()}")

    scoped = await search_semantic(client, embedding, match_count=5, group_code=group_code)
    assert any(row["id"] == chunk_id for row in scoped)

    other_group = await search_semantic(client, embedding, match_count=5, group_code=f"other-{uuid.uuid4()}")
    assert not any(row["id"] == chunk_id for row in other_group)


async def test_search_semantic_group_code_matches_by_substring():
    client = await get_service_role_client()
    unique_suffix = str(uuid.uuid4())
    group_code = f"HD-2026-{unique_suffix}"
    chunk_id, embedding = await _create_grouped_chunk(client, group_code, f"drilling contract clause {uuid.uuid4()}")

    # A partial fragment of the code (case-insensitive) should still match.
    scoped = await search_semantic(client, embedding, match_count=5, group_code=unique_suffix.upper())
    assert any(row["id"] == chunk_id for row in scoped)


async def test_search_fulltext_scopes_to_group_code():
    client = await get_service_role_client()
    unique_text = f"drilling contract penalty clause {uuid.uuid4()}"
    group_code = f"group-{uuid.uuid4()}"
    chunk_id, _ = await _create_grouped_chunk(client, group_code, unique_text)

    scoped = await search_fulltext(client, unique_text, match_count=5, group_code=group_code)
    assert any(row["id"] == chunk_id for row in scoped)

    other_group = await search_fulltext(client, unique_text, match_count=5, group_code=f"other-{uuid.uuid4()}")
    assert not any(row["id"] == chunk_id for row in other_group)
