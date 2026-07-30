import asyncio
import uuid
from collections.abc import AsyncIterator

import structlog
from pydantic_ai import AgentRunResult
from pydantic_ai.messages import ModelMessage, ToolReturnPart

from app.assistant.agent import agent, generate_title
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
from app.grounding.validator import GroundingError, strip_inline_citation_markers, validate_grounding
from app.retrieval.types import SourcePassage

logger = structlog.get_logger(__name__)

# LLMs occasionally mistranscribe a chunk_id (blend two similar-looking UUIDs, cite
# chunk_index instead, drop a character) rather than fully hallucinate one. One corrective
# retry with the validation error fed back resolves most of these without failing the turn.
_GROUNDING_RETRY_PROMPT = (
    "Your previous answer's citations failed validation: {error} Re-emit a corrected answer. "
    "Copy each chunk_id character-for-character from the search_documents/read_chunk/"
    "read_surrounding_chunks results already in this conversation — never chunk_index, a "
    "section number, or a value from memory."
)


async def run_turn(user: AuthenticatedUser, request: ChatStreamRequest) -> AsyncIterator[str]:
    user_message = request.messages[-1]
    is_first_turn = len(request.messages) == 1
    await chats.append_message(user, request.id, "user", to_stored_content(user_message))
    # Runs concurrently with the agent below (which takes much longer) instead of blocking the
    # start of the answer — awaited before the turn ends so it's always set by the time the
    # frontend refreshes the thread list.
    title_task = (
        asyncio.create_task(_set_generated_title(user, request.id, extract_text(user_message)))
        if is_first_turn
        else None
    )

    try:
        client = await get_user_scoped_client(user.access_token)
        deps = DocumentAgentDeps(user_id=user.id, thread_id=request.id, supabase_client=client)

        try:
            result, retrieved_passages = await _run_agent_grounded(extract_text(user_message), deps)
        except GroundingError as exc:
            logger.error("chat.grounding_failed", thread_id=request.id, detail=str(exc))
            async for chunk in stream_error(
                "The assistant couldn't produce a fully grounded answer. Please rephrase your question and try again."
            ):
                yield chunk
            return
        except Exception:
            logger.error("chat.agent_run_failed", thread_id=request.id, exc_info=True)
            async for chunk in stream_error("The assistant is unavailable right now. Please try again."):
                yield chunk
            return

        result.output.answer = strip_inline_citation_markers(result.output.answer)

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
    finally:
        # Always wait for it, success or failure, so the thread never gets stuck untitled.
        if title_task:
            await title_task


async def _set_generated_title(user: AuthenticatedUser, thread_id: str, text: str) -> None:
    try:
        title = await generate_title(text)
    except Exception:
        logger.warning("chat.title_generation_failed", thread_id=thread_id, exc_info=True)
        title = derive_title(text)
    # Defensive cap in case the model ignores the length instruction — derive_title's own
    # truncation already keeps its fallback output short, this just guards the LLM path too.
    await chats.set_thread_title(user, thread_id, title[:80])


def _resolve_cited_passages(
    answer: GroundedAnswer, retrieved_passages: list[SourcePassage]
) -> list[SourcePassage]:
    """Maps each citation's chunk_id back to the full passage retrieved this turn, in citation order."""
    passages_by_chunk_id = {passage.chunk_id: passage for passage in retrieved_passages}
    return [passages_by_chunk_id[c.chunk_id] for c in answer.citations if c.chunk_id in passages_by_chunk_id]


async def _run_agent_grounded(
    user_prompt: str, deps: DocumentAgentDeps
) -> tuple[AgentRunResult, list[SourcePassage]]:
    """Run the agent and validate its citations, retrying once with corrective feedback
    if a citation doesn't match a retrieved chunk_id. Raises GroundingError if the retry
    is also ungrounded."""
    result = await agent.run(user_prompt, deps=deps)
    retrieved_passages = _extract_retrieved_passages(result.all_messages())

    try:
        validate_grounding(result.output, retrieved_passages)
    except GroundingError as exc:
        result = await agent.run(
            _GROUNDING_RETRY_PROMPT.format(error=exc), message_history=result.all_messages(), deps=deps
        )
        retrieved_passages = _extract_retrieved_passages(result.all_messages())
        validate_grounding(result.output, retrieved_passages)

    return result, retrieved_passages


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
