from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.chat.messages import ChatStreamRequest
from app.chat.orchestrator import run_turn
from app.chat.streaming import UI_MESSAGE_STREAM_HEADERS
from app.database import chats

router = APIRouter(prefix="/chat", tags=["chat"])


class CreateThreadRequest(BaseModel):
    title: str | None = None


@router.post("/threads")
async def create_thread(
    body: CreateThreadRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    return await chats.create_thread(user, body.title)


@router.get("/threads")
async def list_threads(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict]:
    return await chats.list_threads(user)


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    thread = await chats.get_thread(user, thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    messages = await chats.list_messages(user, thread_id)
    return {**thread, "messages": messages}


@router.post("/stream")
async def stream_chat(
    request: ChatStreamRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> StreamingResponse:
    thread = await chats.get_thread(user, request.id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    return StreamingResponse(run_turn(user, request), headers=UI_MESSAGE_STREAM_HEADERS)
