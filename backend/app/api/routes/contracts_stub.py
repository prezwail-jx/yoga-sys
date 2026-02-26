from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response

from app.api.deps.auth import CurrentUser, get_current_user


router = APIRouter()


@router.post("/members", tags=["Members"])
def create_member(_: CurrentUser = Depends(get_current_user)) -> dict:
    return {"message": "not implemented"}


@router.patch("/members/{memberId}", tags=["Members"])
def update_member(memberId: str, _: CurrentUser = Depends(get_current_user)) -> dict:
    return {"memberId": memberId, "message": "not implemented"}


@router.delete("/members/{memberId}", tags=["Members"], status_code=204)
def delete_member(
    memberId: str, _: CurrentUser = Depends(get_current_user)
) -> Response:
    return Response(status_code=204)


@router.get("/members/{memberId}/timeline", tags=["Audit"])
def member_timeline(memberId: str, _: CurrentUser = Depends(get_current_user)) -> dict:
    return {"items": [], "memberId": memberId}


@router.post("/card-products", tags=["CardProducts"])
def create_card_product(_: CurrentUser = Depends(get_current_user)) -> dict:
    return {"message": "not implemented"}


@router.post("/member-cards/{memberCardId}/freeze", tags=["MemberCards"])
def freeze_member_card(
    memberCardId: str, _: CurrentUser = Depends(get_current_user)
) -> dict:
    return {"memberCardId": memberCardId, "message": "not implemented"}


@router.post("/member-cards/{memberCardId}/unfreeze", tags=["MemberCards"])
def unfreeze_member_card(
    memberCardId: str, _: CurrentUser = Depends(get_current_user)
) -> dict:
    return {"memberCardId": memberCardId, "message": "not implemented"}


@router.post("/transactions", tags=["Transactions"])
def create_transaction(
    _: CurrentUser = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> dict:
    return {"idempotencyKey": idempotency_key, "message": "not implemented"}


@router.post("/writeoff/events", tags=["WriteOff"])
def apply_writeoff_event(
    _: CurrentUser = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> dict:
    return {"idempotencyKey": idempotency_key, "message": "not implemented"}
