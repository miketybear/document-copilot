import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from app.embeddings import embed_texts
from ingest.chunk import chunk_markdown
from ingest.convert import convert_to_markdown
from ingest.load import insert_chunks, upsert_document


async def ingest_file(data_dir: Path, entry: dict) -> None:
    path = data_dir / entry["file"]
    print(f"Converting {path.name}...")
    markdown = convert_to_markdown(path)

    chunks = chunk_markdown(markdown)
    print(f"  {len(chunks)} chunks, embedding...")
    embeddings = embed_texts([c.text for c in chunks])

    effective_date = date.fromisoformat(entry["effective_date"]) if entry.get("effective_date") else None

    document_id = await upsert_document(
        title=entry["title"],
        document_type=entry["document_type"],
        department=entry.get("department"),
        owner=entry.get("owner"),
        version=entry.get("version"),
        effective_date=effective_date,
        source_location=str(path),
        content_markdown=markdown,
    )
    await insert_chunks(document_id, chunks, embeddings)
    print(f"  done: document_id={document_id}")


async def main(manifest_path: Path) -> None:
    data_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest:
        await ingest_file(data_dir, entry)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("../data/manifest.json"))
    args = parser.parse_args()
    asyncio.run(main(args.manifest))
