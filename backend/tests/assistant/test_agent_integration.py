import pytest

from app.assistant.deps import DocumentAgentDeps
from app.database.supabase import get_service_role_client
from app.chat.orchestrator import _run_agent_grounded

pytestmark = pytest.mark.integration

# These go through _run_agent_grounded rather than a bare agent.run: the model
# occasionally mistranscribes a chunk_id (cites chunk_index instead, or splices two
# similar-looking retrieved chunk_ids together) rather than fabricating one outright.
# _run_agent_grounded is what catches and retries that in production, so it's what
# needs to be exercised here too, or these tests just reintroduce the same flake.


async def test_real_question_produces_grounded_answer_about_the_right_document():
    client = await get_service_role_client()
    deps = DocumentAgentDeps(user_id="test-user", thread_id="test-thread", supabase_client=client)

    result, retrieved_passages = await _run_agent_grounded("How do I maintain a safety level transmitter?", deps)

    assert result.output.citations, "expected the agent to cite at least one passage"

    cited_passages = [p for p in retrieved_passages if p.chunk_id in {c.chunk_id for c in result.output.citations}]
    assert any("Safety Level Transmitter" in p.document_title for p in cited_passages)


async def test_sick_leave_question_produces_grounded_answer_about_the_right_document():
    # Regression test: the HRPPM chunk covering sick-leave termination sits at chunk_index
    # 205, right next to several other sick-leave chunks with similarly-shaped chunk_ids —
    # this is the exact case that used to trip up the model (see the fix's history).
    client = await get_service_role_client()
    deps = DocumentAgentDeps(user_id="test-user", thread_id="test-thread", supabase_client=client)

    result, retrieved_passages = await _run_agent_grounded("What is the sick leave policy?", deps)

    assert result.output.citations, "expected the agent to cite at least one passage"

    cited_passages = [p for p in retrieved_passages if p.chunk_id in {c.chunk_id for c in result.output.citations}]
    assert any("Human Resource" in p.document_title for p in cited_passages)


async def test_question_with_no_relevant_documents_returns_no_fabricated_citations():
    client = await get_service_role_client()
    deps = DocumentAgentDeps(user_id="test-user", thread_id="test-thread", supabase_client=client)

    # _run_agent_grounded raises GroundingError if any citation is fabricated; it not
    # raising is the real assertion here, regardless of whether citations end up empty.
    result, retrieved_passages = await _run_agent_grounded(
        "What is the company's policy on interstellar travel expenses?", deps
    )

    retrieved_ids = {p.chunk_id for p in retrieved_passages}
    assert all(c.chunk_id in retrieved_ids for c in result.output.citations)
