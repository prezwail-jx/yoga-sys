from __future__ import annotations

from fastapi import HTTPException, status

from app.api.deps.auth import CurrentUser


class AccessPolicyService:
    def assert_member_readable(self, actor: CurrentUser, member_id: str) -> None:
        if actor.role == "admin":
            return
        if actor.role == "member" and actor.member_id == member_id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    def assert_member_writable(self, actor: CurrentUser, member_id: str) -> None:
        if actor.role == "admin":
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    def assert_card_product_writable(self, actor: CurrentUser) -> None:
        if actor.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )

    def assert_cross_member_query_allowed(self, actor: CurrentUser) -> None:
        if actor.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )
