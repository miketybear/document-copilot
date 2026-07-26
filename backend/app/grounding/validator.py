from app.assistant.outputs import GroundedAnswer
from app.retrieval.types import SourcePassage


class GroundingError(Exception):
    """A citation referenced a chunk_id that was never retrieved during this turn."""


def validate_grounding(answer: GroundedAnswer, retrieved_passages: list[SourcePassage]) -> None:
    """The model cannot cite documents that were not retrieved for the current request."""
    retrieved_ids = {passage.chunk_id for passage in retrieved_passages}

    for citation in answer.citations:
        if citation.chunk_id not in retrieved_ids:
            raise GroundingError(
                f"Citation references chunk_id {citation.chunk_id!r}, which was not retrieved this turn"
            )
