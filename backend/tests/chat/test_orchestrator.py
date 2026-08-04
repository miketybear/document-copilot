from unittest.mock import AsyncMock

from pydantic_ai.messages import ToolReturnPart

from app.assistant.outputs import Citation, GroundedAnswer
from app.auth.dependencies import AuthenticatedUser
from app.chat import orchestrator
from app.chat.messages import ChatStreamRequest, UIMessage, UIMessagePart
from app.mcp.toolsets import MCPToolsetBundle
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
        group_title=None,
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


async def _run_and_collect(
    monkeypatch, agent_result: FakeAgentResult | AsyncMock
) -> tuple[list[str], AsyncMock, AsyncMock]:
    monkeypatch.setattr(orchestrator, "get_user_scoped_client", AsyncMock(return_value=object()))
    monkeypatch.setattr(orchestrator, "build_toolsets", AsyncMock(return_value=MCPToolsetBundle()))
    if not isinstance(agent_result, AsyncMock):
        agent_result = AsyncMock(return_value=agent_result)
    monkeypatch.setattr(orchestrator.agent, "run", agent_result)

    append_message = AsyncMock(side_effect=[{"id": "user-msg"}, {"id": "assistant-msg"}])
    append_citations = AsyncMock()
    monkeypatch.setattr(orchestrator.chats, "append_message", append_message)
    monkeypatch.setattr(orchestrator.chats, "append_citations", append_citations)
    monkeypatch.setattr(orchestrator.chats, "set_thread_title", AsyncMock())
    monkeypatch.setattr(orchestrator, "generate_title", AsyncMock(return_value="Do X"))

    chunks = [chunk async for chunk in orchestrator.run_turn(USER, _request("How do I do X?"))]
    return chunks, append_message, append_citations


async def test_valid_citation_streams_answer_and_persists_citations(monkeypatch):
    answer = GroundedAnswer(answer="You do X by following step 1.", citations=[Citation(chunk_id="chunk-a")])
    result = FakeAgentResult(answer, retrieved_passages=[_passage("chunk-a"), _passage("chunk-b")])

    chunks, append_message, append_citations = await _run_and_collect(monkeypatch, result)

    stream = "".join(chunks)
    assert '"type": "text-delta"' in stream or '"type":"text-delta"' in stream
    assert "step" in stream  # each word streams as its own delta, so check a whole word
    assert '"data-citation"' in stream
    assert '"chunk-a"' in stream
    assert "chunk-b" not in stream  # only cited passages are sent, not every retrieved one
    assert append_message.call_count == 2  # user message, then assistant message
    assistant_content = append_message.await_args_list[1].args[3]
    assert any(part["type"] == "data-citation" for part in assistant_content["parts"])
    append_citations.assert_awaited_once_with(
        USER, "assistant-msg", [{"citation_kind": "document", "chunk_id": "chunk-a"}]
    )


async def test_fabricated_citation_streams_error_and_does_not_persist_assistant_message(monkeypatch):
    answer = GroundedAnswer(answer="You do X by following step 1.", citations=[Citation(chunk_id="chunk-fabricated")])
    result = FakeAgentResult(answer, retrieved_passages=[_passage("chunk-a")])

    chunks, append_message, append_citations = await _run_and_collect(monkeypatch, result)

    stream = "".join(chunks)
    assert '"type": "error"' in stream or '"type":"error"' in stream
    assert "text-delta" not in stream  # the unvalidated answer text must never reach the client
    append_message.assert_called_once()  # only the user message was persisted, not the assistant reply
    append_citations.assert_not_awaited()


async def test_fabricated_citation_is_retried_and_recovers(monkeypatch):
    bad_result = FakeAgentResult(
        GroundedAnswer(answer="You do X by following step 1.", citations=[Citation(chunk_id="chunk-fabricated")]),
        retrieved_passages=[_passage("chunk-a")],
    )
    good_result = FakeAgentResult(
        GroundedAnswer(answer="You do X by following step 1.", citations=[Citation(chunk_id="chunk-a")]),
        retrieved_passages=[_passage("chunk-a")],
    )
    agent_run = AsyncMock(side_effect=[bad_result, good_result])

    chunks, append_message, append_citations = await _run_and_collect(monkeypatch, agent_run)

    stream = "".join(chunks)
    assert '"type": "text-delta"' in stream or '"type":"text-delta"' in stream
    assert agent_run.call_count == 2
    assert "message_history" in agent_run.call_args.kwargs  # retry continues the same conversation
    append_citations.assert_awaited_once_with(
        USER, "assistant-msg", [{"citation_kind": "document", "chunk_id": "chunk-a"}]
    )


async def test_fabricated_citation_still_bad_after_retry_streams_error(monkeypatch):
    bad_result = FakeAgentResult(
        GroundedAnswer(answer="You do X by following step 1.", citations=[Citation(chunk_id="chunk-fabricated")]),
        retrieved_passages=[_passage("chunk-a")],
    )
    agent_run = AsyncMock(side_effect=[bad_result, bad_result])

    chunks, append_message, append_citations = await _run_and_collect(monkeypatch, agent_run)

    stream = "".join(chunks)
    assert '"type": "error"' in stream or '"type":"error"' in stream
    assert agent_run.call_count == 2  # bounded: one retry, not an infinite loop
    append_message.assert_called_once()
    append_citations.assert_not_awaited()


async def test_inline_citation_marker_is_stripped_before_streaming_and_persisting(monkeypatch):
    answer = GroundedAnswer(
        answer="You do X by following step 1. [citation]", citations=[Citation(chunk_id="chunk-a")]
    )
    result = FakeAgentResult(answer, retrieved_passages=[_passage("chunk-a")])

    chunks, append_message, append_citations = await _run_and_collect(monkeypatch, result)

    stream = "".join(chunks)
    assert "[citation]" not in stream

    persisted_assistant_content = append_message.call_args_list[1].args[3]
    assert "[citation]" not in str(persisted_assistant_content)


async def test_no_citations_with_empty_retrieval_streams_answer(monkeypatch):
    answer = GroundedAnswer(answer="The corpus does not contain enough evidence to answer that.", citations=[])
    result = FakeAgentResult(answer, retrieved_passages=[])

    chunks, append_message, append_citations = await _run_and_collect(monkeypatch, result)

    stream = "".join(chunks)
    assert "evidence" in stream
    # append_citations is always called; it's the real function's job to no-op on an empty list.
    append_citations.assert_awaited_once_with(USER, "assistant-msg", [])


async def test_first_turn_sets_thread_title_from_generated_title(monkeypatch):
    answer = GroundedAnswer(answer="You do X.", citations=[Citation(chunk_id="chunk-a")])
    result = FakeAgentResult(answer, retrieved_passages=[_passage("chunk-a")])
    set_thread_title = AsyncMock()
    generate_title = AsyncMock(return_value="Doing X")

    monkeypatch.setattr(orchestrator, "get_user_scoped_client", AsyncMock(return_value=object()))
    monkeypatch.setattr(orchestrator, "build_toolsets", AsyncMock(return_value=MCPToolsetBundle()))
    monkeypatch.setattr(orchestrator.agent, "run", AsyncMock(return_value=result))
    monkeypatch.setattr(orchestrator.chats, "append_message", AsyncMock(side_effect=[{"id": "u"}, {"id": "a"}]))
    monkeypatch.setattr(orchestrator.chats, "append_citations", AsyncMock())
    monkeypatch.setattr(orchestrator.chats, "set_thread_title", set_thread_title)
    monkeypatch.setattr(orchestrator, "generate_title", generate_title)

    request = _request("How do I do X?")
    async for _ in orchestrator.run_turn(USER, request):
        pass

    generate_title.assert_awaited_once_with("How do I do X?")
    set_thread_title.assert_awaited_once_with(USER, "thread-1", "Doing X")


async def test_first_turn_falls_back_to_derived_title_when_generation_fails(monkeypatch):
    answer = GroundedAnswer(answer="You do X.", citations=[Citation(chunk_id="chunk-a")])
    result = FakeAgentResult(answer, retrieved_passages=[_passage("chunk-a")])
    set_thread_title = AsyncMock()

    monkeypatch.setattr(orchestrator, "get_user_scoped_client", AsyncMock(return_value=object()))
    monkeypatch.setattr(orchestrator, "build_toolsets", AsyncMock(return_value=MCPToolsetBundle()))
    monkeypatch.setattr(orchestrator.agent, "run", AsyncMock(return_value=result))
    monkeypatch.setattr(orchestrator.chats, "append_message", AsyncMock(side_effect=[{"id": "u"}, {"id": "a"}]))
    monkeypatch.setattr(orchestrator.chats, "append_citations", AsyncMock())
    monkeypatch.setattr(orchestrator.chats, "set_thread_title", set_thread_title)
    monkeypatch.setattr(orchestrator, "generate_title", AsyncMock(side_effect=RuntimeError("model unavailable")))

    request = _request("How do I do X?")
    async for _ in orchestrator.run_turn(USER, request):
        pass

    set_thread_title.assert_awaited_once_with(USER, "thread-1", "Do X")


async def test_later_turn_does_not_touch_thread_title(monkeypatch):
    answer = GroundedAnswer(answer="You do Y.", citations=[Citation(chunk_id="chunk-a")])
    result = FakeAgentResult(answer, retrieved_passages=[_passage("chunk-a")])
    set_thread_title = AsyncMock()

    monkeypatch.setattr(orchestrator, "get_user_scoped_client", AsyncMock(return_value=object()))
    monkeypatch.setattr(orchestrator, "build_toolsets", AsyncMock(return_value=MCPToolsetBundle()))
    monkeypatch.setattr(orchestrator.agent, "run", AsyncMock(return_value=result))
    monkeypatch.setattr(orchestrator.chats, "append_message", AsyncMock(side_effect=[{"id": "u"}, {"id": "a"}]))
    monkeypatch.setattr(orchestrator.chats, "append_citations", AsyncMock())
    monkeypatch.setattr(orchestrator.chats, "set_thread_title", set_thread_title)

    request = ChatStreamRequest(
        id="thread-1",
        messages=[
            UIMessage(id="msg-1", role="user", parts=[UIMessagePart(type="text", text="How do I do X?")]),
            UIMessage(id="msg-2", role="assistant", parts=[UIMessagePart(type="text", text="You do X.")]),
            UIMessage(id="msg-3", role="user", parts=[UIMessagePart(type="text", text="And then what?")]),
        ],
    )
    async for _ in orchestrator.run_turn(USER, request):
        pass

    set_thread_title.assert_not_awaited()
