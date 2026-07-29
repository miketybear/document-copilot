import uuid
from collections.abc import AsyncIterator

from pydantic_ai import AgentRunResult
from pydantic_ai.messages import ModelMessage, ToolReturnPart

from app.assistant.agent import agent
from app.assistant.deps import DocumentAgentDeps
from app.auth.dependencies import AuthenticatedUser
from app.chat.messages import ChatStreamRequest, build_assistant_message, extract_text, to_stored_content
from app.chat.streaming import stream_error, stream_text_reply
from app.database import chats
from app.database.supabase import get_user_scoped_client
from app.grounding.validator import GroundingError, validate_grounding
from app.retrieval.types import SourcePassage

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
    await chats.append_message(user, request.id, "user", to_stored_content(user_message))

    client = await get_user_scoped_client(user.access_token)
    deps = DocumentAgentDeps(user_id=user.id, thread_id=request.id, supabase_client=client)

    try:
        result, retrieved_passages = await _run_agent_grounded(extract_text(user_message), deps)
    except GroundingError as exc:
        async for chunk in stream_error(str(exc)):
            yield chunk
        return
    except Exception as exc:
        async for chunk in stream_error(f"The assistant is unavailable right now: {exc}"):
            yield chunk
        return

    assistant_message_id = str(uuid.uuid4())

    async for chunk in stream_text_reply(assistant_message_id, result.output.answer):
        yield chunk

    assistant_message = await chats.append_message(
        user, request.id, "assistant", build_assistant_message(assistant_message_id, result.output.answer)
    )
    await chats.append_citations(user, assistant_message["id"], [c.chunk_id for c in result.output.citations])


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
