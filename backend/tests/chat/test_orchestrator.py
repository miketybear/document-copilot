from unittest.mock import AsyncMock

from pydantic_ai.messages import ToolReturnPart

from app.assistant.outputs import Citation, GroundedAnswer
from app.auth.dependencies import AuthenticatedUser
from app.chat import orchestrator
from app.chat.messages import ChatStreamRequest, UIMessage, UIMessagePart
from app.retrieval.types import SourcePassage

USER = AuthenticatedUser(id="user-1", email="user@example.com", access_token="fake-token")


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


def _request(text: str) -> ChatStreamRequest:
    return ChatStreamRequest(
        id="thread-1",
        messages=[UIMessage(id="msg-1", role="user", parts=[UIMessagePart(type="text", text=text)])],
    )


class FakeAgentResult:
    def __init__(self, output: GroundedAnswer, retrieved_passages: list[SourcePassage]):
        self.output = output
        self._retrieved_passages = retrieved_passages

    def all_messages(self):
        tool_return = ToolReturnPart(tool_name="search_documents", content=self._retrieved_passages)

        class FakeMessage:
            parts = [tool_return]

        return [FakeMessage()]


async def _run_and_collect(monkeypatch, agent_result: FakeAgentResult) -> tuple[list[str], AsyncMock, AsyncMock]:
    monkeypatch.setattr(orchestrator, "get_user_scoped_client", AsyncMock(return_value=object()))
    monkeypatch.setattr(orchestrator.agent, "run", AsyncMock(return_value=agent_result))

    append_message = AsyncMock(side_effect=[{"id": "user-msg"}, {"id": "assistant-msg"}])
    append_citations = AsyncMock()
    monkeypatch.setattr(orchestrator.chats, "append_message", append_message)
    monkeypatch.setattr(orchestrator.chats, "append_citations", append_citations)

    chunks = [chunk async for chunk in orchestrator.run_turn(USER, _request("How do I do X?"))]
    return chunks, append_message, append_citations


async def test_valid_citation_streams_answer_and_persists_citations(monkeypatch):
    answer = GroundedAnswer(answer="You do X by following step 1.", citations=[Citation(chunk_id="chunk-a")])
    result = FakeAgentResult(answer, retrieved_passages=[_passage("chunk-a"), _passage("chunk-b")])

    chunks, append_message, append_citations = await _run_and_collect(monkeypatch, result)

    stream = "".join(chunks)
    assert '"type": "text-delta"' in stream or '"type":"text-delta"' in stream
    assert "step" in stream  # each word streams as its own delta, so check a whole word
    assert append_message.call_count == 2  # user message, then assistant message
    append_citations.assert_awaited_once_with(USER, "assistant-msg", ["chunk-a"])


async def test_fabricated_citation_streams_error_and_does_not_persist_assistant_message(monkeypatch):
    answer = GroundedAnswer(answer="You do X by following step 1.", citations=[Citation(chunk_id="chunk-fabricated")])
    result = FakeAgentResult(answer, retrieved_passages=[_passage("chunk-a")])

    chunks, append_message, append_citations = await _run_and_collect(monkeypatch, result)

    stream = "".join(chunks)
    assert '"type": "error"' in stream or '"type":"error"' in stream
    assert "text-delta" not in stream  # the unvalidated answer text must never reach the client
    append_message.assert_called_once()  # only the user message was persisted, not the assistant reply
    append_citations.assert_not_awaited()


async def test_no_citations_with_empty_retrieval_streams_answer(monkeypatch):
    answer = GroundedAnswer(answer="The corpus does not contain enough evidence to answer that.", citations=[])
    result = FakeAgentResult(answer, retrieved_passages=[])

    chunks, append_message, append_citations = await _run_and_collect(monkeypatch, result)

    stream = "".join(chunks)
    assert "evidence" in stream
    # append_citations is always called; it's the real function's job to no-op on an empty list.
    append_citations.assert_awaited_once_with(USER, "assistant-msg", [])
