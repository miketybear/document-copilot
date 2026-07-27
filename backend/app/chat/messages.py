from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.retrieval.types import SourcePassage


class UIMessagePart(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    text: str | None = None


class UIMessage(BaseModel):
    id: str
    role: Literal["system", "user", "assistant"]
    parts: list[UIMessagePart]


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    messages: list[UIMessage]
    trigger: str | None = None
    message_id: str | None = Field(default=None, alias="messageId")


def extract_text(message: UIMessage) -> str:
    """Concatenate a message's text parts. Non-text parts (tool calls, files) aren't used yet."""
    return "".join(part.text or "" for part in message.parts if part.type == "text")


def to_stored_content(message: UIMessage) -> dict:
    """The raw AI SDK message JSON, as persisted in chat_messages.content."""
    return message.model_dump(mode="json", by_alias=True)


def build_citation_part(passage: SourcePassage) -> dict:
    """A `data-citation` UI message part carrying enough metadata to render a source card."""
    return {
        "type": "data-citation",
        "id": passage.chunk_id,
        "data": {
            "chunkId": passage.chunk_id,
            "documentId": passage.document_id,
            "documentTitle": passage.document_title,
            "documentType": passage.document_type,
            "department": passage.department,
            "version": passage.version,
            "effectiveDate": passage.effective_date,
            "headingPath": passage.heading_path,
            "excerpt": passage.chunk_text,
        },
    }


def build_assistant_message(message_id: str, text: str, citation_parts: list[dict]) -> dict:
    return {
        "id": message_id,
        "role": "assistant",
        "parts": [{"type": "text", "text": text}, *citation_parts],
    }


MAX_TITLE_LENGTH = 48

# Vietnamese wh-words are frequently post-posed ("Chính sách thai sản là gì?"), so trailing
# phrases are stripped before leading ones.
_TRAILING_PHRASES = [
    "là gì", "là sao", "là như thế nào", "như thế nào", "thế nào", "ra sao", "là bao nhiêu", "bao nhiêu",
]
_LEADING_PHRASES = [
    "how do i", "how can i", "how to", "what is the", "what is", "what's the", "what's",
    "what are the", "what are", "can you tell me about", "can you tell me", "can you", "could you",
    "please tell me about", "tell me about",
    "làm sao để", "làm thế nào để", "làm sao", "làm thế nào", "cho tôi biết về", "cho biết về", "cho biết",
]


def derive_title(text: str) -> str:
    """Best-effort thread title: strip a common question phrase from the first message, then truncate."""
    cleaned = text.strip().rstrip("?!. ")

    lowered = cleaned.lower()
    for phrase in _TRAILING_PHRASES:
        if lowered.endswith(phrase):
            cleaned = cleaned[: len(cleaned) - len(phrase)].strip(" ,")
            break

    lowered = cleaned.lower()
    for phrase in _LEADING_PHRASES:
        if lowered.startswith(phrase):
            cleaned = cleaned[len(phrase) :].strip(" ,:")
            break

    cleaned = cleaned[:1].upper() + cleaned[1:] if cleaned else text.strip()

    if len(cleaned) > MAX_TITLE_LENGTH:
        cleaned = cleaned[:MAX_TITLE_LENGTH].rstrip() + "…"

    return cleaned
