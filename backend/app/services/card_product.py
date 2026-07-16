from uuid import UUID

from fastapi import HTTPException, status

from app.domain.card_product import CardProduct
from app.repositories.card_product import CardProductRepository
from app.schemas.card_product import CreateCardProductRequest, UpdateCardProductRequest

_RULE_FIELDS = (
    "name",
    "card_type",
    "price",
    "cost_price",
    "total_times",
    "valid_days",
    "activation_mode",
    "applicable_course_scope",
    "specific_course_ids",
    "absence_deduct_enabled",
    "cancel_refund_enabled",
)


class CardProductService:
    def __init__(self, card_product_repo: CardProductRepository):
        self.card_product_repo = card_product_repo

    def create_card_product(self, req: CreateCardProductRequest) -> CardProduct:
        return self.card_product_repo.create(CardProduct(**req.model_dump(), enabled=True))

    def get_card_product(self, product_id: UUID) -> CardProduct:
        product = self.card_product_repo.get_by_id(product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card product not found")
        return product

    def list_card_products(self, skip: int = 0, limit: int = 20, enabled: bool | None = None) -> tuple[list[CardProduct], int]:
        return self.card_product_repo.list(skip, limit, enabled)

    def update_card_product(self, product_id: UUID, req: UpdateCardProductRequest) -> CardProduct:
        product = self.get_card_product(product_id)
        changes = req.model_dump(exclude_unset=True)
        merged = {field: changes.get(field, getattr(product, field)) for field in _RULE_FIELDS}
        CreateCardProductRequest.model_validate(merged)
        for field, value in changes.items():
            setattr(product, field, value)
        return self.card_product_repo.update(product)
