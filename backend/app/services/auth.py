from fastapi import HTTPException, status
from app.schemas.auth import LoginRequest, LoginResponse
from app.repositories.admin_user import AdminUserRepository
from app.core.security import verify_password, create_access_token
from datetime import timedelta
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES

class AuthService:
    def __init__(self, admin_user_repo: AdminUserRepository):
        self.admin_user_repo = admin_user_repo

    def login(self, request: LoginRequest) -> LoginResponse:
        user = self.admin_user_repo.get_by_username(request.username)
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
        )
        return LoginResponse(access_token=access_token, role=user.role)
