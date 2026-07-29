import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import GroundingError, strip_inline_citation_markers, validate_grounding
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


def test_strip_inline_citation_markers_removes_bracket_citation_word():
    text = "Employees on approved leave are paid at half pay after 10 days. [citation]"

    assert strip_inline_citation_markers(text) == "Employees on approved leave are paid at half pay after 10 days."


def test_strip_inline_citation_markers_removes_footnote_style_numbers():
    text = "Absence without notice is treated as unauthorized leave [1]."

    assert strip_inline_citation_markers(text) == "Absence without notice is treated as unauthorized leave."


def test_strip_inline_citation_markers_removes_multiple_markers_across_sentences():
    text = "First rule applies here [citation]. Second rule applies there [2]. Third point stands [source]."

    assert strip_inline_citation_markers(text) == (
        "First rule applies here. Second rule applies there. Third point stands."
    )


def test_strip_inline_citation_markers_removes_chunk_id_leak():
    text = "The policy requires manager approval [chunk_id: abc-123]."

    assert strip_inline_citation_markers(text) == "The policy requires manager approval."


def test_strip_inline_citation_markers_leaves_clean_prose_untouched():
    text = "You are entitled to 10 days of paid sick leave per year."

    assert strip_inline_citation_markers(text) == text


def test_strip_inline_citation_markers_preserves_paragraph_breaks():
    text = "First paragraph. [citation]\n\nSecond paragraph stands on its own."

    assert strip_inline_citation_markers(text) == "First paragraph.\n\nSecond paragraph stands on its own."
