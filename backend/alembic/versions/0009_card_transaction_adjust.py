"""add card transaction adjust type

Revision ID: 0009_card_transaction_adjust
Revises: 0008_wechat_identity
"""

from alembic import op


revision = "0009_card_transaction_adjust"
down_revision = "0008_wechat_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE card_transaction_type ADD VALUE IF NOT EXISTS 'adjust'")


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM card_transaction WHERE txn_type = 'adjust') THEN
                RAISE EXCEPTION 'cannot remove card_transaction_type adjust while adjust transactions exist';
            END IF;
        END $$
    """)
    op.execute("DROP INDEX uq_card_transaction_refund_origin")
    op.execute("ALTER TYPE card_transaction_type RENAME TO card_transaction_type_with_adjust")
    op.execute("CREATE TYPE card_transaction_type AS ENUM ('purchase', 'renew', 'reissue', 'refund', 'freeze', 'unfreeze', 'extend')")
    op.execute("ALTER TABLE card_transaction ALTER COLUMN txn_type TYPE card_transaction_type USING txn_type::text::card_transaction_type")
    op.execute("DROP TYPE card_transaction_type_with_adjust")
    op.execute("CREATE UNIQUE INDEX uq_card_transaction_refund_origin ON card_transaction (origin_transaction_id) WHERE txn_type = 'refund' AND origin_transaction_id IS NOT NULL")
