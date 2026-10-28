from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Payment, PaymentStatus, Subscription, User
from app.services.clock import utcnow
from app.services.tickets import count_open_tickets


@dataclass(frozen=True, slots=True)
class Revenue:
    payments: int
    paid_kop: int
    stars: int


@dataclass(frozen=True, slots=True)
class Stats:
    users: int
    users_day: int
    users_week: int
    blocked: int
    active_paid: int
    active_trial: int
    trials_used: int
    revenue_day: Revenue
    revenue_week: Revenue
    revenue_month: Revenue
    revenue_total: Revenue
    balances_kop: int
    open_tickets: int


async def _count(session: AsyncSession, *where: ColumnElement[bool]) -> int:
    return int(await session.scalar(select(func.count()).select_from(User).where(*where)) or 0)


async def _revenue(session: AsyncSession, since: datetime | None) -> Revenue:
    query = select(
        func.count(Payment.id),
        func.coalesce(func.sum(Payment.paid_kop), 0),
        func.coalesce(func.sum(Payment.stars), 0),
    ).where(Payment.status == PaymentStatus.PAID)
    if since is not None:
        query = query.where(Payment.paid_at >= since)
    count, paid, stars = (await session.execute(query)).one()
    return Revenue(int(count), int(paid), int(stars))


async def collect_stats(session: AsyncSession, now: datetime | None = None) -> Stats:
    now = now or utcnow()
    active = select(func.count()).select_from(Subscription).where(Subscription.expires_at > now)
    return Stats(
        users=await _count(session),
        users_day=await _count(session, User.created_at >= now - timedelta(days=1)),
        users_week=await _count(session, User.created_at >= now - timedelta(days=7)),
        blocked=await _count(session, User.is_blocked_bot.is_(True)),
        active_paid=int(await session.scalar(active.where(Subscription.is_trial.is_(False))) or 0),
        active_trial=int(await session.scalar(active.where(Subscription.is_trial.is_(True))) or 0),
        trials_used=await _count(session, User.trial_used_at.is_not(None)),
        revenue_day=await _revenue(session, now - timedelta(days=1)),
        revenue_week=await _revenue(session, now - timedelta(days=7)),
        revenue_month=await _revenue(session, now - timedelta(days=30)),
        revenue_total=await _revenue(session, None),
        balances_kop=int(
            await session.scalar(select(func.coalesce(func.sum(User.balance_kop), 0))) or 0
        ),
        open_tickets=await count_open_tickets(session),
    )
