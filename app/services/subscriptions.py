from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Plan, Subscription, User
from app.vpn.panel import PanelUser, VpnPanel


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(moment: datetime) -> datetime:
    """SQLite отдаёт даты без часового пояса; в базе всё хранится в UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def panel_username(user_id: int) -> str:
    return f"tg_{user_id}"


def is_active(subscription: Subscription | None, now: datetime | None = None) -> bool:
    return subscription is not None and as_utc(subscription.expires_at) > (now or utcnow())


async def get_subscription(session: AsyncSession, user_id: int) -> Subscription | None:
    return await session.scalar(select(Subscription).where(Subscription.user_id == user_id))


async def extend_subscription(
    session: AsyncSession,
    panel: VpnPanel,
    user: User,
    days: int,
    *,
    is_trial: bool = False,
    now: datetime | None = None,
) -> Subscription:
    """Продлевает доступ на days дней: от текущей даты окончания или от сейчас, если истёк.

    Сначала меняется срок в панели, потом в базе: если панель недоступна, PanelError
    пробрасывается наверх, и в базе ничего не меняется.
    """
    now = now or utcnow()
    subscription = await get_subscription(session, user.id)
    start = max(as_utc(subscription.expires_at), now) if subscription else now
    expires_at = start + timedelta(days=days)

    panel_user: PanelUser
    if subscription is not None:
        panel_user = await panel.update_user(subscription.panel_user_id, expires_at)
    else:
        username = panel_username(user.id)
        # Пользователь мог остаться в панели, если прошлый раз упали после её ответа.
        existing = await panel.get_user_by_username(username)
        if existing is not None:
            panel_user = await panel.update_user(existing.id, expires_at)
        else:
            panel_user = await panel.create_user(username, user.id, expires_at)
        subscription = Subscription(user_id=user.id)
        session.add(subscription)

    subscription.panel_user_id = panel_user.id
    subscription.panel_username = panel_user.username
    subscription.subscription_url = panel_user.subscription_url
    subscription.expires_at = expires_at
    subscription.is_trial = is_trial
    await session.flush()
    return subscription


class TrialStatus(StrEnum):
    AVAILABLE = "available"
    ALREADY_USED = "used"


async def trial_status(session: AsyncSession, user: User) -> TrialStatus:
    if user.trial_used_at is not None or await get_subscription(session, user.id) is not None:
        return TrialStatus.ALREADY_USED
    return TrialStatus.AVAILABLE


async def activate_trial(
    session: AsyncSession, panel: VpnPanel, user: User, days: int
) -> Subscription | None:
    """Выдаёт пробный период, если он ещё не использован. Иначе возвращает None."""
    # Блокируем строку пользователя, чтобы двойное нажатие не выдало триал дважды.
    await session.refresh(user, with_for_update=True)
    if await trial_status(session, user) is not TrialStatus.AVAILABLE:
        return None
    subscription = await extend_subscription(session, panel, user, days, is_trial=True)
    # Отмечаем после успешного ответа панели: при ошибке триал остаётся доступным.
    user.trial_used_at = utcnow()
    return subscription


async def active_plans(session: AsyncSession) -> list[Plan]:
    """Тарифы для магазина: включённые и с заданной ценой."""
    result = await session.scalars(
        select(Plan)
        .where(Plan.is_active, Plan.price_rub.is_not(None))
        .order_by(Plan.sort_order, Plan.months)
    )
    return list(result)
