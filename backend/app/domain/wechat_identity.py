import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base


class WechatIdentity(Base):
    __tablename__ = "wechat_identity"
    __table_args__ = (
        UniqueConstraint("appid", "openid_digest", name="uq_wechat_identity_appid_openid"),
        UniqueConstraint("appid", "account_id", name="uq_wechat_identity_appid_account"),
        CheckConstraint("length(appid) > 0", name="ck_wechat_identity_appid_not_empty"),
        CheckConstraint("length(openid_digest) = 64", name="ck_wechat_identity_openid_digest_length"),
        CheckConstraint("bound_by_role IN ('member', 'coach')", name="ck_wechat_identity_bound_by_role"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appid: Mapped[str] = mapped_column(String(64), nullable=False)
    openid_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("admin_user.id", ondelete="RESTRICT"), nullable=False
    )
    bound_by_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("admin_user.id", ondelete="RESTRICT"), nullable=False
    )
    bound_by_role: Mapped[str] = mapped_column(String(32), nullable=False)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class WechatBindingChallenge(Base):
    __tablename__ = "wechat_binding_challenge"
    __table_args__ = (
        UniqueConstraint("ticket_digest", name="uq_wechat_binding_challenge_ticket_digest"),
        CheckConstraint("length(appid) > 0", name="ck_wechat_binding_challenge_appid_not_empty"),
        CheckConstraint("length(ticket_digest) = 64", name="ck_wechat_binding_challenge_ticket_digest_length"),
        CheckConstraint("length(openid_digest) = 64", name="ck_wechat_binding_challenge_openid_digest_length"),
        CheckConstraint("length(source_fingerprint) = 64", name="ck_wechat_binding_challenge_source_length"),
        CheckConstraint("failed_attempts >= 0", name="ck_wechat_binding_challenge_failed_attempts_non_negative"),
        CheckConstraint("expires_at > created_at", name="ck_wechat_binding_challenge_expiry_order"),
        Index("ix_wechat_binding_challenge_expires", "expires_at"),
        Index("ix_wechat_binding_challenge_appid_openid", "appid", "openid_digest"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    appid: Mapped[str] = mapped_column(String(64), nullable=False)
    openid_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
