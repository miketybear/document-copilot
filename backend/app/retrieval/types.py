from pydantic import BaseModel


class SourcePassage(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    document_type: str
    department: str | None
    version: str | None
    effective_date: str | None
    chunk_index: int
    heading_path: list[str]
    chunk_text: str
