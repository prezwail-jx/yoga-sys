from pydantic import BaseModel

from app.schemas.base import ApiModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class CurrentUserResponse(ApiModel):
    username: str
    role: str
    member_id: str | None = None
