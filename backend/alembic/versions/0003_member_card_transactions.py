"""member card transactions

Revision ID: 0003_member_card_transactions
Revises: 0002_member_card_product
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_member_card_transactions"
down_revision = "0002_member_card_product"
branch_labels = None
depends_on = None

def upgrade() -> None:
    member_card_status = postgresql.ENUM("pending_activation", "active", "frozen", "expired", "closed", name="member_card_status")
    transaction_type = postgresql.ENUM("purchase", "renew", "reissue", "refund", "freeze", "unfreeze", "extend", name="card_transaction_type")
    member_card_status.create(op.get_bind(), checkfirst=True)
    transaction_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "member_card",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_member_card_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", postgresql.ENUM("pending_activation", "active", "frozen", "expired", "closed", name="member_card_status", create_type=False), nullable=False),
        sa.Column("product_name", sa.String(100), nullable=False),
        sa.Column("card_type", sa.String(32), nullable=False),
        sa.Column("terms_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("remaining_times", sa.Integer(), nullable=True),
        sa.Column("used_times", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_days", sa.Integer(), nullable=True),
        sa.Column("opened_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("remind_on", sa.Date(), nullable=True),
        sa.Column("frozen_from", sa.Date(), nullable=True),
        sa.Column("frozen_until", sa.Date(), nullable=True),
        sa.Column("freeze_reason", sa.String(255), nullable=True),
        sa.Column("total_frozen_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["member_id"], ["member.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["card_product_id"], ["card_product.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_member_card_id"], ["member_card.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("remaining_times IS NULL OR remaining_times >= 0", name="ck_member_card_remaining_nonnegative"),
        sa.CheckConstraint("used_times >= 0", name="ck_member_card_used_nonnegative"),
        sa.CheckConstraint("valid_days IS NULL OR valid_days >= 0", name="ck_member_card_valid_days_nonnegative"),
        sa.CheckConstraint("total_frozen_days >= 0", name="ck_member_card_frozen_days_nonnegative"),
        sa.CheckConstraint("frozen_until IS NULL OR frozen_from IS NOT NULL", name="ck_member_card_freeze_dates"),
    )
    op.create_index("ix_member_card_member_status_expiry", "member_card", ["member_id", "status", "expires_on"])
    op.create_table(
        "card_transaction",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_member_card_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("txn_type", postgresql.ENUM("purchase", "renew", "reissue", "refund", "freeze", "unfreeze", "extend", name="card_transaction_type", create_type=False), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("times_delta", sa.Integer(), nullable=True),
        sa.Column("valid_days_delta", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("operator_id", sa.String(64), nullable=False),
        sa.Column("operator_role", sa.String(32), nullable=False),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["member_id"], ["member.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["member_card_id"], ["member_card.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["origin_transaction_id"], ["card_transaction.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_member_card_id"], ["member_card.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("operator_id", "idempotency_key", name="uq_card_transaction_actor_key"),
    )
    op.create_index("ix_card_transaction_member_occurred", "card_transaction", ["member_id", sa.text("occurred_at DESC")])
    op.create_index("uq_card_transaction_refund_origin", "card_transaction", ["origin_transaction_id"], unique=True, postgresql_where=sa.text("txn_type = 'refund' AND origin_transaction_id IS NOT NULL"))

def downgrade() -> None:
    op.drop_index("uq_card_transaction_refund_origin", table_name="card_transaction")
    op.drop_index("ix_card_transaction_member_occurred", table_name="card_transaction")
    op.drop_table("card_transaction")
    op.drop_index("ix_member_card_member_status_expiry", table_name="member_card")
    op.drop_table("member_card")
    postgresql.ENUM(name="card_transaction_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="member_card_status").drop(op.get_bind(), checkfirst=True)
