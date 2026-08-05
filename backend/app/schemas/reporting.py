from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from app.schemas.base import ApiModel


ReportTrendCategory = Literal["revenue", "bookings", "attendance", "private"]
ReportDetailCategory = Literal["expiring_members", "transactions", "refunds", "attendance", "private"]


class ReportSummaryResponse(ApiModel):
    total_members: int
    active_members: int
    expiring_soon_members: int
    card_sales: Decimal
    renewal_sales: Decimal
    refund_amount: Decimal
    attendance_rate: float
    full_class_rate: float
    private_lesson_count: int
    private_consumed_hours: Decimal
    private_completion_rate: float


class ReportTrendPoint(ApiModel):
    bucket: date
    value: Decimal | float | int


class ReportTrendResponse(ApiModel):
    category: ReportTrendCategory
    points: list[ReportTrendPoint]


class ReportDetailResponse(ApiModel):
    category: ReportDetailCategory
    items: list[dict]
    total: int
    skip: int
    limit: int


class ReportFilterMeta(ApiModel):
    date_from: date | None = None
    date_to: date | None = None
    coach_id: UUID | None = None
    course_id: UUID | None = None
    card_product_id: UUID | None = None
