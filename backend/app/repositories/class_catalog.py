from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.domain.class_session import ClassSession
from app.domain.coach_profile import CoachProfile
from app.domain.course import Course
from app.domain.room import Room


class _CatalogRepository:
    model = None

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, item_id: UUID, *, for_update: bool = False):
        statement = select(self.model).where(self.model.id == item_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalars(statement).first()

    def lock_name(self, name: str) -> None:
        key = f"{self.model.__tablename__}:{name.casefold()}"
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": key},
        )

    def name_exists(self, name: str, *, exclude_id: UUID | None = None) -> bool:
        statement = select(self.model.id).where(func.lower(self.model.name) == name.lower())
        if exclude_id is not None:
            statement = statement.where(self.model.id != exclude_id)
        return self.session.scalar(statement.limit(1)) is not None

    def list(
        self,
        *,
        skip: int,
        limit: int,
        keyword: str | None,
        enabled: bool | None,
    ) -> tuple[list, int]:
        filters = []
        if keyword:
            filters.append(self.model.name.ilike(f"%{keyword}%"))
        if enabled is not None:
            filters.append(self.model.enabled == enabled)
        items = list(
            self.session.scalars(
                select(self.model)
                .where(*filters)
                .order_by(self.model.name, self.model.id)
                .offset(skip)
                .limit(limit)
            ).all()
        )
        total = self.session.scalar(select(func.count()).select_from(self.model).where(*filters)) or 0
        return items, total

    def create(self, item):
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def update(self, item):
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item


class CourseRepository(_CatalogRepository):
    model = Course

    def existing_ids(self, course_ids: set[UUID]) -> set[UUID]:
        if not course_ids:
            return set()
        return set(self.session.scalars(select(Course.id).where(Course.id.in_(course_ids))).all())


class RoomRepository(_CatalogRepository):
    model = Room

    def max_future_session_capacity(self, room_id: UUID, now: datetime) -> int:
        return int(
            self.session.scalar(
                select(func.max(ClassSession.capacity)).where(
                    ClassSession.room_id == room_id,
                    ClassSession.end_at > now,
                    ClassSession.status.in_(("draft", "published", "paused")),
                )
            )
            or 0
        )


class CoachProfileRepository(_CatalogRepository):
    model = CoachProfile
