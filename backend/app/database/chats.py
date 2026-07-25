from app.auth.dependencies import AuthenticatedUser
from app.database.supabase import get_user_scoped_client


async def create_thread(user: AuthenticatedUser, title: str | None = None) -> dict:
    client = await get_user_scoped_client(user.access_token)
    response = await client.table("chat_threads").insert({"user_id": user.id, "title": title}).execute()
    return response.data[0]


async def list_threads(user: AuthenticatedUser) -> list[dict]:
    client = await get_user_scoped_client(user.access_token)
    response = await client.table("chat_threads").select("*").order("created_at", desc=True).execute()
    return response.data


async def get_thread(user: AuthenticatedUser, thread_id: str) -> dict | None:
    """Returns None if the thread doesn't exist or isn't owned by this user — RLS makes the two indistinguishable."""
    client = await get_user_scoped_client(user.access_token)
    response = await client.table("chat_threads").select("*").eq("id", thread_id).maybe_single().execute()
    return response.data if response else None


async def list_messages(user: AuthenticatedUser, thread_id: str) -> list[dict]:
    client = await get_user_scoped_client(user.access_token)
    response = (
        await client.table("chat_messages")
        .select("*")
        .eq("thread_id", thread_id)
        .order("created_at")
        .execute()
    )
    return response.data


async def append_message(user: AuthenticatedUser, thread_id: str, role: str, content: dict) -> dict:
    client = await get_user_scoped_client(user.access_token)
    response = (
        await client.table("chat_messages")
        .insert({"thread_id": thread_id, "role": role, "content": content})
        .execute()
    )
    return response.data[0]
