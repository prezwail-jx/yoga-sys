from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import get_current_admin, get_reporting_service
from app.schemas.reporting import ReportDetailResponse, ReportSummaryResponse, ReportTrendResponse
from app.services.reporting import ReportingService


router = APIRouter(prefix="/reports")


@router.get("/summary", response_model=ReportSummaryResponse)
def report_summary(
    date_from: date | None = Query(None, alias="dateFrom"),
    date_to: date | None = Query(None, alias="dateTo"),
    service: ReportingService = Depends(get_reporting_service),
    _=Depends(get_current_admin),
):
    return service.summary(date_from=date_from, date_to=date_to)


@router.get("/trends", response_model=ReportTrendResponse)
def report_trends(
    category: str = Query(...),
    date_from: date | None = Query(None, alias="dateFrom"),
    date_to: date | None = Query(None, alias="dateTo"),
    service: ReportingService = Depends(get_reporting_service),
    _=Depends(get_current_admin),
):
    return {"category": category, "points": service.trend(category=category, date_from=date_from, date_to=date_to)}


@router.get("/details/{category}", response_model=ReportDetailResponse)
def report_details(
    category: str,
    date_from: date | None = Query(None, alias="dateFrom"),
    date_to: date | None = Query(None, alias="dateTo"),
    coach_id: UUID | None = Query(None, alias="coachId"),
    course_id: UUID | None = Query(None, alias="courseId"),
    card_product_id: UUID | None = Query(None, alias="cardProductId"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: ReportingService = Depends(get_reporting_service),
    _=Depends(get_current_admin),
):
    items, total = service.details(
        category=category, date_from=date_from, date_to=date_to,
        coach_id=coach_id, course_id=course_id, card_product_id=card_product_id,
        skip=skip, limit=limit,
    )
    return {"category": category, "items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/export")
def report_export(
    category: str = Query(...),
    date_from: date | None = Query(None, alias="dateFrom"),
    date_to: date | None = Query(None, alias="dateTo"),
    coach_id: UUID | None = Query(None, alias="coachId"),
    course_id: UUID | None = Query(None, alias="courseId"),
    card_product_id: UUID | None = Query(None, alias="cardProductId"),
    service: ReportingService = Depends(get_reporting_service),
    _=Depends(get_current_admin),
):
    content = service.export_xlsx(
        category=category, date_from=date_from, date_to=date_to,
        coach_id=coach_id, course_id=course_id, card_product_id=card_product_id,
    )
    filename = f"report-{category}.xlsx"
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
