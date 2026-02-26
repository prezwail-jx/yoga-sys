from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

bearer = HTTPBearer(auto_error=True)


@dataclass(slots=True)
class CurrentUser:
    user_id: str
    role: str
    member_id: str | None = None
    coach_profile_id: str | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    role = payload.get("role")
    user_id = payload.get("sub")
    if not role or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    return CurrentUser(
        user_id=str(user_id),
        role=str(role),
        member_id=payload.get("member_id"),
        coach_profile_id=payload.get("coach_profile_id"),
    )


def require_roles(*roles: str):
    allowed = set(roles)

    def _guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )
        return user

    return _guard


def require_any_role(roles: Iterable[str]):
    return require_roles(*tuple(roles))
