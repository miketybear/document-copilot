from datetime import date

from app.database.supabase import get_service_role_client
from ingest.chunk import Chunk


async def upsert_document(
    *,
    title: str,
    document_type: str,
    department: str | None,
    owner: str | None,
    version: str | None,
    effective_date: date | None,
    source_location: str,
    content_markdown: str,
) -> str:
    """Inserts a new source_documents row. If a `current` row with the same title
    already exists, it's marked `superseded` and pointed at the new row."""
    client = await get_service_role_client()

    existing = (
        await client.table("source_documents")
        .select("id")
        .eq("title", title)
        .eq("status", "current")
        .maybe_single()
        .execute()
    )

    response = (
        await client.table("source_documents")
        .insert(
            {
                "title": title,
                "document_type": document_type,
                "department": department,
                "owner": owner,
                "version": version,
                "effective_date": effective_date.isoformat() if effective_date else None,
                "source_location": source_location,
                "content_markdown": content_markdown,
                "status": "current",
            }
        )
        .execute()
    )
    new_id = response.data[0]["id"]

    if existing is not None and existing.data is not None:
        old_id = existing.data["id"]
        await (
            client.table("source_documents")
            .update({"status": "superseded", "superseded_by": new_id})
            .eq("id", old_id)
            .execute()
        )

    return new_id


async def insert_chunks(document_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    client = await get_service_role_client()
    rows = [
        {
            "document_id": document_id,
            "chunk_index": i,
            "heading_path": chunk.heading_path,
            "chunk_text": chunk.text,
            "embedding": embedding,
            "token_count": chunk.token_count,
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
    ]
    await client.table("document_chunks").insert(rows).execute()
