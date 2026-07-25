import pytest

from app.database.supabase import get_service_role_client
from app.embeddings import embed_query
from app.retrieval.queries import search_fulltext, search_semantic
from app.retrieval.retriever import search_documents

pytestmark = pytest.mark.integration


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
