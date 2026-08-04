import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import structlog
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import AbstractToolset

from app.database import mcp_connections as db
from app.database.models import MCPAuthType, MCPConnectionStatus
from app.mcp import crypto

logger = structlog.get_logger(__name__)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_TOOL_VERB_PREFIX = re.compile(r"^(get|search|list|find|read)_")

# Refresh an OAuth access token slightly before it actually expires, so a turn never starts a
# tool call with a token that dies mid-request.
_REFRESH_BUFFER = timedelta(minutes=2)


@dataclass
class MCPToolsetBundle:
    """The per-turn MCP toolsets to hand to `agent.run(toolsets=...)`, plus enough metadata to
    label which connection a given tool call came from afterwards (see
    `app.mcp.citations.extract_tool_source_citations`)."""

    toolsets: list[AbstractToolset] = field(default_factory=list)
    connection_name_by_prefix: dict[str, str] = field(default_factory=dict)


async def build_toolsets() -> MCPToolsetBundle:
    """One PydanticAI MCPToolset per connected MCP connection, so the agent can call out to
    external systems (e.g. Maximo) alongside its built-in document-search tools. A connection
    that fails to build (bad URL, expired token) is skipped rather than failing the whole turn —
    the same way one flaky external system shouldn't take down document search."""
    bundle = MCPToolsetBundle()
    for connection in await db.list_connected():
        try:
            token = await _resolve_access_token(connection)
            prefix = _slug(connection["name"])
            toolset = MCPToolset(connection["server_url"], auth=token, id=connection["id"]).prefixed(prefix)
            bundle.toolsets.append(toolset)
            bundle.connection_name_by_prefix[prefix] = connection["name"]
        except Exception as exc:
            # An unreachable/misconfigured connection is expected here, not a bug — see the
            # matching comment in app.mcp.service for why this skips exc_info=True.
            logger.warning("mcp.toolset_build_failed", connection_id=connection["id"], error=str(exc)[:500])
    return bundle


async def _resolve_access_token(connection: dict) -> str | None:
    if connection["auth_type"] == MCPAuthType.api_token.value:
        encrypted = connection.get("encrypted_api_token")
        return crypto.decrypt(encrypted) if encrypted else None

    expires_at = connection.get("token_expires_at")
    if expires_at is not None and _needs_refresh(expires_at):
        connection = await _refresh_oauth_tokens(connection)
    encrypted = connection.get("encrypted_access_token")
    return crypto.decrypt(encrypted) if encrypted else None


def _needs_refresh(expires_at: str) -> bool:
    expiry = datetime.fromisoformat(expires_at)
    return datetime.now(UTC) >= expiry - _REFRESH_BUFFER


async def _refresh_oauth_tokens(connection: dict) -> dict:
    from app.mcp import oauth  # local import: keeps oauth.py free of a toolsets.py import cycle

    try:
        tokens = await oauth.refresh_access_token(
            connection["oauth_token_endpoint"],
            refresh_token=crypto.decrypt(connection["encrypted_refresh_token"]),
            client_id=connection["oauth_client_id"],
            client_secret=(
                crypto.decrypt(connection["encrypted_oauth_client_secret"])
                if connection.get("encrypted_oauth_client_secret")
                else None
            ),
        )
    except Exception as exc:
        await db.update_connection(
            connection["id"],
            {"status": MCPConnectionStatus.token_expired.value, "last_error": str(exc)[:500]},
        )
        raise

    updated_fields = {
        "encrypted_access_token": crypto.encrypt(tokens.access_token),
        "token_expires_at": oauth.expiry_timestamp(tokens.expires_in),
    }
    if tokens.refresh_token:
        updated_fields["encrypted_refresh_token"] = crypto.encrypt(tokens.refresh_token)
    return await db.update_connection(connection["id"], updated_fields)


def _slug(name: str) -> str:
    return _NON_ALNUM.sub("_", name.lower()).strip("_")


def humanize_tool_name(tool_name: str) -> str:
    """Best-effort record-type label from a tool name, e.g. `search_work_orders` -> "Work Orders"."""
    stripped = _TOOL_VERB_PREFIX.sub("", tool_name)
    return stripped.replace("_", " ").title()
