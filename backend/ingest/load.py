from datetime import date

from app.database.supabase import get_service_role_client
from ingest.chunk import Chunk


async def _resolve_group_id(client, group_code: str, group_title: str | None) -> str:
    """Looks up a document_groups row by group_code, creating it if it doesn't exist yet.
    group_id is stable across re-ingests, so grouping survives a member document being
    superseded (unlike keying off any single document's own id)."""
    existing = (
        await client.table("document_groups")
        .select("id")
        .eq("group_code", group_code)
        .maybe_single()
        .execute()
    )
    if existing is not None and existing.data is not None:
        return existing.data["id"]

    response = (
        await client.table("document_groups")
        .insert({"group_code": group_code, "title": group_title or group_code})
        .execute()
    )
    return response.data[0]["id"]


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
    group_code: str | None = None,
    group_title: str | None = None,
    doc_role: str | None = None,
) -> str:
    """Inserts a new source_documents row. If a `current` row with the same title already
    exists in the same group (or, for ungrouped documents, the same title with no group at
    all), it's marked `superseded` and pointed at the new row."""
    client = await get_service_role_client()

    group_id = await _resolve_group_id(client, group_code, group_title) if group_code else None

    existing_query = client.table("source_documents").select("id").eq("title", title).eq("status", "current")
    existing_query = existing_query.eq("group_id", group_id) if group_id else existing_query.is_("group_id", None)
    existing = await existing_query.maybe_single().execute()

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
                "group_id": group_id,
                "doc_role": doc_role,
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
