from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from html import escape
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.orm import Session

from app.domain.card_transaction import CardTransaction
from app.domain.class_booking import ClassBooking
from app.domain.class_session import ClassSession
from app.domain.coach_profile import CoachProfile
from app.domain.course import Course
from app.domain.member import Member
from app.domain.member_card import MemberCard
from app.domain.private_training import PrivateBooking, PrivateLessonRecord


SHANGHAI = ZoneInfo("Asia/Shanghai")
MAX_EXPORT_DAYS = 180


class ReportingService:
    def __init__(self, session: Session):
        self.session = session

    def summary(self, *, date_from: date | None = None, date_to: date | None = None) -> dict:
        start, end = self._range(date_from, date_to)
        total_members = self._scalar_int(select(func.count()).select_from(Member).where(Member.deleted_at.is_(None)))
        active_members = self._scalar_int(select(func.count()).select_from(Member).where(Member.deleted_at.is_(None), Member.status == "normal"))
        today = datetime.now(SHANGHAI).date()
        expiring = self._scalar_int(
            select(func.count(func.distinct(MemberCard.member_id))).select_from(MemberCard).join(Member, Member.id == MemberCard.member_id).where(
                Member.deleted_at.is_(None), MemberCard.status == "active",
                MemberCard.expires_on >= today, MemberCard.expires_on <= today + timedelta(days=7),
            )
        )
        card_sales = self._money_sum("purchase", start, end)
        renewal_sales = self._money_sum("renew", start, end)
        refund_amount = abs(self._money_sum("refund", start, end))
        attendance_rate, full_class_rate = self._class_rates(start, end)
        private_count, private_hours, private_rate = self._private_metrics(start, end)
        return {
            "total_members": total_members,
            "active_members": active_members,
            "expiring_soon_members": expiring,
            "card_sales": card_sales,
            "renewal_sales": renewal_sales,
            "refund_amount": refund_amount,
            "attendance_rate": attendance_rate,
            "full_class_rate": full_class_rate,
            "private_lesson_count": private_count,
            "private_consumed_hours": private_hours,
            "private_completion_rate": private_rate,
        }

    def trend(self, *, category: str, date_from: date | None = None, date_to: date | None = None) -> list[dict]:
        start, end = self._range(date_from, date_to)
        if category == "revenue":
            rows = self.session.execute(
                select(
                    cast(func.date_trunc("day", CardTransaction.occurred_at), Date).label("bucket"),
                    func.coalesce(func.sum(CardTransaction.amount), 0).label("value"),
                ).where(
                    CardTransaction.txn_type.in_(("purchase", "renew")),
                    *self._between(CardTransaction.occurred_at, start, end),
                ).group_by("bucket").order_by("bucket")
            ).all()
            return [{"bucket": row.bucket, "value": row.value or Decimal("0.00")} for row in rows]
        if category == "bookings":
            rows = self.session.execute(
                select(cast(func.date_trunc("day", ClassSession.start_at), Date).label("bucket"), func.count(ClassBooking.id).label("value"))
                .select_from(ClassBooking)
                .join(ClassSession, ClassSession.id == ClassBooking.class_session_id)
                .where(*self._between(ClassSession.start_at, start, end))
                .group_by("bucket")
                .order_by("bucket")
            ).all()
            return [{"bucket": row.bucket, "value": int(row.value)} for row in rows]
        if category == "attendance":
            rows = self.session.execute(
                select(
                    cast(func.date_trunc("day", ClassSession.start_at), Date).label("bucket"),
                    func.sum(case((ClassBooking.status == "checked_in", 1), else_=0)).label("checked"),
                    func.sum(case((ClassBooking.status.in_(("checked_in", "absent")), 1), else_=0)).label("total"),
                ).select_from(ClassBooking).join(ClassSession, ClassSession.id == ClassBooking.class_session_id).where(
                    ClassSession.status == "completed", *self._between(ClassSession.start_at, start, end),
                ).group_by("bucket").order_by("bucket")
            ).all()
            return [{"bucket": row.bucket, "value": float(row.checked or 0) / float(row.total or 1)} for row in rows]
        if category == "private":
            return self._count_trend(PrivateLessonRecord.completed_at, PrivateLessonRecord.id, PrivateLessonRecord, start, end)
        raise HTTPException(status_code=422, detail="Unsupported trend category")

    def details(self, *, category: str, date_from: date | None = None, date_to: date | None = None, coach_id: UUID | None = None, course_id: UUID | None = None, card_product_id: UUID | None = None, skip: int = 0, limit: int = 50) -> tuple[list[dict], int]:
        start, end = self._range(date_from, date_to)
        if category == "expiring_members":
            today = datetime.now(SHANGHAI).date()
            stmt = select(Member, MemberCard).join(MemberCard, MemberCard.member_id == Member.id).where(
                Member.deleted_at.is_(None), MemberCard.status == "active",
                MemberCard.expires_on >= today, MemberCard.expires_on <= today + timedelta(days=7),
            )
            return self._paged(stmt, skip, limit, lambda row: {
                "memberId": str(row[0].id), "memberName": row[0].name,
                "memberCardId": str(row[1].id), "cardName": row[1].product_name,
                "remainingTimes": row[1].remaining_times, "expiresOn": row[1].expires_on.isoformat() if row[1].expires_on else None,
            })
        if category in {"transactions", "refunds"}:
            filters = self._between(CardTransaction.occurred_at, start, end)
            if category == "refunds":
                filters.append(CardTransaction.txn_type == "refund")
            else:
                filters.append(CardTransaction.txn_type.in_(("purchase", "renew", "refund")))
            if card_product_id:
                filters.append(MemberCard.card_product_id == card_product_id)
            stmt = select(CardTransaction, Member, MemberCard).join(Member, Member.id == CardTransaction.member_id).join(MemberCard, MemberCard.id == CardTransaction.member_card_id).where(*filters)
            return self._paged(stmt, skip, limit, lambda row: {
                "transactionId": str(row[0].id), "memberId": str(row[1].id), "memberName": row[1].name,
                "memberCardId": str(row[2].id), "cardName": row[2].product_name,
                "type": row[0].txn_type, "amount": str(abs(row[0].amount or Decimal("0.00")) if row[0].txn_type == "refund" else (row[0].amount or Decimal("0.00"))),
                "reason": row[0].reason, "occurredAt": row[0].occurred_at.isoformat(),
            })
        if category == "attendance":
            filters = [ClassSession.status == "completed", *self._between(ClassSession.start_at, start, end)]
            if coach_id:
                filters.append(ClassSession.coach_profile_id == coach_id)
            if course_id:
                filters.append(ClassSession.course_id == course_id)
            stmt = select(ClassBooking, ClassSession, Member, Course, CoachProfile).join(ClassSession, ClassSession.id == ClassBooking.class_session_id).join(Member, Member.id == ClassBooking.member_id).join(Course, Course.id == ClassSession.course_id).join(CoachProfile, CoachProfile.id == ClassSession.coach_profile_id).where(*filters)
            return self._paged(stmt, skip, limit, lambda row: {
                "bookingId": str(row[0].id), "sessionId": str(row[1].id), "memberId": str(row[2].id),
                "memberName": row[2].name, "courseName": row[3].name, "coachName": row[4].name,
                "status": row[0].status, "startAt": row[1].start_at.isoformat(),
            })
        if category == "private":
            filters = self._between(PrivateLessonRecord.completed_at, start, end)
            if coach_id:
                filters.append(PrivateLessonRecord.coach_profile_id == coach_id)
            stmt = select(PrivateLessonRecord, PrivateBooking, Member, CoachProfile).join(PrivateBooking, PrivateBooking.id == PrivateLessonRecord.booking_id).join(Member, Member.id == PrivateLessonRecord.member_id).join(CoachProfile, CoachProfile.id == PrivateLessonRecord.coach_profile_id).where(*filters)
            return self._paged(stmt, skip, limit, lambda row: {
                "lessonId": str(row[0].id), "bookingId": str(row[1].id), "memberId": str(row[2].id),
                "memberName": row[2].name, "coachName": row[3].name, "consumedHours": str(row[0].consumed_hours),
                "completedAt": row[0].completed_at.isoformat(), "content": row[0].content,
            })
        raise HTTPException(status_code=422, detail="Unsupported detail category")

    def export_xlsx(self, *, category: str, date_from: date | None, date_to: date | None, coach_id: UUID | None = None, course_id: UUID | None = None, card_product_id: UUID | None = None) -> bytes:
        if date_from and date_to and (date_to - date_from).days > MAX_EXPORT_DAYS:
            raise HTTPException(status_code=422, detail="Export date range cannot exceed 180 days")
        items, _ = self.details(category=category, date_from=date_from, date_to=date_to, coach_id=coach_id, course_id=course_id, card_product_id=card_product_id, skip=0, limit=10_000)
        rows = [["Report", category], ["Date From", date_from.isoformat() if date_from else ""], ["Date To", date_to.isoformat() if date_to else ""], []]
        if items:
            headers = list(items[0].keys())
            rows.append(headers)
            rows.extend([[item.get(header, "") for header in headers] for item in items])
        else:
            rows.append(["No data"])
        return self._xlsx(rows)

    def _money_sum(self, txn_type: str, start: datetime | None, end: datetime | None) -> Decimal:
        return self.session.scalar(select(func.coalesce(func.sum(CardTransaction.amount), 0)).where(CardTransaction.txn_type == txn_type, *self._between(CardTransaction.occurred_at, start, end))) or Decimal("0.00")

    def _class_rates(self, start: datetime | None, end: datetime | None) -> tuple[float, float]:
        rows = self.session.execute(
            select(
                ClassSession.id, ClassSession.capacity,
                func.sum(case((ClassBooking.status == "checked_in", 1), else_=0)).label("checked"),
                func.sum(case((ClassBooking.status.in_(("checked_in", "absent")), 1), else_=0)).label("final_count"),
            ).select_from(ClassSession).outerjoin(ClassBooking, ClassBooking.class_session_id == ClassSession.id).where(
                ClassSession.status == "completed", *self._between(ClassSession.start_at, start, end),
            ).group_by(ClassSession.id, ClassSession.capacity)
        ).all()
        checked = sum(int(row.checked or 0) for row in rows)
        final_count = sum(int(row.final_count or 0) for row in rows)
        full = sum(1 for row in rows if int(row.final_count or 0) >= row.capacity)
        return (checked / final_count if final_count else 0.0, full / len(rows) if rows else 0.0)

    def _private_metrics(self, start: datetime | None, end: datetime | None) -> tuple[int, Decimal, float]:
        completed = self._scalar_int(select(func.count()).select_from(PrivateLessonRecord).where(*self._between(PrivateLessonRecord.completed_at, start, end)))
        hours = self.session.scalar(select(func.coalesce(func.sum(PrivateLessonRecord.consumed_hours), 0)).where(*self._between(PrivateLessonRecord.completed_at, start, end))) or Decimal("0.0")
        total = self._scalar_int(select(func.count()).select_from(PrivateBooking).where(*self._between(PrivateBooking.created_at, start, end), PrivateBooking.status.in_(("confirmed", "completed"))))
        return completed, hours, completed / total if total else 0.0

    def _count_trend(self, bucket_column, id_column, model, start, end) -> list[dict]:
        rows = self.session.execute(
            select(cast(func.date_trunc("day", bucket_column), Date).label("bucket"), func.count(id_column).label("value"))
            .select_from(model).where(*self._between(bucket_column, start, end)).group_by("bucket").order_by("bucket")
        ).all()
        return [{"bucket": row.bucket, "value": int(row.value)} for row in rows]

    def _paged(self, stmt, skip: int, limit: int, mapper) -> tuple[list[dict], int]:
        subq = stmt.subquery()
        total = self.session.scalar(select(func.count()).select_from(subq)) or 0
        rows = self.session.execute(stmt.offset(skip).limit(limit)).all()
        return [mapper(row) for row in rows], int(total)

    def _range(self, date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
        start = datetime.combine(date_from, time.min, SHANGHAI).astimezone(timezone.utc) if date_from else None
        end = datetime.combine(date_to + timedelta(days=1), time.min, SHANGHAI).astimezone(timezone.utc) if date_to else None
        return start, end

    @staticmethod
    def _between(column, start: datetime | None, end: datetime | None) -> list:
        filters = []
        if start:
            filters.append(column >= start)
        if end:
            filters.append(column < end)
        return filters

    def _scalar_int(self, stmt) -> int:
        return int(self.session.scalar(stmt) or 0)

    def _xlsx(self, rows: list[list]) -> bytes:
        sheet_rows = []
        for idx, row in enumerate(rows, start=1):
            cells = []
            for col_idx, value in enumerate(row, start=1):
                ref = f"{chr(64 + col_idx)}{idx}"
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
            sheet_rows.append(f'<row r="{idx}">{"".join(cells)}</row>')
        sheet = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + "".join(sheet_rows) + "</sheetData></worksheet>"
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
            zf.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            zf.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>')
            zf.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
            zf.writestr("xl/worksheets/sheet1.xml", sheet)
        return output.getvalue()
