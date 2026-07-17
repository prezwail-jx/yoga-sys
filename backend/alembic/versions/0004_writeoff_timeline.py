"""write-off events and timeline indexes

Revision ID: 0004_writeoff_timeline
Revises: 0003_member_card_transactions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_writeoff_timeline"
down_revision = "0003_member_card_transactions"
branch_labels = None
depends_on = None

def upgrade() -> None:
    event_type = postgresql.ENUM("reserve_hold", "checkin_commit", "cancel_refund", "absence_commit", name="writeoff_event_type")
    event_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "writeoff_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", postgresql.ENUM("reserve_hold", "checkin_commit", "cancel_refund", "absence_commit", name="writeoff_event_type", create_type=False), nullable=False),
        sa.Column("business_ref", sa.String(128), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("times_delta", sa.Integer(), server_default="0", nullable=False),
        sa.Column("selection_basis", sa.String(255), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("operator_id", sa.String(64), nullable=False),
        sa.Column("operator_role", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["member_id"], ["member.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["member_card_id"], ["member_card.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["previous_event_id"], ["writeoff_event.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("business_ref", "event_type", name="uq_writeoff_business_event"),
        sa.CheckConstraint("sequence_no IN (1, 2)", name="ck_writeoff_sequence"),
        sa.CheckConstraint("(event_type = 'reserve_hold' AND sequence_no = 1 AND previous_event_id IS NULL) OR (event_type <> 'reserve_hold' AND sequence_no = 2 AND previous_event_id IS NOT NULL)", name="ck_writeoff_lifecycle_shape"),
    )
    op.create_index("ix_writeoff_member_occurred", "writeoff_event", ["member_id", sa.text("occurred_at DESC")])
    op.create_index("ix_writeoff_business_ref", "writeoff_event", ["business_ref"])
    op.create_index("uq_writeoff_single_terminal", "writeoff_event", ["business_ref"], unique=True, postgresql_where=sa.text("event_type IN ('checkin_commit', 'cancel_refund', 'absence_commit')"))
    op.create_index("ix_audit_member_occurred", "audit_log", ["member_id", sa.text("occurred_at DESC")])

def downgrade() -> None:
    op.drop_index("ix_audit_member_occurred", table_name="audit_log")
    op.drop_index("uq_writeoff_single_terminal", table_name="writeoff_event")
    op.drop_index("ix_writeoff_business_ref", table_name="writeoff_event")
    op.drop_index("ix_writeoff_member_occurred", table_name="writeoff_event")
    op.drop_table("writeoff_event")
    postgresql.ENUM(name="writeoff_event_type").drop(op.get_bind(), checkfirst=True)
