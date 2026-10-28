"""Запросы для админки: поиск пользователя, карточка, аудитория рассылки."""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Payment, PaymentStatus, Subscription, Ticket, User
from app.services.clock import utcnow
from app.services.referrals import ReferralStats, referral_stats
from app.services.subscriptions import get_subscription
from app.services.tickets import open_ticket

USERNAME = re.compile(r"^@?([A-Za-z0-9_]{4,32})$")
AMOUNT = re.compile(r"^[+-]?\d+([.,]\d{1,2})?$")


async def find_user(session: AsyncSession, query: str) -> User | None:
    """Ищет по Telegram ID или @username (без учёта регистра)."""
    query = query.strip()
    if query.isdigit():
        return await session.get(User, int(query))
    match = USERNAME.match(query)
    if match is None:
        return None
    return await session.scalar(
        select(User).where(func.lower(User.username) == match.group(1).lower())
    )


@dataclass(frozen=True, slots=True)
class UserCard:
    user: User
    subscription: Subscription | None
    referrer: User | None
    referrals: ReferralStats
    payments: int
    paid_kop: int
    ticket: Ticket | None


async def user_card(session: AsyncSession, user: User) -> UserCard:
    payments, paid = (
        await session.execute(
            select(func.count(Payment.id), func.coalesce(func.sum(Payment.paid_kop), 0)).where(
                Payment.user_id == user.id, Payment.status == PaymentStatus.PAID
            )
        )
    ).one()
    return UserCard(
        user=user,
        subscription=await get_subscription(session, user.id),
        referrer=await session.get(User, user.referrer_id) if user.referrer_id else None,
        referrals=await referral_stats(session, user.id),
        payments=int(payments),
        paid_kop=int(paid),
        ticket=await open_ticket(session, user.id),
    )


def parse_amount_kop(raw: str) -> int | None:
    """«150», «-50», «+99,90» → копейки. Ноль и мусор — None."""
    raw = raw.strip().replace(" ", "")
    if not AMOUNT.match(raw):
        return None
    try:
        kop = int(Decimal(raw.replace(",", ".")) * 100)
    except InvalidOperation:
        return None
    return kop or None


class Audience(StrEnum):
    ALL = "all"
    ACTIVE = "active"
    INACTIVE = "inactive"


async def audience_ids(
    session: AsyncSession, audience: Audience, now: datetime | None = None
) -> list[int]:
    """Получатели рассылки: без забаненных и заблокировавших бота."""
    now = now or utcnow()
    active = select(Subscription.user_id).where(Subscription.expires_at > now)
    query = select(User.id).where(User.is_banned.is_(False), User.is_blocked_bot.is_(False))
    if audience is Audience.ACTIVE:
        query = query.where(User.id.in_(active))
    elif audience is Audience.INACTIVE:
        query = query.where(User.id.not_in(active))
    return list(await session.scalars(query.order_by(User.id)))
