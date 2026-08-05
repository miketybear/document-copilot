import tiktoken
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from app.chat.messages import UIMessage, extract_text

# Bounds how much of a thread's prior turns get replayed into the model's context on every
# turn. Deliberately conservative: the agent's own instructions (~1k tokens) plus a single
# search_documents call (up to 10 chunks x 500 tokens) already cost several thousand tokens
# per turn before history is added, and a grounding retry runs the whole agent a second time.
MAX_HISTORY_TOKENS = 6000

_encoding = tiktoken.get_encoding("cl100k_base")


def build_message_history(messages: list[UIMessage]) -> list[ModelMessage]:
    """Converts a thread's prior turns (everything before the current user message) into
    pydantic_ai message history for `agent.run(message_history=...)`.

    Keeps the most recent turns and drops older ones from the front once MAX_HISTORY_TOKENS
    is exceeded, so a long thread can't grow the prompt without bound. The turn immediately
    preceding the current one is always kept even if it alone exceeds the budget, so the
    conversation never loses its most recent context.
    """
    kept: list[ModelMessage] = []
    budget = MAX_HISTORY_TOKENS

    for message in reversed(messages):
        if message.role == "system":
            continue
        text = extract_text(message)
        if not text:
            continue
        tokens = len(_encoding.encode(text))
        if kept and tokens > budget:
            break
        budget -= tokens
        kept.append(_to_model_message(message, text))

    kept.reverse()
    return kept


def _to_model_message(message: UIMessage, text: str) -> ModelMessage:
    if message.role == "user":
        return ModelRequest(parts=[UserPromptPart(content=text)])
    return ModelResponse(parts=[TextPart(content=text)])


def history_token_count(history: list[ModelMessage]) -> int:
    """Total tokens of an already-built history, for logging how much of MAX_HISTORY_TOKENS a turn used."""
    return sum(len(_encoding.encode(part.content)) for message in history for part in message.parts)
