from datetime import timedelta

import pytest
from aiogram import Bot
from aiogram.methods import SendMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.models import BalanceOperation, Payment, PaymentStatus, Plan, User
from app.i18n import TranslatorHub
from app.services.balance import change_balance
from app.services.clock import utcnow
from app.services.payments import complete_stars_payment, create_payment
from app.services.subscriptions import extend_subscription
from app.worker import BackgroundJobs
from tests.fakes import FakePanel, FakeSession

SETTINGS = Settings(bot_token="1:x")


@pytest.fixture
def fake() -> FakeSession:
    return FakeSession()


@pytest.fixture
def panel() -> FakePanel:
    return FakePanel()


@pytest.fixture
def jobs(
    fake: FakeSession, panel: FakePanel, session_factory: async_sessionmaker[AsyncSession]
) -> BackgroundJobs:
    return BackgroundJobs(
        Bot("42:TEST", session=fake), session_factory, panel, TranslatorHub("ru"), SETTINGS
    )


def messages(fake: FakeSession) -> list[SendMessage]:
    return [c for c in fake.calls if isinstance(c, SendMessage)]


async def test_retries_paid_but_unfulfilled_payment(
    jobs: BackgroundJobs,
    fake: FakeSession,
    panel: FakePanel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = User(id=1, first_name="U", language="ru")
        plan = Plan(months=1, days=30, price_rub=100)
        session.add_all([user, plan])
        await session.flush()
        payment = await create_payment(session, user, plan, SETTINGS)
        await complete_stars_payment(session, payment.id, user, "c", SETTINGS)
        await session.commit()

    panel.fail = True
    await jobs.run_once()
    assert messages(fake) == []

    panel.fail = False
    await jobs.run_once()
    assert "Оплата прошла" in messages(fake)[-1].text
    async with session_factory() as session:
        stored = await session.get(Payment, payment.id)
        assert stored is not None and stored.fulfilled_at is not None


async def test_cancels_expired_invoice_and_refunds(
    jobs: BackgroundJobs, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session:
        user = User(id=1, first_name="U")
        plan = Plan(months=1, days=30, price_rub=100)
        session.add_all([user, plan])
        await session.flush()
        await change_balance(session, user, 3000, BalanceOperation.ADMIN)
        payment = await create_payment(session, user, plan, SETTINGS)
        payment.created_at = utcnow() - timedelta(hours=2)
        await session.commit()

    await jobs.run_once()
    async with session_factory() as session:
        stored = await session.get(Payment, payment.id)
        refunded = await session.get(User, 1)
        assert stored is not None and stored.status == PaymentStatus.CANCELLED
        assert refunded is not None and refunded.balance_kop == 3000


async def test_sends_reminder_once(
    jobs: BackgroundJobs,
    fake: FakeSession,
    panel: FakePanel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = User(id=1, first_name="U", language="en")
        session.add(user)
        await session.flush()
        # Подписка куплена 26 дней назад на 30 дней: осталось 4 дня.
        await extend_subscription(session, panel, user, 30, now=utcnow() - timedelta(days=26))
        await session.commit()

    await jobs.run_once()
    await jobs.run_once()
    sent = messages(fake)
    assert len(sent) == 1 and "ends in 5 days" in sent[0].text
