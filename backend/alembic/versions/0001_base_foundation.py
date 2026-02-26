"""0001 base foundation

Revision ID: 0001_base_foundation
Revises:
Create Date: 2026-02-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_base_foundation"
down_revision = None
branch_labels = None
depends_on = None


operator_role = sa.Enum(
    "admin", "coach", "member", "system", name="operator_role", native_enum=True
)
audit_result = sa.Enum(
    "success", "rejected", "failed", name="audit_result", native_enum=True
)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    operator_role.create(op.get_bind(), checkfirst=True)
    audit_result.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("operator_id", sa.String(length=64), nullable=False),
        sa.Column("operator_role", operator_role, nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.String(length=64), nullable=False),
        sa.Column("before_state", postgresql.JSONB, nullable=True),
        sa.Column("after_state", postgresql.JSONB, nullable=True),
        sa.Column("result", audit_result, nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "idempotency_record",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope",
            "actor_id",
            "idempotency_key",
            name="uq_idempotency_scope_actor_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("idempotency_record")
    op.drop_table("audit_log")
    audit_result.drop(op.get_bind(), checkfirst=True)
    operator_role.drop(op.get_bind(), checkfirst=True)
