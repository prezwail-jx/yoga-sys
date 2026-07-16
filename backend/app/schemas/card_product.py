from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.base import ApiModel

CardTypeEnum = Literal["duration", "times", "private", "trial"]
ActivationModeEnum = Literal["immediate", "first_booking"]
CourseScopeEnum = Literal["group", "private", "specific"]


class CreateCardProductRequest(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    card_type: CardTypeEnum
    price: Decimal = Field(ge=0)
    cost_price: Decimal | None = Field(None, ge=0)
    total_times: int | None = Field(None, ge=1)
    valid_days: int | None = Field(None, ge=1)
    activation_mode: ActivationModeEnum
    applicable_course_scope: CourseScopeEnum
    specific_course_ids: list[str] | None = None
    absence_deduct_enabled: bool = False
    cancel_refund_enabled: bool = False

    @model_validator(mode="after")
    def validate_rules(self):
        if self.card_type == "duration" and self.valid_days is None:
            raise ValueError("duration card requires validDays")
        if self.card_type in {"times", "private"} and self.total_times is None:
            raise ValueError(f"{self.card_type} card requires totalTimes")
        if self.card_type == "trial" and self.total_times is None and self.valid_days is None:
            raise ValueError("trial card requires totalTimes or validDays")
        if self.applicable_course_scope == "specific" and not self.specific_course_ids:
            raise ValueError("specific course scope requires specificCourseIds")
        return self


class UpdateCardProductRequest(ApiModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    card_type: CardTypeEnum | None = None
    price: Decimal | None = Field(None, ge=0)
    cost_price: Decimal | None = Field(None, ge=0)
    total_times: int | None = Field(None, ge=1)
    valid_days: int | None = Field(None, ge=1)
    activation_mode: ActivationModeEnum | None = None
    applicable_course_scope: CourseScopeEnum | None = None
    specific_course_ids: list[str] | None = None
    absence_deduct_enabled: bool | None = None
    cancel_refund_enabled: bool | None = None
    enabled: bool | None = None


class CardProductResponse(ApiModel):
    id: UUID
    name: str
    card_type: CardTypeEnum
    price: Decimal
    cost_price: Decimal | None
    total_times: int | None
    valid_days: int | None
    activation_mode: ActivationModeEnum
    applicable_course_scope: CourseScopeEnum
    specific_course_ids: list[str] | None
    absence_deduct_enabled: bool
    cancel_refund_enabled: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CardProductListResponse(ApiModel):
    items: list[CardProductResponse]
    total: int
    skip: int
    limit: int
