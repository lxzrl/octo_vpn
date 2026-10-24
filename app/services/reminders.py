from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Subscription, User
from app.services.clock import as_utc, utcnow


class Reminder(StrEnum):
    DAYS_5 = "5d"
    DAYS_3 = "3d"
    DAYS_1 = "1d"
    HOUR_1 = "1h"
    EXPIRED = "expired"


# Порядок важен: от дальнего к ближнему. Номер бита в Subscription.reminders_sent = индекс.
BEFORE_END: tuple[tuple[Reminder, timedelta], ...] = (
    (Reminder.DAYS_5, timedelta(days=5)),
    (Reminder.DAYS_3, timedelta(days=3)),
    (Reminder.DAYS_1, timedelta(days=1)),
    (Reminder.HOUR_1, timedelta(hours=1)),
)
EXPIRED_BIT = 1 << len(BEFORE_END)


def bits_already_passed(remaining: timedelta) -> int:
    """Напоминания, время которых уже прошло к моменту продления: их не шлём.

    Например, после триала на 3 дня не нужно сразу писать «осталось 5 дней».
    """
    mask = 0
    for index, (_, before) in enumerate(BEFORE_END):
        if remaining <= before:
            mask |= 1 << index
    return mask if remaining > timedelta(0) else mask | EXPIRED_BIT


def next_reminder(subscription: Subscription, now: datetime) -> tuple[Reminder, int] | None:
    """Какое напоминание отправить сейчас и новая маска. Шлём только самое близкое."""
    remaining = as_utc(subscription.expires_at) - now
    sent = subscription.reminders_sent
    if remaining <= timedelta(0):
        if sent & EXPIRED_BIT:
            return None
        return Reminder.EXPIRED, bits_already_passed(remaining)
    due = bits_already_passed(remaining)
    if due & ~sent == 0:
        return None
    closest = max(i for i in range(len(BEFORE_END)) if due & (1 << i) and not sent & (1 << i))
    return BEFORE_END[closest][0], sent | due


@dataclass(frozen=True, slots=True)
class DueReminder:
    subscription: Subscription
    user: User
    reminder: Reminder


async def collect_due_reminders(
    session: AsyncSession, now: datetime | None = None
) -> list[DueReminder]:
    """Находит напоминания к отправке и сразу помечает их отправленными."""
    now = now or utcnow()
    rows = await session.execute(
        select(Subscription, User)
        .join(User, User.id == Subscription.user_id)
        .where(
            Subscription.expires_at <= now + BEFORE_END[0][1],
            # Про давно закончившиеся подписки не пишем (например, после простоя бота).
            Subscription.expires_at > now - timedelta(days=1),
            User.is_banned.is_(False),
            User.is_blocked_bot.is_(False),
        )
    )
    due: list[DueReminder] = []
    for subscription, user in rows:
        found = next_reminder(subscription, now)
        if found is None:
            continue
        reminder, mask = found
        subscription.reminders_sent = mask
        due.append(DueReminder(subscription, user, reminder))
    await session.flush()
    return due
