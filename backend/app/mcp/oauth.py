"""OAuth 2.1 client-side plumbing for connecting to an MCP server: discovery of the
authorization server (MCP Authorization spec / RFC 9728 + RFC 8414), dynamic client
registration (RFC 7591), and the PKCE authorization-code + refresh token exchanges (RFC 7636).

There's no per-server manual setup — the admin just pastes the MCP server URL and clicks
Connect; everything else here is discovered or auto-registered."""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse

import httpx

_HTTP_TIMEOUT = 10.0


class OAuthDiscoveryError(Exception):
    """The MCP server's authorization server metadata couldn't be discovered, or doesn't
    support the dynamic client registration this flow depends on."""


@dataclass
class AuthServerMetadata:
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str | None
    expires_in: int | None


def generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge) for the S256 PKCE method."""
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def expiry_timestamp(expires_in: int | None) -> str | None:
    if expires_in is None:
        return None
    return (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def discover_authorization_server(server_url: str) -> AuthServerMetadata:
    """Follows the MCP Authorization discovery chain: the MCP server's protected-resource
    metadata names its authorization server, whose own metadata document has the endpoints we
    need. Falls back to treating the MCP server's own origin as the authorization server, for
    simpler deployments that skip the resource/AS split."""
    origin = _origin(server_url)
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        issuer = origin
        try:
            resource_metadata = await client.get(f"{origin}/.well-known/oauth-protected-resource")
            if resource_metadata.status_code == 200:
                servers = resource_metadata.json().get("authorization_servers") or []
                if servers:
                    issuer = servers[0]
        except httpx.HTTPError:
            pass  # fall through to treating the MCP server's own origin as the issuer

        try:
            as_metadata_response = await client.get(f"{issuer.rstrip('/')}/.well-known/oauth-authorization-server")
            as_metadata_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OAuthDiscoveryError(f"Couldn't discover OAuth authorization server metadata at {issuer}: {exc}") from exc

        data = as_metadata_response.json()

    try:
        return AuthServerMetadata(
            authorization_endpoint=data["authorization_endpoint"],
            token_endpoint=data["token_endpoint"],
            registration_endpoint=data.get("registration_endpoint"),
        )
    except KeyError as exc:
        raise OAuthDiscoveryError(f"OAuth metadata at {issuer} is missing required field {exc}") from exc


async def register_client(metadata: AuthServerMetadata, redirect_uri: str) -> tuple[str, str | None]:
    """Dynamic Client Registration (RFC 7591) — registers a new public client scoped to our
    redirect_uri, so the admin never has to obtain/paste a client_id themselves."""
    if metadata.registration_endpoint is None:
        raise OAuthDiscoveryError(
            "This MCP server's authorization server doesn't support dynamic client registration"
        )

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        response = await client.post(
            metadata.registration_endpoint,
            json={
                "client_name": "Document Copilot",
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
        response.raise_for_status()
        data = response.json()

    return data["client_id"], data.get("client_secret")


def build_authorize_url(
    metadata: AuthServerMetadata,
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
) -> str:
    # No RFC 8707 `resource` indicator here: the MCP Authorization spec recommends it, but
    # Entra ID's v2.0 endpoint (a common real-world authorization server for MCP gateways)
    # already encodes the target resource in `scope` and rejects a `resource` value that
    # doesn't exactly match it (AADSTS9010010) — every gateway seen so far sets `scope`
    # itself during registration, so this parameter only adds a way to conflict with that.
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{metadata.authorization_endpoint}?{urlencode(params)}"


async def exchange_code_for_tokens(
    token_endpoint: str,
    *,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str | None,
    code_verifier: str,
) -> TokenResponse:
    return await _token_request(
        token_endpoint,
        client_id=client_id,
        client_secret=client_secret,
        grant_type="authorization_code",
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
    )


async def refresh_access_token(
    token_endpoint: str, *, refresh_token: str, client_id: str, client_secret: str | None
) -> TokenResponse:
    return await _token_request(
        token_endpoint,
        client_id=client_id,
        client_secret=client_secret,
        grant_type="refresh_token",
        refresh_token=refresh_token,
    )


async def _token_request(token_endpoint: str, *, client_id: str, client_secret: str | None, **fields: str) -> TokenResponse:
    payload = {"client_id": client_id, **{k: v for k, v in fields.items() if v is not None}}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        response = await client.post(
            token_endpoint,
            data=payload,
            auth=(client_id, client_secret) if client_secret else None,
        )
        response.raise_for_status()
        data = response.json()

    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in"),
    )
