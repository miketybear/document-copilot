from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.database.supabase import get_anon_client, get_service_role_client

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    id: str
    email: str
    access_token: str
    is_admin: bool


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    anon_client = await get_anon_client()
    try:
        response = await anon_client.auth.get_user(credentials.credentials)
    except AuthApiError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    user = response.user if response else None
    if user is None or user.email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    is_admin = user.email.lower() in settings.admin_emails_list

    service_role_client = await get_service_role_client()
    await service_role_client.table("users").upsert(
        {"id": user.id, "email": user.email, "is_admin": is_admin}
    ).execute()

    return AuthenticatedUser(id=user.id, email=user.email, access_token=credentials.credentials, is_admin=is_admin)


async def require_admin(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
