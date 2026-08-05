import structlog
from fastmcp import Client

from app.auth.dependencies import AuthenticatedUser
from app.config import settings
from app.database import mcp_connections as db
from app.database.models import MCPAuthType, MCPConnectionStatus
from app.mcp import crypto, oauth, toolsets

logger = structlog.get_logger(__name__)

_OAUTH_REDIRECT_URI = f"{settings.backend_base_url.rstrip('/')}/mcp/oauth/callback"

_SECRET_FIELDS = {
    "encrypted_api_token",
    "encrypted_access_token",
    "encrypted_refresh_token",
    "encrypted_oauth_client_secret",
    "oauth_state",
    "oauth_pkce_verifier",
}


class ConnectionNotFoundError(Exception):
    pass


class OAuthConnectionError(Exception):
    """An OAuth connection couldn't be started (discovery/registration failed) or completed
    (unrecognized/expired state, or the code-for-token exchange failed)."""


def _redact(connection: dict) -> dict:
    return {k: v for k, v in connection.items() if k not in _SECRET_FIELDS}


async def list_connections(user: AuthenticatedUser) -> list[dict]:
    connections = await db.list_connections(user)
    return [_redact(c) for c in connections]


async def create_api_token_connection(user: AuthenticatedUser, name: str, server_url: str, api_token: str) -> dict:
    connection = await db.create_connection(
        user.id,
        {
            "name": name.strip(),
            "server_url": server_url.strip(),
            "auth_type": MCPAuthType.api_token.value,
            "encrypted_api_token": crypto.encrypt(api_token),
        },
    )
    connection = await _verify_and_update_status(connection)
    return _redact(connection)


async def start_oauth_connection(user: AuthenticatedUser, name: str, server_url: str) -> dict:
    """Creates a `pending` connection and runs OAuth discovery + dynamic client registration,
    so the caller gets back an authorize_url to redirect the admin's browser to — no manual
    client_id/secret entry required."""
    name = name.strip()
    server_url = server_url.strip()
    try:
        metadata = await oauth.discover_authorization_server(server_url)
        client_id, client_secret = await oauth.register_client(metadata, _OAUTH_REDIRECT_URI)
    except oauth.OAuthDiscoveryError as exc:
        raise OAuthConnectionError(str(exc)) from exc

    code_verifier, code_challenge = oauth.generate_pkce_pair()
    state = oauth.generate_state()

    connection = await db.create_connection(
        user.id,
        {
            "name": name,
            "server_url": server_url,
            "auth_type": MCPAuthType.oauth2.value,
            "oauth_client_id": client_id,
            "encrypted_oauth_client_secret": crypto.encrypt(client_secret) if client_secret else None,
            "oauth_token_endpoint": metadata.token_endpoint,
            "oauth_state": state,
            "oauth_pkce_verifier": code_verifier,
        },
    )

    authorize_url = oauth.build_authorize_url(
        metadata,
        client_id=client_id,
        redirect_uri=_OAUTH_REDIRECT_URI,
        state=state,
        code_challenge=code_challenge,
    )
    return {"connection": _redact(connection), "authorize_url": authorize_url}


async def complete_oauth_callback(code: str, state: str) -> dict:
    """Exchanges the authorization code for tokens and marks the connection connected. Raises
    OAuthConnectionError if the state is unrecognized (expired, already used, or forged)."""
    connection = await db.get_connection_by_oauth_state(state)
    if connection is None:
        raise OAuthConnectionError("Unrecognized or expired OAuth state")

    client_secret = (
        crypto.decrypt(connection["encrypted_oauth_client_secret"])
        if connection.get("encrypted_oauth_client_secret")
        else None
    )
    try:
        tokens = await oauth.exchange_code_for_tokens(
            connection["oauth_token_endpoint"],
            code=code,
            redirect_uri=_OAUTH_REDIRECT_URI,
            client_id=connection["oauth_client_id"],
            client_secret=client_secret,
            code_verifier=connection["oauth_pkce_verifier"],
        )
    except Exception as exc:
        await db.update_connection(
            connection["id"], {"status": MCPConnectionStatus.error.value, "last_error": str(exc)[:500]}
        )
        raise OAuthConnectionError(str(exc)) from exc

    connection = await db.update_connection(
        connection["id"],
        {
            "encrypted_access_token": crypto.encrypt(tokens.access_token),
            "encrypted_refresh_token": crypto.encrypt(tokens.refresh_token) if tokens.refresh_token else None,
            "token_expires_at": oauth.expiry_timestamp(tokens.expires_in),
            "oauth_state": None,
            "oauth_pkce_verifier": None,
        },
    )
    connection = await _verify_and_update_status(connection)
    return _redact(connection)


async def delete_connection(user: AuthenticatedUser, connection_id: str) -> None:
    connection = await db.get_connection(user, connection_id)
    if connection is None:
        raise ConnectionNotFoundError(connection_id)
    await db.delete_connection(connection_id)


async def test_connection(user: AuthenticatedUser, connection_id: str) -> dict:
    connection = await db.get_connection(user, connection_id)
    if connection is None:
        raise ConnectionNotFoundError(connection_id)
    connection = await _verify_and_update_status(connection)
    return _redact(connection)


async def list_tools(user: AuthenticatedUser, connection_id: str) -> list[dict]:
    """Live tool list from the MCP server, each flagged with whether it's currently enabled
    for the agent to use (see app.mcp.toolsets.build_toolsets for where disabled_tools is
    actually enforced — this is read-only, for the connection detail UI)."""
    connection = await db.get_connection(user, connection_id)
    if connection is None:
        raise ConnectionNotFoundError(connection_id)

    token = await toolsets.resolve_access_token(connection)
    async with Client(connection["server_url"], auth=token) as client:
        tools = await client.list_tools()

    disabled = set(connection["disabled_tools"])
    return [{"name": tool.name, "description": tool.description, "enabled": tool.name not in disabled} for tool in tools]


async def set_disabled_tools(user: AuthenticatedUser, connection_id: str, disabled_tools: list[str]) -> dict:
    connection = await db.get_connection(user, connection_id)
    if connection is None:
        raise ConnectionNotFoundError(connection_id)
    connection = await db.update_connection(connection_id, {"disabled_tools": disabled_tools})
    return _redact(connection)


async def _verify_and_update_status(connection: dict) -> dict:
    """Connects to the remote MCP server and lists its tools, just to confirm the credential
    and URL actually work, then persists the resulting status/error for the UI's status badge."""
    token = await toolsets.resolve_access_token(connection)
    try:
        async with Client(connection["server_url"], auth=token) as client:
            await client.list_tools()
    except Exception as exc:
        # An unreachable server or a bad token is an expected outcome here, not a bug — log the
        # message only. (exc_info=True would render a full traceback that can crash structlog's
        # console renderer on Windows when the traceback contains non-cp1252 characters.)
        logger.warning("mcp.connection_test_failed", connection_id=connection["id"], error=str(exc)[:500])
        return await db.update_connection(
            connection["id"], {"status": MCPConnectionStatus.error.value, "last_error": str(exc)[:500]}
        )

    return await db.update_connection(
        connection["id"], {"status": MCPConnectionStatus.connected.value, "last_error": None}
    )
