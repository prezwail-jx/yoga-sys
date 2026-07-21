from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, Uuid, cast, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from app.domain.audit_log import AuditLog
from app.domain.card_transaction import CardTransaction, TRANSACTION_TYPES
from app.domain.class_booking import ClassBooking
from app.domain.class_session import ClassSession
from app.domain.course import Course
from app.domain.member_card import MemberCard
from app.domain.member_timeline_view import MemberTimelineView
from app.domain.writeoff_event import WRITE_OFF_EVENT_TYPES, WriteOffEvent

SHANGHAI = ZoneInfo("Asia/Shanghai")
ACTION_LABELS = {
    "purchase": "购卡", "renew": "续费", "reissue": "补卡", "refund": "退款",
    "freeze": "冻结", "unfreeze": "解冻", "extend": "延期",
    "reserve_hold": "预约预扣", "checkin_commit": "签到实扣",
    "cancel_refund": "取消预约", "absence_commit": "缺勤处理",
}

class MemberTimelineService:
    def __init__(self, session: Session):
        self.session = session

    def query(self, *, member_id: UUID, actor_role: str, category: str = "all",
              action: str | None = None, date_from: date | None = None,
              date_to: date | None = None, business_ref: str | None = None,
              skip: int = 0, limit: int = 50) -> tuple[list[MemberTimelineView], int]:
        start = self._day_start(date_from) if date_from else None
        end = self._day_start(date_to + timedelta(days=1)) if date_to else None
        statements = []
        if category in {"all", "transaction"} and not business_ref:
            filters = [CardTransaction.member_id == member_id]
            self._time_filters(filters, CardTransaction.occurred_at, start, end)
            if action:
                filters.append(CardTransaction.txn_type == action)
            statements.append(select(
                CardTransaction.id.label("id"), literal("transaction").label("source"),
                cast(CardTransaction.txn_type, String).label("action"), literal("success").label("result"),
                CardTransaction.occurred_at.label("occurred_at"), CardTransaction.trace_id.label("trace_id"),
                CardTransaction.member_card_id.label("member_card_id"), cast(literal(None), String).label("business_ref"),
                cast(literal(None), Integer).label("sequence_no"), CardTransaction.times_delta.label("times_delta"),
                CardTransaction.amount.label("amount"), MemberCard.product_name.label("product_name"),
                MemberCard.card_type.label("card_type"), CardTransaction.valid_days_delta.label("valid_days_delta"),
                CardTransaction.reason.label("reason"), CardTransaction.operator_id.label("operator_id"),
                CardTransaction.operator_role.label("operator_role"), literal("member_card").label("object_type"),
                cast(CardTransaction.member_card_id, String).label("object_id"), literal(2).label("source_priority"),
                cast(literal(None), String).label("booking_course_name"),
            ).join(MemberCard, MemberCard.id == CardTransaction.member_card_id).where(*filters))
        if category in {"all", "writeoff"}:
            filters = [WriteOffEvent.member_id == member_id]
            self._time_filters(filters, WriteOffEvent.occurred_at, start, end)
            if action:
                filters.append(WriteOffEvent.event_type == action)
            if business_ref:
                filters.append(WriteOffEvent.business_ref == business_ref)
            statements.append(select(
                WriteOffEvent.id.label("id"), literal("writeoff").label("source"),
                cast(WriteOffEvent.event_type, String).label("action"), literal("success").label("result"),
                WriteOffEvent.occurred_at.label("occurred_at"), WriteOffEvent.trace_id.label("trace_id"),
                WriteOffEvent.member_card_id.label("member_card_id"), WriteOffEvent.business_ref.label("business_ref"),
                WriteOffEvent.sequence_no.label("sequence_no"), WriteOffEvent.times_delta.label("times_delta"),
                cast(literal(None), Numeric(12, 2)).label("amount"), cast(literal(None), String).label("product_name"),
                cast(literal(None), String).label("card_type"), cast(literal(None), Integer).label("valid_days_delta"),
                cast(literal(None), String).label("reason"), WriteOffEvent.operator_id.label("operator_id"),
                WriteOffEvent.operator_role.label("operator_role"), literal("writeoff_event").label("object_type"),
                cast(WriteOffEvent.id, String).label("object_id"), literal(1).label("source_priority"),
                Course.name.label("booking_course_name"),
            ).outerjoin(
                ClassBooking, cast(ClassBooking.id, String) == WriteOffEvent.business_ref
            ).outerjoin(
                ClassSession, ClassSession.id == ClassBooking.class_session_id
            ).outerjoin(Course, Course.id == ClassSession.course_id).where(*filters))
        if actor_role == "admin" and category in {"all", "audit"} and not business_ref:
            filters = [
                AuditLog.member_id == member_id,
                or_(AuditLog.result != "success", AuditLog.action.notin_(TRANSACTION_TYPES + WRITE_OFF_EVENT_TYPES)),
            ]
            self._time_filters(filters, AuditLog.occurred_at, start, end)
            if action:
                filters.append(AuditLog.action == action)
            statements.append(select(
                AuditLog.id.label("id"), literal("audit").label("source"), AuditLog.action.label("action"),
                cast(AuditLog.result, String).label("result"), AuditLog.occurred_at.label("occurred_at"),
                AuditLog.trace_id.label("trace_id"), cast(literal(None), Uuid).label("member_card_id"),
                cast(literal(None), String).label("business_ref"), cast(literal(None), Integer).label("sequence_no"),
                cast(literal(None), Integer).label("times_delta"), cast(literal(None), Numeric(12, 2)).label("amount"),
                cast(literal(None), String).label("product_name"), cast(literal(None), String).label("card_type"),
                cast(literal(None), Integer).label("valid_days_delta"), AuditLog.reason.label("reason"),
                AuditLog.operator_id.label("operator_id"), cast(AuditLog.operator_role, String).label("operator_role"),
                AuditLog.object_type.label("object_type"), AuditLog.object_id.label("object_id"),
                literal(3).label("source_priority"),
                cast(literal(None), String).label("booking_course_name"),
            ).where(*filters))
        if not statements:
            return [], 0
        combined = union_all(*statements).subquery()
        total = self.session.scalar(select(func.count()).select_from(combined)) or 0
        rows = self.session.execute(
            select(combined).order_by(
                combined.c.occurred_at.desc(), combined.c.sequence_no.desc().nullslast(),
                combined.c.source_priority.asc(), combined.c.id.desc(),
            ).offset(skip).limit(limit)
        ).mappings().all()
        items = []
        for row in rows:
            operator_id = row["operator_id"] if actor_role == "admin" else None
            items.append(MemberTimelineView(
                id=row["id"], source=row["source"], action=row["action"], result=row["result"],
                occurred_at=row["occurred_at"], trace_id=row["trace_id"],
                member_card_id=row["member_card_id"], business_ref=row["business_ref"],
                sequence_no=row["sequence_no"], times_delta=row["times_delta"], amount=row["amount"],
                product_name=row["product_name"], card_type=row["card_type"],
                valid_days_delta=row["valid_days_delta"], reason=row["reason"],
                operator_id=operator_id, operator_role=row["operator_role"] if actor_role == "admin" else None,
                object_type=row["object_type"] if actor_role == "admin" else None,
                object_id=row["object_id"] if actor_role == "admin" else None,
                summary=self._summary(row["action"], row["booking_course_name"]),
            ))
        return items, int(total)

    @staticmethod
    def _day_start(value: date) -> datetime:
        return datetime.combine(value, time.min, SHANGHAI).astimezone(timezone.utc)

    @staticmethod
    def _time_filters(filters: list, column, start: datetime | None, end: datetime | None) -> None:
        if start:
            filters.append(column >= start)
        if end:
            filters.append(column < end)

    @staticmethod
    def _summary(action: str, course_name: str | None) -> str:
        label = ACTION_LABELS.get(action, action)
        return f"{label} · {course_name}" if course_name else label
