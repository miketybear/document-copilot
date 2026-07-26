import pytest

from app.assistant.agent import agent
from app.assistant.deps import DocumentAgentDeps
from app.database.supabase import get_service_role_client
from app.grounding.validator import validate_grounding
from app.chat.orchestrator import _extract_retrieved_passages

pytestmark = pytest.mark.integration


async def test_real_question_produces_grounded_answer_about_the_right_document():
    client = await get_service_role_client()
    deps = DocumentAgentDeps(user_id="test-user", thread_id="test-thread", supabase_client=client)

    result = await agent.run("How do I maintain a safety level transmitter?", deps=deps)

    assert result.output.citations, "expected the agent to cite at least one passage"

    retrieved_passages = _extract_retrieved_passages(result.all_messages())
    validate_grounding(result.output, retrieved_passages)  # raises GroundingError if any citation is fabricated

    retrieved_by_id = {p.chunk_id for p in retrieved_passages}
    cited_passages = [p for p in retrieved_passages if p.chunk_id in {c.chunk_id for c in result.output.citations}]
    assert any("Safety Level Transmitter" in p.document_title for p in cited_passages)


async def test_question_with_no_relevant_documents_returns_no_fabricated_citations():
    client = await get_service_role_client()
    deps = DocumentAgentDeps(user_id="test-user", thread_id="test-thread", supabase_client=client)

    result = await agent.run("What is the company's policy on interstellar travel expenses?", deps=deps)

    retrieved_passages = _extract_retrieved_passages(result.all_messages())
    validate_grounding(result.output, retrieved_passages)  # must not raise even if citations is empty
