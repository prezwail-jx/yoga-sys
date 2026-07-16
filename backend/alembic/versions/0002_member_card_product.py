"""0002 member card product

Revision ID: 0002_member_card_product
Revises: 0001_base_foundation
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_member_card_product"
down_revision = "0001_base_foundation"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create Enums
    sa.Enum('normal', 'paused', 'expired', 'disabled', name='member_status').create(op.get_bind())
    sa.Enum('duration', 'times', 'private', 'trial', name='card_type').create(op.get_bind())
    sa.Enum('immediate', 'first_booking', name='activation_mode').create(op.get_bind())
    sa.Enum('group', 'private', 'specific', name='course_scope').create(op.get_bind())

    # 2. Create admin_user
    op.create_table('admin_user',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )

    # 3. Create member
    op.create_table('member',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('gender', sa.String(length=16), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('birthday', sa.Date(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('join_date', sa.Date(), nullable=False),
        sa.Column('emergency_contact', sa.String(length=100), nullable=True),
        sa.Column('status', postgresql.ENUM('normal', 'paused', 'expired', 'disabled', name='member_status', create_type=False), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone')
    )
    op.create_index('ix_member_status', 'member', ['status'], unique=False)

    # 4. Create card_product
    op.create_table('card_product',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('card_type', postgresql.ENUM('duration', 'times', 'private', 'trial', name='card_type', create_type=False), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('cost_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_times', sa.Integer(), nullable=True),
        sa.Column('valid_days', sa.Integer(), nullable=True),
        sa.Column('activation_mode', postgresql.ENUM('immediate', 'first_booking', name='activation_mode', create_type=False), nullable=False),
        sa.Column('applicable_course_scope', postgresql.ENUM('group', 'private', 'specific', name='course_scope', create_type=False), nullable=False),
        sa.Column('specific_course_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('absence_deduct_enabled', sa.Boolean(), nullable=False),
        sa.Column('cancel_refund_enabled', sa.Boolean(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_card_product_enabled', 'card_product', ['enabled'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_card_product_enabled', table_name='card_product')
    op.drop_table('card_product')
    op.drop_index('ix_member_status', table_name='member')
    op.drop_table('member')
    op.drop_table('admin_user')

    sa.Enum(name='course_scope').drop(op.get_bind())
    sa.Enum(name='activation_mode').drop(op.get_bind())
    sa.Enum(name='card_type').drop(op.get_bind())
    sa.Enum(name='member_status').drop(op.get_bind())
