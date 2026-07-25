import uuid
from collections.abc import AsyncIterator

from app.auth.dependencies import AuthenticatedUser
from app.chat.messages import ChatStreamRequest, build_assistant_message, to_stored_content
from app.chat.streaming import stream_text_reply
from app.database import chats

STUB_REPLY = (
    "This is a stub response from the chat pipeline — real, grounded answers "
    "arrive once retrieval and the assistant agent are wired up in a later phase."
)


async def run_stub_turn(user: AuthenticatedUser, request: ChatStreamRequest) -> AsyncIterator[str]:
    user_message = request.messages[-1]
    await chats.append_message(user, request.id, "user", to_stored_content(user_message))

    assistant_message_id = str(uuid.uuid4())

    async for chunk in stream_text_reply(assistant_message_id, STUB_REPLY):
        yield chunk

    await chats.append_message(
        user, request.id, "assistant", build_assistant_message(assistant_message_id, STUB_REPLY)
    )
