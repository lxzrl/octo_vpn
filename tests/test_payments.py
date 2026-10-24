from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import (
    BalanceOperation,
    BalanceTransaction,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Plan,
    PromoCode,
    PromoKind,
    User,
)
from app.services.balance import change_balance, ledger_total
from app.services.clock import as_utc, utcnow
from app.services.payments import (
    can_checkout,
    complete_stars_payment,
    create_payment,
    expired_pending_payments,
    fulfill_payment,
    make_quote,
)
from app.services.promo import apply_promo
from app.services.subscriptions import get_subscription
from app.services.users import TelegramProfile, get_or_create_user
from tests.fakes import FakePanel

SETTINGS = Settings(bot_token="1:x", stars_rub_rate="2")


@pytest.fixture
async def plan(session: AsyncSession) -> Plan:
    plan = Plan(months=1, days=30, price_rub=200)
    session.add(plan)
    await session.flush()
    return plan


async def make_user(session: AsyncSession, user_id: int, referrer_id: int | None = None) -> User:
    user, _ = await get_or_create_user(session, TelegramProfile(user_id, None, "U"), referrer_id)
    return user


async def pay(session: AsyncSession, user: User, plan: Plan, charge: str = "ch") -> Payment:
    payment = await create_payment(session, user, plan, SETTINGS)
    result = await complete_stars_payment(session, payment.id, user, charge, SETTINGS)
    assert result is not None
    return result[0]


async def test_quote_without_discount_or_balance(session: AsyncSession, plan: Plan) -> None:
    user = await make_user(session, 1)
    quote = await make_quote(session, user, plan, SETTINGS)
    assert (quote.to_pay_kop, quote.stars) == (20000, 100)


async def test_quote_applies_discount_then_balance(session: AsyncSession, plan: Plan) -> None:
    user = await make_user(session, 1)
    session.add(PromoCode(code="SALE20", kind=PromoKind.DISCOUNT, value=20))
    await session.flush()
    await apply_promo(session, FakePanel(), user, "sale20")
    await change_balance(session, user, 5000, BalanceOperation.ADMIN)

    quote = await make_quote(session, user, plan, SETTINGS)
    assert quote.discount_kop == 4000
    assert quote.balance_used_kop == 5000
    assert quote.to_pay_kop == 11000 and quote.stars == 55


async def test_stars_payment_full_cycle(session: AsyncSession, plan: Plan) -> None:
    user = await make_user(session, 1)
    payment = await create_payment(session, user, plan, SETTINGS)
    assert payment.provider == PaymentProvider.STARS and payment.stars == 100
    assert await can_checkout(session, payment.id, user.id, 100, SETTINGS)
    assert not await can_checkout(session, payment.id, user.id, 99, SETTINGS)
    assert not await can_checkout(session, payment.id, 2, 100, SETTINGS)

    result = await complete_stars_payment(session, payment.id, user, "charge-1", SETTINGS)
    assert result is not None and result[0].status == PaymentStatus.PAID
    assert result[0].paid_kop == 20000
    # Telegram может прислать подтверждение повторно.
    assert await complete_stars_payment(session, payment.id, user, "charge-1", SETTINGS) is None

    panel = FakePanel()
    await fulfill_payment(session, panel, payment, user)
    await fulfill_payment(session, panel, payment, user)
    sub = await get_subscription(session, user.id)
    assert sub is not None and len(panel.users) == 1
    assert as_utc(sub.expires_at) - utcnow() > timedelta(days=29)
    assert as_utc(sub.expires_at) - utcnow() <= timedelta(days=30)


async def test_balance_covers_whole_price(session: AsyncSession, plan: Plan) -> None:
    user = await make_user(session, 1)
    await change_balance(session, user, 25000, BalanceOperation.ADMIN)
    payment = await create_payment(session, user, plan, SETTINGS)
    assert payment.provider == PaymentProvider.BALANCE
    assert payment.status == PaymentStatus.PAID and payment.paid_kop == 0
    assert user.balance_kop == 5000
    assert await ledger_total(session, user.id) == user.balance_kop


async def test_new_invoice_cancels_old_and_returns_reserved_balance(
    session: AsyncSession, plan: Plan
) -> None:
    user = await make_user(session, 1)
    await change_balance(session, user, 5000, BalanceOperation.ADMIN)
    first = await create_payment(session, user, plan, SETTINGS)
    assert user.balance_kop == 0 and first.balance_used_kop == 5000

    second = await create_payment(session, user, plan, SETTINGS)
    assert first.status == PaymentStatus.CANCELLED
    assert second.balance_used_kop == 5000 and user.balance_kop == 0
    assert await ledger_total(session, user.id) == 0


async def test_expired_invoice_is_rejected_and_listed(session: AsyncSession, plan: Plan) -> None:
    user = await make_user(session, 1)
    payment = await create_payment(session, user, plan, SETTINGS)
    payment.created_at = utcnow() - timedelta(minutes=SETTINGS.payment_ttl_minutes + 1)
    await session.flush()
    assert not await can_checkout(session, payment.id, user.id, payment.stars, SETTINGS)
    assert [p.id for p in await expired_pending_payments(session, SETTINGS)] == [payment.id]


async def test_referral_reward_first_then_next(session: AsyncSession, plan: Plan) -> None:
    referrer = await make_user(session, 1)
    friend = await make_user(session, 2, referrer_id=1)

    payment = await create_payment(session, friend, plan, SETTINGS)
    result = await complete_stars_payment(session, payment.id, friend, "c1", SETTINGS)
    assert result is not None and result[1] is not None
    assert result[1].amount_kop == 4000  # 20% от 200 ₽

    payment = await create_payment(session, friend, plan, SETTINGS)
    result = await complete_stars_payment(session, payment.id, friend, "c2", SETTINGS)
    assert result is not None and result[1] is not None
    assert result[1].amount_kop == 2000  # 10%
    assert referrer.balance_kop == 6000

    rows = await session.scalars(
        select(BalanceTransaction).where(BalanceTransaction.user_id == referrer.id)
    )
    assert {r.source_user_id for r in rows} == {friend.id}


async def test_no_referral_reward_for_balance_only_purchase(
    session: AsyncSession, plan: Plan
) -> None:
    referrer = await make_user(session, 1)
    friend = await make_user(session, 2, referrer_id=1)
    await change_balance(session, friend, 20000, BalanceOperation.ADMIN)
    await create_payment(session, friend, plan, SETTINGS)
    assert referrer.balance_kop == 0


async def test_discount_is_spent_by_payment(session: AsyncSession, plan: Plan) -> None:
    user = await make_user(session, 1)
    session.add(PromoCode(code="SALE", kind=PromoKind.DISCOUNT, value=50))
    await session.flush()
    await apply_promo(session, FakePanel(), user, "SALE")
    await pay(session, user, plan)
    quote = await make_quote(session, user, plan, SETTINGS)
    assert quote.discount_kop == 0
