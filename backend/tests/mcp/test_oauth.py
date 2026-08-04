import base64
import hashlib

import httpx
import pytest

from app.mcp import oauth


def test_generate_pkce_pair_challenge_matches_verifier():
    verifier, challenge = oauth.generate_pkce_pair()

    expected_challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode()
    assert challenge == expected_challenge
    assert "=" not in challenge  # padding must be stripped for the S256 method


def test_generate_state_is_unique_per_call():
    assert oauth.generate_state() != oauth.generate_state()


def test_expiry_timestamp_none_when_not_provided():
    assert oauth.expiry_timestamp(None) is None


def test_expiry_timestamp_returns_future_iso_string():
    from datetime import UTC, datetime

    before = datetime.now(UTC)
    result = oauth.expiry_timestamp(3600)
    parsed = datetime.fromisoformat(result)

    assert parsed > before


_RealAsyncClient = httpx.AsyncClient


def _mock_client(handler):
    def factory(**kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler))

    return factory


async def test_discover_authorization_server_falls_back_to_mcp_server_origin(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/oauth-protected-resource":
            return httpx.Response(404)
        if request.url.path == "/.well-known/oauth-authorization-server":
            return httpx.Response(
                200,
                json={
                    "authorization_endpoint": "https://mcp.example.com/authorize",
                    "token_endpoint": "https://mcp.example.com/token",
                    "registration_endpoint": "https://mcp.example.com/register",
                },
            )
        raise AssertionError(f"unexpected request to {request.url}")

    monkeypatch.setattr(oauth.httpx, "AsyncClient", _mock_client(handler))

    metadata = await oauth.discover_authorization_server("https://mcp.example.com/mcp")

    assert metadata.authorization_endpoint == "https://mcp.example.com/authorize"
    assert metadata.token_endpoint == "https://mcp.example.com/token"
    assert metadata.registration_endpoint == "https://mcp.example.com/register"


async def test_discover_authorization_server_follows_protected_resource_metadata(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/oauth-protected-resource":
            return httpx.Response(200, json={"authorization_servers": ["https://auth.example.com"]})
        if str(request.url) == "https://auth.example.com/.well-known/oauth-authorization-server":
            return httpx.Response(
                200,
                json={
                    "authorization_endpoint": "https://auth.example.com/authorize",
                    "token_endpoint": "https://auth.example.com/token",
                },
            )
        raise AssertionError(f"unexpected request to {request.url}")

    monkeypatch.setattr(oauth.httpx, "AsyncClient", _mock_client(handler))

    metadata = await oauth.discover_authorization_server("https://mcp.example.com/mcp")

    assert metadata.authorization_endpoint == "https://auth.example.com/authorize"
    assert metadata.registration_endpoint is None


async def test_discover_authorization_server_raises_when_metadata_missing(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    monkeypatch.setattr(oauth.httpx, "AsyncClient", _mock_client(handler))

    with pytest.raises(oauth.OAuthDiscoveryError):
        await oauth.discover_authorization_server("https://mcp.example.com/mcp")
