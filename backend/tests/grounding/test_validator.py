import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import GroundingError, validate_grounding
from app.retrieval.types import SourcePassage


def _passage(chunk_id: str) -> SourcePassage:
    return SourcePassage(
        chunk_id=chunk_id,
        document_id="doc-1",
        document_title="Doc One",
        document_type="policy",
        department="HR",
        version="1.0",
        effective_date="2024-01-01",
        chunk_index=0,
        heading_path=[],
        chunk_text="some text",
    )


def test_citations_matching_retrieved_passages_pass():
    answer = GroundedAnswer(answer="...", citations=[Citation(chunk_id="chunk-a")])
    retrieved = [_passage("chunk-a"), _passage("chunk-b")]

    validate_grounding(answer, retrieved)  # should not raise


def test_citation_not_in_retrieved_passages_fails():
    answer = GroundedAnswer(answer="...", citations=[Citation(chunk_id="chunk-made-up")])
    retrieved = [_passage("chunk-a")]

    with pytest.raises(GroundingError):
        validate_grounding(answer, retrieved)


def test_no_citations_passes_trivially():
    answer = GroundedAnswer(answer="Not enough evidence in the corpus.", citations=[])
    retrieved = [_passage("chunk-a")]

    validate_grounding(answer, retrieved)  # should not raise


def test_one_bad_citation_among_good_ones_fails():
    answer = GroundedAnswer(
        answer="...", citations=[Citation(chunk_id="chunk-a"), Citation(chunk_id="chunk-fabricated")]
    )
    retrieved = [_passage("chunk-a"), _passage("chunk-b")]

    with pytest.raises(GroundingError):
        validate_grounding(answer, retrieved)
