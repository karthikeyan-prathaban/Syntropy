"""initial

Revision ID: 001
Revises:
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120)),
        sa.Column("mobile_enc", sa.String(255)),
        sa.Column("email_enc", sa.String(255)),
        sa.Column("vua_enc", sa.String(255)),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("avatar_initials", sa.String(8), nullable=True),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "consent_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("request_id", sa.String(120), unique=True),
        sa.Column("consent_id", sa.String(120), nullable=True),
        sa.Column("status", sa.String(40)),
        sa.Column("consent_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("linked_acc_ref", sa.String(120)),
        sa.Column("masked_acc_number", sa.String(40)),
        sa.Column("account_type", sa.String(40)),
        sa.Column("current_balance", sa.Float()),
        sa.Column("currency", sa.String(8)),
        sa.Column("fip_id", sa.String(80), nullable=True),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id")),
        sa.Column("txn_id", sa.String(120)),
        sa.Column("amount", sa.Float()),
        sa.Column("txn_type", sa.String(12)),
        sa.Column("narration", sa.Text()),
        sa.Column("mode", sa.String(40)),
        sa.Column("category", sa.String(80)),
        sa.Column("transaction_timestamp", sa.DateTime()),
        sa.Column("balance_after", sa.Float(), nullable=True),
    )
    op.create_table(
        "waitlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True),
        sa.Column("source", sa.String(80), nullable=True),
        sa.Column("utm", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table("waitlist")
    op.drop_table("transactions")
    op.drop_table("bank_accounts")
    op.drop_table("consent_records")
    op.drop_table("users")
