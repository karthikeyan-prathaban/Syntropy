"""production schema: ingestion, enrichment, budgets, auth hardening

Revision ID: 002
Revises: 001
Create Date: 2026-09-17
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def _backfill_txn_hashes() -> None:
    """Existing rows predate txn_hash, so compute it before the unique index lands."""
    from app.ingestion.dedupe import compute_txn_hash

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT t.id, t.user_id, a.linked_acc_ref, t.transaction_timestamp, "
            "t.amount, t.txn_type, t.narration "
            "FROM transactions t JOIN bank_accounts a ON a.id = t.account_id"
        )
    ).fetchall()

    seen: set[tuple[int, str]] = set()
    for row in rows:
        timestamp = row.transaction_timestamp
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        digest = compute_txn_hash(
            row.user_id, row.linked_acc_ref, timestamp, row.amount, row.txn_type, row.narration or ""
        )
        # Pre-existing duplicates would violate the new unique index; disambiguate them.
        while (row.user_id, digest) in seen:
            digest = digest[:-8] + f"{row.id:08x}"
        seen.add((row.user_id, digest))
        bind.execute(
            sa.text("UPDATE transactions SET txn_hash = :h, raw_narration = narration WHERE id = :i"),
            {"h": digest, "i": row.id},
        )


def upgrade() -> None:
    # --- new tables -------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    op.create_table(
        "merchants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("canonical_key", sa.String(120), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("vpa_handles", sa.JSON(), nullable=True),
        sa.Column("mcc", sa.String(8), nullable=True),
        sa.Column("logo_url", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "canonical_key", name="uq_merchant_user_key"),
    )
    op.create_index("ix_merchants_user_id", "merchants", ["user_id"])
    op.create_index("ix_merchants_canonical_key", "merchants", ["canonical_key"])

    op.create_table(
        "recurring_series",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id"), nullable=True),
        sa.Column("merchant_name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("cadence", sa.String(20), nullable=False),
        sa.Column("interval_days", sa.Float(), nullable=False),
        sa.Column("expected_amount", sa.Float(), nullable=False),
        sa.Column("amount_variation", sa.Float(), nullable=True),
        sa.Column("occurrences", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("direction", sa.String(10), nullable=True),
        sa.Column("first_seen", sa.Date(), nullable=False),
        sa.Column("last_seen", sa.Date(), nullable=False),
        sa.Column("next_due", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_recurring_series_user_id", "recurring_series", ["user_id"])

    op.create_table(
        "balance_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.UniqueConstraint("account_id", "snapshot_date", name="uq_balance_account_date"),
    )
    op.create_index("ix_balance_snapshots_user_id", "balance_snapshots", ["user_id"])
    op.create_index("ix_balance_snapshots_account_id", "balance_snapshots", ["account_id"])
    op.create_index("ix_balance_snapshots_snapshot_date", "balance_snapshots", ["snapshot_date"])

    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("monthly_limit", sa.Float(), nullable=False),
        sa.Column("alert_threshold", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "category", name="uq_budget_user_category"),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])

    op.create_table(
        "goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("target_amount", sa.Float(), nullable=False),
        sa.Column("current_amount", sa.Float(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("is_achieved", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])

    op.create_table(
        "statement_uploads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(80), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("detected_bank", sa.String(60), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("rows_parsed", sa.Integer(), nullable=True),
        sa.Column("rows_imported", sa.Integer(), nullable=True),
        sa.Column("rows_duplicate", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_statement_uploads_user_id", "statement_uploads", ["user_id"])
    op.create_index("ix_statement_uploads_status", "statement_uploads", ["status"])

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("trigger", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("accounts_seen", sa.Integer(), nullable=True),
        sa.Column("rows_in", sa.Integer(), nullable=True),
        sa.Column("rows_new", sa.Integer(), nullable=True),
        sa.Column("rows_duplicate", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ingestion_runs_user_id", "ingestion_runs", ["user_id"])

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=True),
        sa.Column("consent_id", sa.String(120), nullable=True),
        sa.Column("session_id", sa.String(120), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_webhook_events_consent_id", "webhook_events", ["consent_id"])
    op.create_index("ix_webhook_events_processed", "webhook_events", ["processed"])

    # --- users ------------------------------------------------------------
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("is_demo", sa.Boolean(), nullable=True, server_default=sa.false()))
        batch.add_column(sa.Column("email_verified", sa.Boolean(), nullable=True, server_default=sa.false()))
    op.create_index("ix_users_email_hash", "users", ["email_hash"], unique=True)

    # --- consent_records --------------------------------------------------
    with op.batch_alter_table("consent_records") as batch:
        batch.add_column(sa.Column("fi_types", sa.String(255), nullable=True, server_default="DEPOSIT"))
        batch.add_column(sa.Column("purpose_code", sa.String(10), nullable=True, server_default="101"))
        batch.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("last_fetched_at", sa.DateTime(), nullable=True))
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])
    op.create_index("ix_consent_records_consent_id", "consent_records", ["consent_id"])

    # --- bank_accounts ----------------------------------------------------
    with op.batch_alter_table("bank_accounts") as batch:
        batch.add_column(sa.Column("fi_type", sa.String(40), nullable=True, server_default="DEPOSIT"))
        batch.add_column(sa.Column("bank_name", sa.String(120), nullable=True))
        batch.add_column(sa.Column("holder_name", sa.String(160), nullable=True))
        batch.add_column(sa.Column("holdings", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("source", sa.String(20), nullable=True, server_default="aa"))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()))
        batch.add_column(sa.Column("last_synced_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        # Batch mode is required because SQLite cannot ALTER a constraint in place.
        batch.create_unique_constraint("uq_account_user_ref", ["user_id", "linked_acc_ref"])
    op.create_index("ix_bank_accounts_user_id", "bank_accounts", ["user_id"])
    op.create_index("ix_bank_accounts_fi_type", "bank_accounts", ["fi_type"])

    # --- transactions -----------------------------------------------------
    with op.batch_alter_table("transactions") as batch:
        batch.add_column(sa.Column("txn_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("raw_narration", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("category_overridden_by_user", sa.Boolean(), nullable=True, server_default=sa.false())
        )
        batch.add_column(sa.Column("merchant_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("merchant_name", sa.String(160), nullable=True))
        batch.add_column(sa.Column("counterparty_vpa", sa.String(120), nullable=True))
        batch.add_column(sa.Column("is_transfer", sa.Boolean(), nullable=True, server_default=sa.false()))
        batch.add_column(sa.Column("transfer_pair_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("is_recurring", sa.Boolean(), nullable=True, server_default=sa.false()))
        batch.add_column(sa.Column("recurring_series_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("source", sa.String(20), nullable=True, server_default="aa"))
        batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))

    # The unique index cannot land until every existing row has a hash.
    _backfill_txn_hashes()

    with op.batch_alter_table("transactions") as batch:
        batch.create_unique_constraint("uq_txn_user_hash", ["user_id", "txn_hash"])

    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_txn_hash", "transactions", ["txn_hash"])
    op.create_index("ix_transactions_category", "transactions", ["category"])
    op.create_index("ix_transactions_is_transfer", "transactions", ["is_transfer"])
    op.create_index("ix_transactions_transfer_pair_id", "transactions", ["transfer_pair_id"])
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_txn_user_timestamp", "transactions", ["user_id", "transaction_timestamp"])
    op.create_index("ix_txn_user_category", "transactions", ["user_id", "category"])


def downgrade() -> None:
    for index in (
        "ix_txn_user_category",
        "ix_txn_user_timestamp",
        "ix_transactions_merchant_id",
        "ix_transactions_transfer_pair_id",
        "ix_transactions_is_transfer",
        "ix_transactions_category",
        "ix_transactions_txn_hash",
        "ix_transactions_account_id",
        "ix_transactions_user_id",
    ):
        op.drop_index(index, table_name="transactions")
    with op.batch_alter_table("transactions") as batch:
        batch.drop_constraint("uq_txn_user_hash", type_="unique")
        for column in (
            "created_at", "source", "recurring_series_id", "is_recurring", "transfer_pair_id",
            "is_transfer", "counterparty_vpa", "merchant_name", "merchant_id",
            "category_overridden_by_user", "raw_narration", "txn_hash",
        ):
            batch.drop_column(column)

    op.drop_index("ix_bank_accounts_fi_type", table_name="bank_accounts")
    op.drop_index("ix_bank_accounts_user_id", table_name="bank_accounts")
    with op.batch_alter_table("bank_accounts") as batch:
        batch.drop_constraint("uq_account_user_ref", type_="unique")
        for column in (
            "created_at", "last_synced_at", "is_active", "source", "holdings",
            "holder_name", "bank_name", "fi_type",
        ):
            batch.drop_column(column)

    op.drop_index("ix_consent_records_consent_id", table_name="consent_records")
    op.drop_index("ix_consent_records_user_id", table_name="consent_records")
    with op.batch_alter_table("consent_records") as batch:
        for column in ("last_fetched_at", "expires_at", "purpose_code", "fi_types"):
            batch.drop_column(column)

    op.drop_index("ix_users_email_hash", table_name="users")
    with op.batch_alter_table("users") as batch:
        for column in ("email_verified", "is_demo", "email_hash"):
            batch.drop_column(column)

    for table in (
        "webhook_events", "ingestion_runs", "statement_uploads", "goals", "budgets",
        "balance_snapshots", "recurring_series", "merchants", "refresh_tokens",
    ):
        op.drop_table(table)
