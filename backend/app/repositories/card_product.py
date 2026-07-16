from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.card_product import CardProduct


class CardProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, product_id: UUID) -> CardProduct | None:
        return self.session.scalars(select(CardProduct).where(CardProduct.id == product_id)).first()

    def create(self, product: CardProduct) -> CardProduct:
        self.session.add(product)
        self.session.flush()
        self.session.refresh(product)
        return product

    def list(self, skip: int = 0, limit: int = 20, enabled: bool | None = None) -> tuple[list[CardProduct], int]:
        filters = [CardProduct.enabled == enabled] if enabled is not None else []
        items = list(
            self.session.scalars(
                select(CardProduct)
                .where(*filters)
                .order_by(CardProduct.created_at.desc())
                .offset(skip)
                .limit(limit)
            ).all()
        )
        total = self.session.scalar(select(func.count()).select_from(CardProduct).where(*filters)) or 0
        return items, total

    def update(self, product: CardProduct) -> CardProduct:
        self.session.add(product)
        self.session.flush()
        self.session.refresh(product)
        return product
