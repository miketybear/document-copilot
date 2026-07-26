from pydantic import BaseModel


class Citation(BaseModel):
    chunk_id: str


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation]
