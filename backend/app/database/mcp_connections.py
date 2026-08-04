from app.auth.dependencies import AuthenticatedUser
from app.database.supabase import get_service_role_client, get_user_scoped_client


async def list_connections(user: AuthenticatedUser) -> list[dict]:
    client = await get_user_scoped_client(user.access_token)
    response = await client.table("mcp_connections").select("*").order("created_at").execute()
    return response.data


async def get_connection(user: AuthenticatedUser, connection_id: str) -> dict | None:
    client = await get_user_scoped_client(user.access_token)
    response = (
        await client.table("mcp_connections").select("*").eq("id", connection_id).maybe_single().execute()
    )
    return response.data if response else None


async def get_connection_by_oauth_state(oauth_state: str) -> dict | None:
    """Used by the OAuth callback, which arrives from the authorization server with no app
    session — looked up by the unguessable per-flow state token instead of a user token."""
    client = await get_service_role_client()
    response = (
        await client.table("mcp_connections")
        .select("*")
        .eq("oauth_state", oauth_state)
        .maybe_single()
        .execute()
    )
    return response.data if response else None


async def list_connected() -> list[dict]:
    """Connections currently usable by the agent, for building per-turn MCP toolsets."""
    client = await get_service_role_client()
    response = await client.table("mcp_connections").select("*").eq("status", "connected").execute()
    return response.data


async def create_connection(created_by: str, fields: dict) -> dict:
    client = await get_service_role_client()
    response = await client.table("mcp_connections").insert({**fields, "created_by": created_by}).execute()
    return response.data[0]


async def update_connection(connection_id: str, fields: dict) -> dict:
    client = await get_service_role_client()
    response = await client.table("mcp_connections").update(fields).eq("id", connection_id).execute()
    return response.data[0]


async def delete_connection(connection_id: str) -> None:
    client = await get_service_role_client()
    await client.table("mcp_connections").delete().eq("id", connection_id).execute()
