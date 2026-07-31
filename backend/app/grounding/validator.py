import re

from app.assistant.outputs import GroundedAnswer
from app.retrieval.types import SourcePassage

# The model is instructed to put citations only in the structured `citations` field, but
# occasionally leaks a bracket-style marker into the prose anyway. Strip these as defense in
# depth so the frontend never renders a raw marker to the user.
_INLINE_CITATION_MARKER = re.compile(
    r"[ \t]?\[(?:citations?|sources?|refs?|references?|docs?|footnotes?|\d+|chunk[-_]?id\s*:?\s*[\w-]+)\]",
    re.IGNORECASE,
)

# Occasionally the leak skips the brackets entirely too — e.g. "...caring.citefa098285-924e-
# 4d14-8e8e-ea9261f81b9b3501e04b-9217-42c0-b39f-ac1a5a312881" (the word glued directly to one
# or more raw chunk_id UUIDs, no separator). Catch that shape directly since the bracket regex
# above can't.
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_BARE_CITATION_MARKER = re.compile(
    rf"[ \t]?(?:cites?|citations?|sources?|refs?|references?|chunk[-_]?ids?)\s*:?\s*(?:{_UUID}\s*)+",
    re.IGNORECASE,
)


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


def strip_inline_citation_markers(answer: str) -> str:
    """Remove bracket-style and bare citation-word-plus-UUID markers that leaked into the prose."""
    cleaned = _INLINE_CITATION_MARKER.sub("", answer)
    cleaned = _BARE_CITATION_MARKER.sub("", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    return cleaned.strip()
