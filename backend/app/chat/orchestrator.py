import uuid
from collections.abc import AsyncIterator

import structlog
from pydantic_ai.messages import ModelMessage, ToolReturnPart

from app.assistant.agent import agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.auth.dependencies import AuthenticatedUser
from app.chat.messages import (
    ChatStreamRequest,
    build_assistant_message,
    build_citation_part,
    derive_title,
    extract_text,
    to_stored_content,
)
from app.chat.streaming import stream_error, stream_text_reply
from app.database import chats
from app.database.supabase import get_user_scoped_client
from app.grounding.validator import GroundingError, validate_grounding
from app.retrieval.types import SourcePassage

logger = structlog.get_logger(__name__)


async def run_turn(user: AuthenticatedUser, request: ChatStreamRequest) -> AsyncIterator[str]:
    user_message = request.messages[-1]
    is_first_turn = len(request.messages) == 1
    await chats.append_message(user, request.id, "user", to_stored_content(user_message))
    if is_first_turn:
        await chats.set_thread_title(user, request.id, derive_title(extract_text(user_message)))

    client = await get_user_scoped_client(user.access_token)
    deps = DocumentAgentDeps(user_id=user.id, thread_id=request.id, supabase_client=client)

    try:
        result = await agent.run(extract_text(user_message), deps=deps)
    except Exception:
        logger.error("chat.agent_run_failed", thread_id=request.id, exc_info=True)
        async for chunk in stream_error("The assistant is unavailable right now. Please try again."):
            yield chunk
        return

    retrieved_passages = _extract_retrieved_passages(result.all_messages())

    try:
        validate_grounding(result.output, retrieved_passages)
    except GroundingError as exc:
        logger.error("chat.grounding_failed", thread_id=request.id, detail=str(exc))
        async for chunk in stream_error(
            "The assistant couldn't produce a fully grounded answer. Please rephrase your question and try again."
        ):
            yield chunk
        return

    assistant_message_id = str(uuid.uuid4())
    cited_passages = _resolve_cited_passages(result.output, retrieved_passages)
    citation_parts = [build_citation_part(passage) for passage in cited_passages]

    async for chunk in stream_text_reply(assistant_message_id, result.output.answer, citation_parts):
        yield chunk

    assistant_message = await chats.append_message(
        user,
        request.id,
        "assistant",
        build_assistant_message(assistant_message_id, result.output.answer, citation_parts),
    )
    await chats.append_citations(user, assistant_message["id"], [c.chunk_id for c in result.output.citations])


def _resolve_cited_passages(
    answer: GroundedAnswer, retrieved_passages: list[SourcePassage]
) -> list[SourcePassage]:
    """Maps each citation's chunk_id back to the full passage retrieved this turn, in citation order."""
    passages_by_chunk_id = {passage.chunk_id: passage for passage in retrieved_passages}
    return [passages_by_chunk_id[c.chunk_id] for c in answer.citations if c.chunk_id in passages_by_chunk_id]


def _extract_retrieved_passages(messages: list[ModelMessage]) -> list[SourcePassage]:
    passages: list[SourcePassage] = []
    for message in messages:
        for part in getattr(message, "parts", []):
            if not isinstance(part, ToolReturnPart):
                continue
            content = part.content
            if isinstance(content, SourcePassage):
                passages.append(content)
            elif isinstance(content, list):
                passages.extend(item for item in content if isinstance(item, SourcePassage))
    return passages
