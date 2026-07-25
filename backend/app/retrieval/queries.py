from supabase import AsyncClient

DEFAULT_MATCH_COUNT = 20


async def search_semantic(client: AsyncClient, query_embedding: list[float], match_count: int = DEFAULT_MATCH_COUNT) -> list[dict]:
    response = await client.rpc(
        "search_chunks_semantic",
        {"query_embedding": query_embedding, "match_count": match_count},
    ).execute()
    return response.data


async def search_fulltext(client: AsyncClient, query_text: str, match_count: int = DEFAULT_MATCH_COUNT) -> list[dict]:
    response = await client.rpc(
        "search_chunks_fulltext",
        {"query_text": query_text, "match_count": match_count},
    ).execute()
    return response.data
