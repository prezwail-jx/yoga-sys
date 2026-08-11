"""wechat identity and binding challenge

Revision ID: 0008_wechat_identity
Revises: 0007_private_training_reporting
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_wechat_identity"
down_revision = "0007_private_training_reporting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wechat_identity",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("appid", sa.String(64), nullable=False),
        sa.Column("openid_digest", sa.String(64), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bound_by_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bound_by_role", sa.String(32), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["account_id"], ["admin_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["bound_by_account_id"], ["admin_user.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("appid", "openid_digest", name="uq_wechat_identity_appid_openid"),
        sa.UniqueConstraint("appid", "account_id", name="uq_wechat_identity_appid_account"),
        sa.CheckConstraint("length(appid) > 0", name="ck_wechat_identity_appid_not_empty"),
        sa.CheckConstraint("length(openid_digest) = 64", name="ck_wechat_identity_openid_digest_length"),
        sa.CheckConstraint("bound_by_role IN ('member', 'coach')", name="ck_wechat_identity_bound_by_role"),
    )

    op.create_table(
        "wechat_binding_challenge",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ticket_digest", sa.String(64), nullable=False),
        sa.Column("appid", sa.String(64), nullable=False),
        sa.Column("openid_digest", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_digest", name="uq_wechat_binding_challenge_ticket_digest"),
        sa.CheckConstraint("length(appid) > 0", name="ck_wechat_binding_challenge_appid_not_empty"),
        sa.CheckConstraint("length(ticket_digest) = 64", name="ck_wechat_binding_challenge_ticket_digest_length"),
        sa.CheckConstraint("length(openid_digest) = 64", name="ck_wechat_binding_challenge_openid_digest_length"),
        sa.CheckConstraint("length(source_fingerprint) = 64", name="ck_wechat_binding_challenge_source_length"),
        sa.CheckConstraint("failed_attempts >= 0", name="ck_wechat_binding_challenge_failed_attempts_non_negative"),
        sa.CheckConstraint("expires_at > created_at", name="ck_wechat_binding_challenge_expiry_order"),
    )
    op.create_index("ix_wechat_binding_challenge_expires", "wechat_binding_challenge", ["expires_at"])
    op.create_index("ix_wechat_binding_challenge_appid_openid", "wechat_binding_challenge", ["appid", "openid_digest"])


def downgrade() -> None:
    op.drop_index("ix_wechat_binding_challenge_appid_openid", table_name="wechat_binding_challenge")
    op.drop_index("ix_wechat_binding_challenge_expires", table_name="wechat_binding_challenge")
    op.drop_table("wechat_binding_challenge")

    op.drop_table("wechat_identity")
