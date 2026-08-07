import pytest
from fastapi import HTTPException

from app.auth.dependencies import AuthenticatedUser, require_admin

_ADMIN = AuthenticatedUser(id="admin-1", email="admin@example.com", access_token="t", is_admin=True)
_NON_ADMIN = AuthenticatedUser(id="user-1", email="user@example.com", access_token="t", is_admin=False)


async def test_require_admin_allows_admin_user():
    assert await require_admin(_ADMIN) is _ADMIN


async def test_require_admin_rejects_non_admin_user():
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(_NON_ADMIN)

    assert exc_info.value.status_code == 403
