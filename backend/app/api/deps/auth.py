from dataclasses import dataclass
from uuid import UUID

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
    coach_profile_id: str | None = None


def _validated_uuid_claim(value: object, detail: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail) from exc


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> CurrentUser:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    role = payload.get("role")
    user_id = payload.get("sub")
    if role not in {"admin", "coach", "member"} or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌内容无效")
    member_id = payload.get("memberId")
    if role == "member" and not member_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="会员令牌缺少 memberId")
    if role == "member":
        member_id = _validated_uuid_claim(member_id, "Member token has invalid memberId")
    coach_profile_id = payload.get("coachProfileId")
    if role == "coach" and not coach_profile_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="教练令牌缺少 coachProfileId",
        )
    if role == "coach":
        coach_profile_id = _validated_uuid_claim(
            coach_profile_id, "Coach token has invalid coachProfileId"
        )
    user = CurrentUser(
        user_id=str(user_id),
        role=str(role),
        member_id=member_id if member_id else None,
        coach_profile_id=coach_profile_id if coach_profile_id else None,
    )
    request.state.current_user = user
    return user


def require_roles(*roles: str):
    allowed = set(roles)

    def guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限")
        return user

    return guard
