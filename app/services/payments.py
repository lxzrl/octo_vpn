import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import (
    BalanceOperation,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Plan,
    PromoActivation,
    User,
)
from app.services.balance import change_balance
from app.services.clock import as_utc, utcnow
from app.services.money import percent_of, stars_for
from app.services.options import Options
from app.services.promo import pending_discount
from app.services.subscriptions import extend_subscription
from app.vpn.panel import VpnPanel

logger = logging.getLogger(__name__)

PAYLOAD_PREFIX = "pay:"


@dataclass(frozen=True, slots=True)
class Quote:
    price_kop: int
    discount_percent: int
    discount_kop: int
    balance_used_kop: int
    to_pay_kop: int
    stars: int
    promo_activation_id: int | None


async def make_quote(session: AsyncSession, user: User, plan: Plan, rate: Decimal) -> Quote:
    """Итог к оплате: сначала скидка по промокоду, затем баланс, остаток — звёздами."""
    if plan.price_rub is None:
        raise ValueError(f"Plan {plan.id} has no price")
    price = plan.price_rub * 100
    discount = await pending_discount(session, user.id)
    percent = discount[1] if discount else 0
    discount_kop = percent_of(price, percent)
    after_discount = price - discount_kop
    balance_used = min(user.balance_kop, after_discount)
    to_pay = after_discount - balance_used
    return Quote(
        price_kop=price,
        discount_percent=percent,
        discount_kop=discount_kop,
        balance_used_kop=balance_used,
        to_pay_kop=to_pay,
        stars=stars_for(to_pay, rate),
        promo_activation_id=discount[0].id if discount else None,
    )


def payload(payment: Payment) -> str:
    return f"{PAYLOAD_PREFIX}{payment.id}"


def parse_payload(value: str) -> int | None:
    raw = value.removeprefix(PAYLOAD_PREFIX)
    return int(raw) if value.startswith(PAYLOAD_PREFIX) and raw.isdigit() else None


async def cancel_payment(session: AsyncSession, payment: Payment) -> None:
    """Отменяет неоплаченный счёт и возвращает зарезервированный баланс."""
    if payment.status != PaymentStatus.PENDING:
        return
    payment.status = PaymentStatus.CANCELLED
    if payment.balance_used_kop:
        user = await session.get(User, payment.user_id, with_for_update=True)
        assert user is not None
        await change_balance(
            session, user, payment.balance_used_kop, BalanceOperation.REFUND, payment_id=payment.id
        )
    await session.flush()


async def create_payment(
    session: AsyncSession, user: User, plan: Plan, options: Options
) -> Payment:
    """Создаёт платёж и резервирует баланс. Если баланса хватает, платёж сразу оплачен."""
    await session.refresh(user, with_for_update=True)
    # Один открытый счёт на пользователя: старые отменяем, их резерв возвращается.
    for old in await session.scalars(
        select(Payment).where(Payment.user_id == user.id, Payment.status == PaymentStatus.PENDING)
    ):
        await cancel_payment(session, old)

    quote = await make_quote(session, user, plan, options.stars_rub_rate)
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        days=plan.days,
        provider=PaymentProvider.STARS if quote.to_pay_kop else PaymentProvider.BALANCE,
        status=PaymentStatus.PENDING,
        price_kop=quote.price_kop,
        discount_kop=quote.discount_kop,
        balance_used_kop=quote.balance_used_kop,
        stars=quote.stars,
        promo_activation_id=quote.promo_activation_id,
    )
    session.add(payment)
    await session.flush()
    await change_balance(
        session, user, -quote.balance_used_kop, BalanceOperation.PURCHASE, payment_id=payment.id
    )
    if not quote.to_pay_kop:
        await mark_paid(session, payment, user, options, charge_id=None)
    return payment


def is_expired(payment: Payment, settings: Settings) -> bool:
    return as_utc(payment.created_at) + timedelta(minutes=settings.payment_ttl_minutes) <= utcnow()


async def can_checkout(
    session: AsyncSession, payment_id: int | None, user_id: int, stars: int, settings: Settings
) -> bool:
    """Проверка перед списанием звёзд (pre_checkout_query)."""
    if payment_id is None:
        return False
    payment = await session.get(Payment, payment_id)
    return (
        payment is not None
        and payment.user_id == user_id
        and payment.status == PaymentStatus.PENDING
        and payment.stars == stars
        # Запас 5 минут, чтобы фоновая отмена не успела сработать между проверкой и оплатой.
        and as_utc(payment.created_at) + timedelta(minutes=settings.payment_ttl_minutes - 5)
        > utcnow()
    )


@dataclass(frozen=True, slots=True)
class ReferralReward:
    referrer: User
    amount_kop: int


async def mark_paid(
    session: AsyncSession,
    payment: Payment,
    user: User,
    options: Options,
    charge_id: str | None,
) -> ReferralReward | None:
    """Фиксирует оплату: тратит скидку, начисляет рефереру. Подписку продлевает fulfill_payment."""
    if payment.status == PaymentStatus.CANCELLED:
        # Звёзды уже списаны, а счёт успели отменить: снова резервируем баланс, сколько есть.
        logger.warning("Payment %s was paid after cancellation", payment.id)
        payment.balance_used_kop = min(payment.balance_used_kop, user.balance_kop)
        await change_balance(
            session,
            user,
            -payment.balance_used_kop,
            BalanceOperation.PURCHASE,
            payment_id=payment.id,
        )
    payment.status = PaymentStatus.PAID
    payment.paid_at = utcnow()
    payment.telegram_charge_id = charge_id
    payment.paid_kop = payment.price_kop - payment.discount_kop - payment.balance_used_kop
    if payment.promo_activation_id is not None:
        activation = await session.get(PromoActivation, payment.promo_activation_id)
        if activation is not None:
            activation.used_at = utcnow()
    await session.flush()
    return await reward_referrer(session, payment, user, options)


async def reward_referrer(
    session: AsyncSession, payment: Payment, user: User, options: Options
) -> ReferralReward | None:
    if payment.paid_kop <= 0 or user.referrer_id is None:
        return None
    referrer = await session.get(User, user.referrer_id, with_for_update=True)
    if referrer is None:
        return None
    had_paid_before = await session.scalar(
        select(
            exists().where(
                Payment.user_id == user.id,
                Payment.id != payment.id,
                Payment.status == PaymentStatus.PAID,
                Payment.paid_kop > 0,
            )
        )
    )
    percent = options.referral_next_percent if had_paid_before else options.referral_first_percent
    amount = percent_of(payment.paid_kop, percent)
    if amount <= 0:
        return None
    await change_balance(
        session,
        referrer,
        amount,
        BalanceOperation.REFERRAL,
        payment_id=payment.id,
        source_user_id=user.id,
    )
    return ReferralReward(referrer, amount)


async def complete_stars_payment(
    session: AsyncSession,
    payment_id: int | None,
    user: User,
    charge_id: str,
    options: Options,
) -> tuple[Payment, ReferralReward | None] | None:
    """Обрабатывает successful_payment. Повтор с тем же charge_id ничего не делает."""
    if payment_id is None:
        return None
    payment = await session.get(Payment, payment_id, with_for_update=True)
    if payment is None or payment.user_id != user.id or payment.status == PaymentStatus.PAID:
        return None
    await session.refresh(user, with_for_update=True)
    reward = await mark_paid(session, payment, user, options, charge_id)
    return payment, reward


async def fulfill_payment(
    session: AsyncSession, panel: VpnPanel, payment: Payment, user: User
) -> None:
    """Продлевает подписку по оплаченному платежу. При ошибке панели бросает PanelError."""
    if payment.fulfilled_at is not None:
        return
    await extend_subscription(session, panel, user, payment.days)
    payment.fulfilled_at = utcnow()
    await session.flush()


async def unfulfilled_payments(session: AsyncSession) -> list[Payment]:
    result = await session.scalars(
        select(Payment)
        .where(Payment.status == PaymentStatus.PAID, Payment.fulfilled_at.is_(None))
        .order_by(Payment.id)
    )
    return list(result)


async def expired_pending_payments(session: AsyncSession, settings: Settings) -> list[Payment]:
    deadline = utcnow() - timedelta(minutes=settings.payment_ttl_minutes)
    result = await session.scalars(
        select(Payment).where(
            Payment.status == PaymentStatus.PENDING, Payment.created_at <= deadline
        )
    )
    return list(result)
