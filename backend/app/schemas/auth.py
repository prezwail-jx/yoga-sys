from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class CurrentUserResponse(BaseModel):
    username: str
    role: str
