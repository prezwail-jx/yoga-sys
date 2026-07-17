from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.writeoff_event import TERMINAL_EVENT_TYPES, WriteOffEvent

class WriteOffRepository:
    def __init__(self, session: Session):
        self.session = session

    def lock_chain(self, business_ref: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:business_ref, 0))"),
            {"business_ref": business_ref},
        )

    def get_event(self, business_ref: str, event_type: str) -> WriteOffEvent | None:
        return self.session.scalars(
            select(WriteOffEvent).where(
                WriteOffEvent.business_ref == business_ref,
                WriteOffEvent.event_type == event_type,
            )
        ).first()

    def get_reserve(self, business_ref: str, *, for_update: bool = False) -> WriteOffEvent | None:
        stmt = select(WriteOffEvent).where(
            WriteOffEvent.business_ref == business_ref,
            WriteOffEvent.event_type == "reserve_hold",
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalars(stmt).first()

    def get_terminal(self, business_ref: str) -> WriteOffEvent | None:
        return self.session.scalars(
            select(WriteOffEvent).where(
                WriteOffEvent.business_ref == business_ref,
                WriteOffEvent.event_type.in_(TERMINAL_EVENT_TYPES),
            )
        ).first()

    def create(self, event: WriteOffEvent) -> WriteOffEvent:
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event
