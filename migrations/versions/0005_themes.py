"""Темы оформления: наборы картинок к экранам, выбор темы пользователем

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    themes = op.create_table(
        "themes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=64), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_themes")),
        sa.UniqueConstraint("code", name=op.f("uq_themes_code")),
    )
    op.create_table(
        "theme_images",
        sa.Column("theme_id", sa.Integer(), nullable=False),
        sa.Column("screen", sa.String(length=16), nullable=False),
        sa.Column("file_id", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["theme_id"],
            ["themes.id"],
            name=op.f("fk_theme_images_theme_id_themes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("theme_id", "screen", name=op.f("pk_theme_images")),
    )
    op.add_column("users", sa.Column("theme_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_users_theme_id_themes"),
        "users",
        "themes",
        ["theme_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Встроенные темы, картинки к ним админ загружает в боте.
    op.bulk_insert(
        themes,
        [
            {"code": "light", "name": "☀️ Светлая", "name_en": "☀️ Light", "sort_order": 1},
            {"code": "dark", "name": "🌙 Тёмная", "name_en": "🌙 Dark", "sort_order": 2},
        ],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_users_theme_id_themes"), "users", type_="foreignkey")
    op.drop_column("users", "theme_id")
    op.drop_table("theme_images")
    op.drop_table("themes")
