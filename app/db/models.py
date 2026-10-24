from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
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
    # Внутренний баланс в копейках: реферальные начисления и промокоды. Вывести нельзя.
    balance_kop: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")


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
    # Битовая маска уже отправленных напоминаний (см. services/reminders.py).
    reminders_sent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Plan(TimestampMixin, Base):
    """Тариф. Без цены тариф не показывается в магазине."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    months: Mapped[int] = mapped_column(Integer)
    days: Mapped[int] = mapped_column(Integer)
    price_rub: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentProvider(StrEnum):
    STARS = "stars"
    BALANCE = "balance"


class Payment(TimestampMixin, Base):
    """Покупка тарифа. Суммы в копейках; stars — сколько звёзд выставлено в счёте."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    days: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default=PaymentStatus.PENDING, index=True)
    price_kop: Mapped[int] = mapped_column(BigInteger)
    discount_kop: Mapped[int] = mapped_column(BigInteger, default=0)
    balance_used_kop: Mapped[int] = mapped_column(BigInteger, default=0)
    # Сколько заплачено реальными деньгами (в рублёвом эквиваленте).
    paid_kop: Mapped[int] = mapped_column(BigInteger, default=0)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    promo_activation_id: Mapped[int | None] = mapped_column(
        ForeignKey("promo_activations.id", ondelete="SET NULL")
    )
    telegram_charge_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Подписка продлена в панели. Оплаченные, но не выданные платежи довыдаёт фоновая задача.
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BalanceOperation(StrEnum):
    REFERRAL = "referral"
    PROMO = "promo"
    PURCHASE = "purchase"
    REFUND = "refund"
    ADMIN = "admin"


class BalanceTransaction(Base):
    """Журнал движений по балансу: сумма всех записей пользователя равна его балансу."""

    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    amount_kop: Mapped[int] = mapped_column(BigInteger)
    operation: Mapped[str] = mapped_column(String(16))
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
    # Для реферальных начислений: чья покупка принесла бонус.
    source_user_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromoKind(StrEnum):
    DISCOUNT = "discount"  # value — скидка в процентах на следующую покупку
    BALANCE = "balance"  # value — сумма на баланс в копейках
    DAYS = "days"  # value — дни подписки


class PromoCode(TimestampMixin, Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    kind: Mapped[str] = mapped_column(String(16))
    value: Mapped[int] = mapped_column(Integer)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    uses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class PromoActivation(Base):
    """Пользователь ввёл промокод. Для скидки payment_id заполняется, когда скидка потрачена."""

    __tablename__ = "promo_activations"
    __table_args__ = (UniqueConstraint("promo_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    promo_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
