from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


def build_assistant_message(message_id: str, text: str) -> dict:
    return {
        "id": message_id,
        "role": "assistant",
        "parts": [{"type": "text", "text": text}],
    }
