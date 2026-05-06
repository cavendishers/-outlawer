from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_user
from app.domains.auth import authenticate_user
from app.schemas.auth import CurrentUserResponse, LoginRequest, LogoutResponse, TokenPayload
from app.schemas.common import Envelope

router = APIRouter()


@router.post("/login", response_model=Envelope[TokenPayload])
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


@router.post("/logout", response_model=Envelope[LogoutResponse])
def logout() -> dict:
    return {"code": 0, "message": "ok", "data": {"logged_out": True}}


@router.get("/me", response_model=Envelope[CurrentUserResponse])
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
