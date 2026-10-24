from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.reminders import Reminder, collect_due_reminders
from app.services.subscriptions import extend_subscription
from app.services.users import TelegramProfile, get_or_create_user
from tests.fakes import FakePanel

NOW = datetime(2026, 3, 1, 12, tzinfo=UTC)


async def reminders_at(session: AsyncSession, moment: datetime) -> list[Reminder]:
    return [d.reminder for d in await collect_due_reminders(session, moment)]


async def test_month_subscription_gets_every_reminder_once(session: AsyncSession) -> None:
    user, _ = await get_or_create_user(session, TelegramProfile(1, None, "U"))
    await extend_subscription(session, FakePanel(), user, 30, now=NOW)
    end = NOW + timedelta(days=30)

    assert await reminders_at(session, NOW + timedelta(days=1)) == []
    assert await reminders_at(session, end - timedelta(days=5)) == [Reminder.DAYS_5]
    assert await reminders_at(session, end - timedelta(days=4)) == []
    assert await reminders_at(session, end - timedelta(days=3)) == [Reminder.DAYS_3]
    assert await reminders_at(session, end - timedelta(hours=23)) == [Reminder.DAYS_1]
    assert await reminders_at(session, end - timedelta(minutes=59)) == [Reminder.HOUR_1]
    assert await reminders_at(session, end + timedelta(minutes=1)) == [Reminder.EXPIRED]
    assert await reminders_at(session, end + timedelta(minutes=5)) == []


async def test_trial_skips_reminders_that_already_passed(session: AsyncSession) -> None:
    user, _ = await get_or_create_user(session, TelegramProfile(1, None, "U"))
    await extend_subscription(session, FakePanel(), user, 3, is_trial=True, now=NOW)
    assert await reminders_at(session, NOW + timedelta(minutes=1)) == []
    assert await reminders_at(session, NOW + timedelta(days=2, hours=1)) == [Reminder.DAYS_1]


async def test_downtime_sends_only_closest_reminder(session: AsyncSession) -> None:
    user, _ = await get_or_create_user(session, TelegramProfile(1, None, "U"))
    await extend_subscription(session, FakePanel(), user, 30, now=NOW)
    end = NOW + timedelta(days=30)
    assert await reminders_at(session, end - timedelta(hours=12)) == [Reminder.DAYS_1]
    assert await reminders_at(session, end - timedelta(hours=11)) == []


async def test_extension_resets_reminders(session: AsyncSession) -> None:
    user, _ = await get_or_create_user(session, TelegramProfile(1, None, "U"))
    panel = FakePanel()
    await extend_subscription(session, panel, user, 30, now=NOW)
    end = NOW + timedelta(days=30)
    assert await reminders_at(session, end - timedelta(days=5)) == [Reminder.DAYS_5]
    await extend_subscription(session, panel, user, 30, now=end - timedelta(days=5))
    new_end = end + timedelta(days=30)
    assert await reminders_at(session, new_end - timedelta(days=5)) == [Reminder.DAYS_5]


async def test_blocked_users_are_skipped(session: AsyncSession) -> None:
    user, _ = await get_or_create_user(session, TelegramProfile(1, None, "U"))
    await extend_subscription(session, FakePanel(), user, 30, now=NOW)
    user.is_blocked_bot = True
    await session.flush()
    assert await reminders_at(session, NOW + timedelta(days=25)) == []
