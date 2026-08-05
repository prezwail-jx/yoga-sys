"""private training and reporting indexes

Revision ID: 0007_private_training_reporting
Revises: 0006_group_class_booking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_private_training_reporting"
down_revision = "0006_group_class_booking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    private_availability_status = postgresql.ENUM(
        "available", "locked", "cancelled", name="private_availability_status"
    )
    private_booking_status = postgresql.ENUM(
        "pending", "confirmed", "rejected", "cancelled", "completed",
        name="private_booking_status",
    )
    private_availability_status.create(op.get_bind(), checkfirst=True)
    private_booking_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "private_availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("coach_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("available", "locked", "cancelled", name="private_availability_status", create_type=False),
            server_default="available", nullable=False,
        ),
        sa.Column("created_by_id", sa.String(64), nullable=False),
        sa.Column("created_by_role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["coach_profile_id"], ["coach_profile.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("end_at > start_at", name="ck_private_availability_time_order"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_private_availability_duration_positive"),
    )
    op.create_index("ix_private_availability_coach_time", "private_availability", ["coach_profile_id", "start_at", "end_at"])
    op.create_index("ix_private_availability_status_time", "private_availability", ["status", "start_at"])

    op.create_table(
        "private_booking",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("availability_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coach_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_card_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "confirmed", "rejected", "cancelled", "completed",
                name="private_booking_status", create_type=False,
            ),
            server_default="pending", nullable=False,
        ),
        sa.Column("member_message", sa.String(500), nullable=True),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column("cancellation_reason", sa.String(255), nullable=True),
        sa.Column("booked_by_id", sa.String(64), nullable=False),
        sa.Column("booked_by_role", sa.String(32), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminal_by_id", sa.String(64), nullable=True),
        sa.Column("terminal_by_role", sa.String(32), nullable=True),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["availability_id"], ["private_availability.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["member_id"], ["member.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["coach_profile_id"], ["coach_profile.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["member_card_id"], ["member_card.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "(status IN ('pending', 'confirmed') AND terminal_by_id IS NULL AND terminal_by_role IS NULL AND terminal_at IS NULL) "
            "OR (status IN ('rejected', 'cancelled', 'completed') AND terminal_by_id IS NOT NULL AND terminal_by_role IS NOT NULL AND terminal_at IS NOT NULL)",
            name="ck_private_booking_terminal_shape",
        ),
        sa.CheckConstraint("status NOT IN ('confirmed', 'completed') OR member_card_id IS NOT NULL", name="ck_private_booking_confirmed_card"),
        sa.CheckConstraint("status = 'rejected' OR rejection_reason IS NULL", name="ck_private_booking_rejection_reason"),
        sa.CheckConstraint("status = 'cancelled' OR cancellation_reason IS NULL", name="ck_private_booking_cancellation_reason"),
    )
    op.create_index("ix_private_booking_slot_status", "private_booking", ["availability_id", "status"])
    op.create_index("ix_private_booking_member_status", "private_booking", ["member_id", "status"])
    op.create_index("ix_private_booking_coach_status", "private_booking", ["coach_profile_id", "status"])
    op.create_index(
        "uq_private_booking_active_slot", "private_booking", ["availability_id"], unique=True,
        postgresql_where=sa.text("status IN ('pending', 'confirmed')"),
    )

    op.create_table(
        "private_lesson_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coach_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("consumed_hours", sa.Numeric(4, 1), nullable=False),
        sa.Column("member_status_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("created_by_id", sa.String(64), nullable=False),
        sa.Column("created_by_role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["booking_id"], ["private_booking.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["member_id"], ["member.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["coach_profile_id"], ["coach_profile.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("booking_id", name="uq_private_lesson_record_booking"),
        sa.CheckConstraint("consumed_hours > 0", name="ck_private_lesson_consumed_hours_positive"),
    )
    op.create_index("ix_private_lesson_member_completed", "private_lesson_record", ["member_id", "completed_at"])
    op.create_index("ix_private_lesson_coach_completed", "private_lesson_record", ["coach_profile_id", "completed_at"])

    op.create_index("ix_card_transaction_type_occurred", "card_transaction", ["txn_type", "occurred_at"])
    op.create_index(
        "ix_member_card_active_expires", "member_card", ["expires_on"],
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_member_card_active_expires", table_name="member_card")
    op.drop_index("ix_card_transaction_type_occurred", table_name="card_transaction")

    op.drop_index("ix_private_lesson_coach_completed", table_name="private_lesson_record")
    op.drop_index("ix_private_lesson_member_completed", table_name="private_lesson_record")
    op.drop_table("private_lesson_record")

    op.drop_index("uq_private_booking_active_slot", table_name="private_booking")
    op.drop_index("ix_private_booking_coach_status", table_name="private_booking")
    op.drop_index("ix_private_booking_member_status", table_name="private_booking")
    op.drop_index("ix_private_booking_slot_status", table_name="private_booking")
    op.drop_table("private_booking")

    op.drop_index("ix_private_availability_status_time", table_name="private_availability")
    op.drop_index("ix_private_availability_coach_time", table_name="private_availability")
    op.drop_table("private_availability")

    postgresql.ENUM(name="private_booking_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="private_availability_status").drop(op.get_bind(), checkfirst=True)
