"""Phase 6 PostgreSQL performance indexes and constraints.

Revision ID: 0005_perf_indexes
Revises: 0004_writeoff_timeline
"""
from alembic import op

revision = "0005_perf_indexes"
down_revision = "0004_writeoff_timeline"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX ix_member_name_trgm ON member USING gin (name gin_trgm_ops)")
    op.execute("CREATE INDEX ix_member_phone_trgm ON member USING gin (phone gin_trgm_ops)")
    op.execute("CREATE INDEX ix_member_live_created ON member (created_at DESC) WHERE deleted_at IS NULL")
    op.execute("CREATE INDEX ix_member_live_status_created ON member (status, created_at DESC) WHERE deleted_at IS NULL")
    op.execute("CREATE INDEX ix_card_product_enabled_created ON card_product (enabled, created_at DESC)")
    op.execute("""CREATE INDEX ix_member_card_fefo ON member_card
        (member_id, status, expires_on, opened_on, created_at)
        WHERE status IN ('active', 'pending_activation')
          AND (remaining_times IS NULL OR remaining_times > 0)""")
    op.execute("CREATE INDEX ix_idempotency_expires_at ON idempotency_record (expires_at)")
    op.execute("DROP INDEX IF EXISTS ix_writeoff_business_ref")
    op.execute("ALTER TABLE idempotency_record ADD CONSTRAINT ck_idempotency_response_code CHECK (response_code BETWEEN 100 AND 599)")
    op.execute("ALTER TABLE idempotency_record ADD CONSTRAINT ck_idempotency_expiry CHECK (expires_at > created_at)")
    op.execute("ALTER TABLE writeoff_event ADD CONSTRAINT ck_writeoff_times_delta CHECK (times_delta BETWEEN -1 AND 1)")

def downgrade() -> None:
    op.execute("ALTER TABLE writeoff_event DROP CONSTRAINT IF EXISTS ck_writeoff_times_delta")
    op.execute("ALTER TABLE idempotency_record DROP CONSTRAINT IF EXISTS ck_idempotency_expiry")
    op.execute("ALTER TABLE idempotency_record DROP CONSTRAINT IF EXISTS ck_idempotency_response_code")
    op.execute("CREATE INDEX IF NOT EXISTS ix_writeoff_business_ref ON writeoff_event (business_ref)")
    for index in (
        "ix_idempotency_expires_at", "ix_member_card_fefo",
        "ix_card_product_enabled_created", "ix_member_live_status_created",
        "ix_member_live_created", "ix_member_phone_trgm", "ix_member_name_trgm",
    ):
        op.execute(f"DROP INDEX IF EXISTS {index}")
