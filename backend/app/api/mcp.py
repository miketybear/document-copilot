import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.config import settings
from app.mcp import service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])

# Where the OAuth callback sends the admin's browser back to after the token exchange —
# there's no user session at that point (the request comes from the authorization server, not
# our SPA), so this can't be a normal JSON response.
_FRONTEND_CONNECTIONS_URL = f"{settings.allowed_origins_list[0]}/settings/connections"


class CreateApiTokenConnectionRequest(BaseModel):
    name: str
    server_url: str
    api_token: str


class StartOAuthConnectionRequest(BaseModel):
    name: str
    server_url: str


@router.get("/connections")
async def list_connections(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict]:
    return await service.list_connections(user)


@router.post("/connections", status_code=status.HTTP_201_CREATED)
async def create_connection(
    body: CreateApiTokenConnectionRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    return await service.create_api_token_connection(user, body.name, body.server_url, body.api_token)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_connection(connection_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> None:
    try:
        await service.delete_connection(user, connection_id)
    except service.ConnectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found") from exc


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    try:
        return await service.test_connection(user, connection_id)
    except service.ConnectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found") from exc


@router.post("/connections/oauth", status_code=status.HTTP_201_CREATED)
async def start_oauth_connection(
    body: StartOAuthConnectionRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    """Creates a pending connection and returns an authorize_url — the frontend navigates the
    browser there to complete the OAuth consent; the server never sees the admin's credentials."""
    try:
        return await service.start_oauth_connection(user, body.name, body.server_url)
    except service.OAuthConnectionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/oauth/callback", include_in_schema=False)
async def oauth_callback(code: str, state: str) -> RedirectResponse:
    """The authorization server redirects the admin's browser here after consent — no bearer
    token on this request, since it's not our SPA calling us. Ends by bouncing back to the
    connections page with a query flag the frontend can show a toast for."""
    try:
        await service.complete_oauth_callback(code, state)
    except service.OAuthConnectionError as exc:
        logger.warning("mcp.oauth_callback_failed", error=str(exc)[:500])
        return RedirectResponse(f"{_FRONTEND_CONNECTIONS_URL}?mcp_oauth=error")

    return RedirectResponse(f"{_FRONTEND_CONNECTIONS_URL}?mcp_oauth=success")
