from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import ALGORITHM, SECRET_KEY

bearer = HTTPBearer(auto_error=True)


@dataclass(slots=True)
class CurrentUser:
    user_id: str
    role: str
    member_id: str | None = None


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> CurrentUser:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    role = payload.get("role")
    user_id = payload.get("sub")
    if role not in {"admin", "coach", "member"} or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    member_id = payload.get("memberId")
    if role == "member" and not member_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Member token is missing memberId")
    user = CurrentUser(user_id=str(user_id), role=str(role), member_id=str(member_id) if member_id else None)
    request.state.current_user = user
    return user


def require_roles(*roles: str):
    allowed = set(roles)

    def guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return guard
