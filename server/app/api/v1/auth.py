from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_user
from app.schemas.auth import LoginRequest
from app.services.auth_service import authenticate_user

router = APIRouter()


@router.post("/login")
def login(payload: LoginRequest, db: DbSession) -> dict:
    user, token = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
            },
        },
    }


@router.post("/logout")
def logout() -> dict:
    return {"code": 0, "message": "ok", "data": {"logged_out": True}}


@router.get("/me")
def me(user=Depends(get_current_user)) -> dict:  # type: ignore[name-defined]
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "status": user.status,
        },
    }
