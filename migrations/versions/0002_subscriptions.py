"""Подписки, тарифы, отметка о пробном периоде

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    plans = op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("months", sa.Integer(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("price_rub", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plans")),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("panel_user_id", sa.Integer(), nullable=False),
        sa.Column("panel_username", sa.String(length=36), nullable=False),
        sa.Column("subscription_url", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_trial", sa.Boolean(), server_default="false", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_subscriptions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
        sa.UniqueConstraint("user_id", name=op.f("uq_subscriptions_user_id")),
    )
    op.create_index(
        op.f("ix_subscriptions_expires_at"), "subscriptions", ["expires_at"], unique=False
    )
    op.add_column("users", sa.Column("trial_used_at", sa.DateTime(timezone=True), nullable=True))

    # Стартовые тарифы без цен: цены задаются позже, до этого тарифы не показываются.
    op.bulk_insert(
        plans,
        [
            {"months": 1, "days": 30, "sort_order": 1},
            {"months": 3, "days": 90, "sort_order": 2},
            {"months": 6, "days": 180, "sort_order": 3},
            {"months": 12, "days": 365, "sort_order": 4},
        ],
    )


def downgrade() -> None:
    op.drop_column("users", "trial_used_at")
    op.drop_index(op.f("ix_subscriptions_expires_at"), table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("plans")
