from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPayload(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
