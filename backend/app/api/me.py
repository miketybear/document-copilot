from fastapi import APIRouter, Depends

from app.auth.dependencies import AuthenticatedUser, get_current_user

router = APIRouter()


@router.get("/me")
async def read_current_user(user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, str]:
    return {"id": user.id, "email": user.email}
