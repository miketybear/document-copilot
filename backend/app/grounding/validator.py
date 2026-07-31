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

# The underlying model has its own native citation encoding: "cite" wrapped in Private Use
# Area sentinel characters (U+E200 / U+E202 / U+E201), e.g. literally
# cite + U+E202 + "690f1be4-87c7-488d-b098-96332f79118b" + U+E201 - that sometimes leaks into
# the plain-text answer verbatim instead of staying confined to the model's own tool-call
# encoding. The sentinels have no glyph in most editors/terminals, which is why this went
# unnoticed until an actual codepoint-level inspection of a raw answer.
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_CITE_START, _CITE_SEP, _CITE_END = chr(0xE200), chr(0xE202), chr(0xE201)
_NATIVE_CITATION_MARKER = re.compile(
    rf"[ \t]?{_CITE_START}?cite{_CITE_SEP}{_UUID}{_CITE_END}", re.IGNORECASE
)

# Defense in depth in case the model instead writes the same idea out as plain ASCII (e.g.
# "cite: <uuid>") rather than the native sentinel-wrapped form above.
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
    """Remove bracket-style, native sentinel-wrapped, and bare citation markers that leaked
    into the prose."""
    cleaned = _INLINE_CITATION_MARKER.sub("", answer)
    cleaned = _NATIVE_CITATION_MARKER.sub("", cleaned)
    cleaned = _BARE_CITATION_MARKER.sub("", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    return cleaned.strip()
