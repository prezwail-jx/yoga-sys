"""group class catalog, scheduling, booking, and account bindings

Revision ID: 0006_group_class_booking
Revises: 0005_perf_indexes
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_group_class_booking"
down_revision = "0005_perf_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    course_difficulty = postgresql.ENUM(
        "all_levels", "beginner", "intermediate", "advanced",
        name="course_difficulty",
    )
    class_session_status = postgresql.ENUM(
        "draft", "published", "paused", "cancelled", "completed",
        name="class_session_status",
    )
    class_booking_status = postgresql.ENUM(
        "reserved", "checked_in", "cancelled", "absent",
        name="class_booking_status",
    )
    course_difficulty.create(op.get_bind(), checkfirst=True)
    class_session_status.create(op.get_bind(), checkfirst=True)
    class_booking_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "course",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "difficulty",
            postgresql.ENUM(
                "all_levels", "beginner", "intermediate", "advanced",
                name="course_difficulty", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.String(512), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_course_duration_positive"),
    )
    op.create_index("uq_course_name_lower", "course", [sa.text("lower(name)")], unique=True)
    op.create_index("ix_course_enabled_name", "course", ["enabled", "name"])

    op.create_table(
        "room",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("capacity > 0", name="ck_room_capacity_positive"),
    )
    op.create_index("uq_room_name_lower", "room", [sa.text("lower(name)")], unique=True)
    op.create_index("ix_room_enabled_name", "room", ["enabled", "name"])

    op.create_table(
        "coach_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("specialty_course_ids", postgresql.JSONB(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coach_profile_enabled_name", "coach_profile", ["enabled", "name"])

    op.add_column("admin_user", sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("admin_user", sa.Column("coach_profile_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_admin_user_member_id", "admin_user", "member", ["member_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_admin_user_coach_profile_id", "admin_user", "coach_profile",
        ["coach_profile_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_admin_user_member_id", "admin_user", ["member_id"])
    op.create_unique_constraint("uq_admin_user_coach_profile_id", "admin_user", ["coach_profile_id"])

    op.create_table(
        "class_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coach_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("booking_open_hours_before", sa.Integer(), server_default="168", nullable=False),
        sa.Column("booking_close_minutes_before", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cancel_cutoff_minutes_before", sa.Integer(), server_default="120", nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft", "published", "paused", "cancelled", "completed",
                name="class_session_status", create_type=False,
            ),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("source_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["course_id"], ["course.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["coach_profile_id"], ["coach_profile.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["room.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_session_id"], ["class_session.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("end_at > start_at", name="ck_class_session_time_order"),
        sa.CheckConstraint("capacity > 0", name="ck_class_session_capacity_positive"),
        sa.CheckConstraint("booking_open_hours_before >= 0", name="ck_class_session_booking_open_nonnegative"),
        sa.CheckConstraint("booking_close_minutes_before >= 0", name="ck_class_session_booking_close_nonnegative"),
        sa.CheckConstraint("cancel_cutoff_minutes_before >= 0", name="ck_class_session_cancel_cutoff_nonnegative"),
    )
    op.create_index("ix_class_session_start_status", "class_session", ["start_at", "status"])
    op.create_index(
        "ix_class_session_coach_time", "class_session",
        ["coach_profile_id", "start_at", "end_at"],
        postgresql_where=sa.text("status IN ('draft', 'published', 'paused')"),
    )
    op.create_index(
        "ix_class_session_room_time", "class_session", ["room_id", "start_at", "end_at"],
        postgresql_where=sa.text("status IN ('draft', 'published', 'paused')"),
    )

    op.create_table(
        "class_booking",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("class_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "reserved", "checked_in", "cancelled", "absent",
                name="class_booking_status", create_type=False,
            ),
            server_default="reserved",
            nullable=False,
        ),
        sa.Column("booked_by_id", sa.String(64), nullable=False),
        sa.Column("booked_by_role", sa.String(32), nullable=False),
        sa.Column("booked_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("terminal_by_id", sa.String(64), nullable=True),
        sa.Column("terminal_by_role", sa.String(32), nullable=True),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(255), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["class_session_id"], ["class_session.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["member_id"], ["member.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "(status = 'reserved' AND terminal_by_id IS NULL AND terminal_by_role IS NULL AND terminal_at IS NULL) "
            "OR (status <> 'reserved' AND terminal_by_id IS NOT NULL AND terminal_by_role IS NOT NULL AND terminal_at IS NOT NULL)",
            name="ck_class_booking_terminal_shape",
        ),
        sa.CheckConstraint(
            "status = 'cancelled' OR cancellation_reason IS NULL",
            name="ck_class_booking_cancellation_reason",
        ),
    )
    op.create_index("ix_class_booking_session_status", "class_booking", ["class_session_id", "status"])
    op.create_index("ix_class_booking_member_status", "class_booking", ["member_id", "status"])
    op.create_index(
        "ix_class_booking_member_created", "class_booking",
        ["member_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "uq_class_booking_active_member_session", "class_booking",
        ["class_session_id", "member_id"], unique=True,
        postgresql_where=sa.text("status = 'reserved'"),
    )


def downgrade() -> None:
    op.drop_index("uq_class_booking_active_member_session", table_name="class_booking")
    op.drop_index("ix_class_booking_member_created", table_name="class_booking")
    op.drop_index("ix_class_booking_member_status", table_name="class_booking")
    op.drop_index("ix_class_booking_session_status", table_name="class_booking")
    op.drop_table("class_booking")

    op.drop_index("ix_class_session_room_time", table_name="class_session")
    op.drop_index("ix_class_session_coach_time", table_name="class_session")
    op.drop_index("ix_class_session_start_status", table_name="class_session")
    op.drop_table("class_session")

    op.drop_constraint("uq_admin_user_coach_profile_id", "admin_user", type_="unique")
    op.drop_constraint("uq_admin_user_member_id", "admin_user", type_="unique")
    op.drop_constraint("fk_admin_user_coach_profile_id", "admin_user", type_="foreignkey")
    op.drop_constraint("fk_admin_user_member_id", "admin_user", type_="foreignkey")
    op.drop_column("admin_user", "coach_profile_id")
    op.drop_column("admin_user", "member_id")

    op.drop_index("ix_coach_profile_enabled_name", table_name="coach_profile")
    op.drop_table("coach_profile")
    op.drop_index("ix_room_enabled_name", table_name="room")
    op.drop_index("uq_room_name_lower", table_name="room")
    op.drop_table("room")
    op.drop_index("ix_course_enabled_name", table_name="course")
    op.drop_index("uq_course_name_lower", table_name="course")
    op.drop_table("course")

    postgresql.ENUM(name="class_booking_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="class_session_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="course_difficulty").drop(op.get_bind(), checkfirst=True)
