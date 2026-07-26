import asyncio
import json
from collections.abc import AsyncIterator

# Matches the `ai` npm package's UI_MESSAGE_STREAM_HEADERS (src/ui-message-stream/ui-message-stream-headers.ts).
UI_MESSAGE_STREAM_HEADERS = {
    "content-type": "text/event-stream",
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "x-vercel-ai-ui-message-stream": "v1",
    "x-accel-buffering": "no",
}


def _sse(chunk: dict) -> str:
    return f"data: {json.dumps(chunk)}\n\n"


async def stream_text_reply(message_id: str, text: str) -> AsyncIterator[str]:
    """Emits a UI Message Stream Protocol response for a single text-only assistant message."""
    yield _sse({"type": "start", "messageId": message_id})
    yield _sse({"type": "start-step"})
    yield _sse({"type": "text-start", "id": message_id})

    words = text.split(" ")
    for i, word in enumerate(words):
        delta = word if i == 0 else f" {word}"
        yield _sse({"type": "text-delta", "id": message_id, "delta": delta})
        await asyncio.sleep(0.05)

    yield _sse({"type": "text-end", "id": message_id})
    yield _sse({"type": "finish-step"})
    yield _sse({"type": "finish"})
    yield "data: [DONE]\n\n"


async def stream_error(error_text: str) -> AsyncIterator[str]:
    """Emits a controlled failure instead of a polished-but-unsupported answer."""
    yield _sse({"type": "error", "errorText": error_text})
    yield "data: [DONE]\n\n"
