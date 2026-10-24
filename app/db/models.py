from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    # Telegram ID пользователя и есть первичный ключ.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(32))
    first_name: Mapped[str] = mapped_column(String(64), default="")
    # None, пока пользователь не выбрал язык при первом запуске.
    language: Mapped[str | None] = mapped_column(String(2))
    referrer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Пользователь заблокировал бота: не шлём ему рассылки и напоминания.
    is_blocked_bot: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    trial_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Subscription(TimestampMixin, Base):
    """VPN-доступ пользователя: одна запись на пользователя, продлевается покупками."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    panel_user_id: Mapped[int] = mapped_column(Integer)
    panel_username: Mapped[str] = mapped_column(String(36))
    subscription_url: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # Текущий срок выдан пробным периодом и ещё ни разу не оплачен.
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class Plan(TimestampMixin, Base):
    """Тариф. Без цены тариф не показывается в магазине."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    months: Mapped[int] = mapped_column(Integer)
    days: Mapped[int] = mapped_column(Integer)
    price_rub: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
