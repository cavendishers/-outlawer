from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginUserResponse(BaseModel):
    id: str
    username: str
    display_name: str | None = None


class CurrentUserResponse(LoginUserResponse):
    status: str


class TokenPayload(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: LoginUserResponse


class LogoutResponse(BaseModel):
    logged_out: bool = True
