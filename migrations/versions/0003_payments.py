"""Платежи, баланс, промокоды, напоминания

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("uses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promo_codes")),
        sa.UniqueConstraint("code", name=op.f("uq_promo_codes_code")),
    )
    op.create_table(
        "promo_activations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("promo_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["promo_id"],
            ["promo_codes.id"],
            name=op.f("fk_promo_activations_promo_id_promo_codes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_promo_activations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promo_activations")),
        sa.UniqueConstraint("promo_id", "user_id", name=op.f("uq_promo_activations_promo_id")),
    )
    op.create_index(
        op.f("ix_promo_activations_user_id"), "promo_activations", ["user_id"], unique=False
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("price_kop", sa.BigInteger(), nullable=False),
        sa.Column("discount_kop", sa.BigInteger(), nullable=False),
        sa.Column("balance_used_kop", sa.BigInteger(), nullable=False),
        sa.Column("paid_kop", sa.BigInteger(), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("promo_activation_id", sa.Integer(), nullable=True),
        sa.Column("telegram_charge_id", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], name=op.f("fk_payments_plan_id_plans")),
        sa.ForeignKeyConstraint(
            ["promo_activation_id"],
            ["promo_activations.id"],
            name=op.f("fk_payments_promo_activation_id_promo_activations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_payments_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
        sa.UniqueConstraint("telegram_charge_id", name=op.f("uq_payments_telegram_charge_id")),
    )
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)
    op.create_table(
        "balance_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("amount_kop", sa.BigInteger(), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("source_user_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name=op.f("fk_balance_transactions_payment_id_payments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_balance_transactions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_balance_transactions")),
    )
    op.create_index(
        op.f("ix_balance_transactions_user_id"), "balance_transactions", ["user_id"], unique=False
    )
    op.add_column(
        "subscriptions",
        sa.Column("reminders_sent", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users", sa.Column("balance_kop", sa.BigInteger(), server_default="0", nullable=False)
    )


def downgrade() -> None:
    op.drop_column("users", "balance_kop")
    op.drop_column("subscriptions", "reminders_sent")
    op.drop_index(op.f("ix_balance_transactions_user_id"), table_name="balance_transactions")
    op.drop_table("balance_transactions")
    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_status"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_promo_activations_user_id"), table_name="promo_activations")
    op.drop_table("promo_activations")
    op.drop_table("promo_codes")
