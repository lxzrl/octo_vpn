from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Payment, PaymentStatus, Plan, Subscription, User
from app.services.admin import Audience, audience_ids, find_user, parse_amount_kop, user_card
from app.services.clock import utcnow
from app.services.stats import collect_stats
from app.services.tickets import add_user_message


def subscription(user_id: int, days: int, is_trial: bool = False) -> Subscription:
    return Subscription(
        user_id=user_id,
        panel_user_id=user_id,
        panel_username=f"tg_{user_id}",
        subscription_url="https://sub.example",
        expires_at=utcnow() + timedelta(days=days),
        is_trial=is_trial,
    )


async def seed(session: AsyncSession) -> None:
    session.add_all(
        [
            User(id=1, first_name="Paid", username="PaidUser"),
            User(id=2, first_name="Trial", trial_used_at=utcnow()),
            User(id=3, first_name="Expired", referrer_id=1),
            User(id=4, first_name="Banned", is_banned=True),
            User(id=5, first_name="Gone", is_blocked_bot=True),
        ]
    )
    await session.flush()
    session.add_all([subscription(1, 10), subscription(2, 2, is_trial=True), subscription(3, -1)])
    plan = Plan(months=1, days=30, price_rub=200)
    session.add(plan)
    await session.flush()
    session.add(
        Payment(
            user_id=1,
            plan_id=plan.id,
            days=30,
            provider="stars",
            status=PaymentStatus.PAID,
            price_kop=20000,
            paid_kop=20000,
            stars=134,
            paid_at=utcnow(),
        )
    )
    await session.flush()


async def test_find_user_by_id_and_username(session: AsyncSession) -> None:
    await seed(session)
    assert (await find_user(session, "2")).first_name == "Trial"  # type: ignore[union-attr]
    assert (await find_user(session, "@paiduser")).id == 1  # type: ignore[union-attr]
    assert (await find_user(session, "PaidUser")).id == 1  # type: ignore[union-attr]
    assert await find_user(session, "@nobody") is None
    assert await find_user(session, "not a name!") is None


async def test_user_card(session: AsyncSession) -> None:
    await seed(session)
    user = await session.get(User, 1)
    assert user is not None
    await add_user_message(session, user, "help")
    card = await user_card(session, user)
    assert card.payments == 1 and card.paid_kop == 20000
    assert card.referrals.invited == 1
    assert card.subscription is not None and card.ticket is not None


def test_parse_amount() -> None:
    assert parse_amount_kop("150") == 15000
    assert parse_amount_kop("-50") == -5000
    assert parse_amount_kop("+99,90") == 9990
    assert parse_amount_kop("1 000") == 100000
    assert parse_amount_kop("0") is None
    assert parse_amount_kop("1.234") is None
    assert parse_amount_kop("abc") is None


async def test_broadcast_audience_skips_banned_and_blocked(session: AsyncSession) -> None:
    await seed(session)
    assert await audience_ids(session, Audience.ALL) == [1, 2, 3]
    assert await audience_ids(session, Audience.ACTIVE) == [1, 2]
    assert await audience_ids(session, Audience.INACTIVE) == [3]


async def test_stats(session: AsyncSession) -> None:
    await seed(session)
    stats = await collect_stats(session)
    assert stats.users == 5 and stats.users_day == 5 and stats.blocked == 1
    assert stats.active_paid == 1 and stats.active_trial == 1 and stats.trials_used == 1
    assert stats.revenue_day.payments == 1 and stats.revenue_total.paid_kop == 20000
    assert stats.revenue_total.stars == 134
