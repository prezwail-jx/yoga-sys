from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.audit import record_audit
from app.api.deps import CurrentUser, get_card_product_service, get_current_admin
from app.infra.db.session import get_session
from app.schemas.card_product import (
    CardProductListResponse,
    CardProductResponse,
    CreateCardProductRequest,
    UpdateCardProductRequest,
)
from app.services.card_product import CardProductService

router = APIRouter()


def state(product) -> dict:
    return CardProductResponse.model_validate(product).model_dump(mode="json", by_alias=True)


@router.post("", response_model=CardProductResponse, status_code=status.HTTP_201_CREATED)
def create_card_product(
    payload: CreateCardProductRequest,
    request: Request,
    service: CardProductService = Depends(get_card_product_service),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_admin),
):
    product = service.create_card_product(payload)
    record_audit(
        session,
        trace_id=request.state.trace_id,
        action="card_product_create",
        user=user,
        object_type="card_product",
        object_id=str(product.id),
        after_state=state(product),
    )
    return product


@router.get("", response_model=CardProductListResponse)
def list_card_products(
    enabled: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: CardProductService = Depends(get_card_product_service),
    _: CurrentUser = Depends(get_current_admin),
):
    items, total = service.list_card_products(skip, limit, enabled)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{product_id}", response_model=CardProductResponse)
def get_card_product(
    product_id: UUID,
    service: CardProductService = Depends(get_card_product_service),
    _: CurrentUser = Depends(get_current_admin),
):
    return service.get_card_product(product_id)


@router.patch("/{product_id}", response_model=CardProductResponse)
def update_card_product(
    product_id: UUID,
    payload: UpdateCardProductRequest,
    request: Request,
    service: CardProductService = Depends(get_card_product_service),
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_admin),
):
    before = state(service.get_card_product(product_id))
    product = service.update_card_product(product_id, payload)
    record_audit(
        session,
        trace_id=request.state.trace_id,
        action="card_product_update",
        user=user,
        object_type="card_product",
        object_id=str(product.id),
        before_state=before,
        after_state=state(product),
    )
    return product
