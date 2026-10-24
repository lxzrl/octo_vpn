from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Plan
from app.services.subscriptions import (
    TrialStatus,
    activate_trial,
    active_plans,
    as_utc,
    extend_subscription,
    get_subscription,
    trial_status,
)
from app.services.users import TelegramProfile, get_or_create_user
from app.vpn.panel import PanelError
from tests.fakes import FakePanel

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


async def make_user(session: AsyncSession, user_id: int = 1):  # type: ignore[no-untyped-def]
    user, _ = await get_or_create_user(session, TelegramProfile(user_id, None, "U"))
    return user


async def test_first_extension_creates_panel_user(session: AsyncSession) -> None:
    panel, user = FakePanel(), await make_user(session)
    sub = await extend_subscription(session, panel, user, 30, now=NOW)
    assert as_utc(sub.expires_at) == NOW + timedelta(days=30)
    assert sub.panel_username == "tg_1" and sub.subscription_url.endswith("tg_1")
    assert panel.users[sub.panel_user_id].expire_at == NOW + timedelta(days=30)


async def test_extension_adds_to_remaining_time(session: AsyncSession) -> None:
    panel, user = FakePanel(), await make_user(session)
    await extend_subscription(session, panel, user, 30, now=NOW)
    sub = await extend_subscription(session, panel, user, 90, now=NOW + timedelta(days=10))
    assert as_utc(sub.expires_at) == NOW + timedelta(days=120)
    assert len(panel.users) == 1


async def test_extension_after_expiry_starts_from_now(session: AsyncSession) -> None:
    panel, user = FakePanel(), await make_user(session)
    await extend_subscription(session, panel, user, 30, now=NOW)
    later = NOW + timedelta(days=45)
    sub = await extend_subscription(session, panel, user, 30, now=later)
    assert as_utc(sub.expires_at) == later + timedelta(days=30)


async def test_reuses_panel_user_left_from_failed_attempt(session: AsyncSession) -> None:
    panel, user = FakePanel(), await make_user(session)
    leftover = await panel.create_user("tg_1", 1, NOW)
    sub = await extend_subscription(session, panel, user, 30, now=NOW)
    assert sub.panel_user_id == leftover.id and len(panel.users) == 1


async def test_panel_error_changes_nothing(session: AsyncSession) -> None:
    panel, user = FakePanel(fail=True), await make_user(session)
    with pytest.raises(PanelError):
        await extend_subscription(session, panel, user, 30, now=NOW)
    assert await get_subscription(session, user.id) is None


async def test_trial_only_once(session: AsyncSession) -> None:
    panel, user = FakePanel(), await make_user(session)
    assert await trial_status(session, user) is TrialStatus.AVAILABLE
    sub = await activate_trial(session, panel, user, 3)
    assert sub is not None and sub.is_trial and user.trial_used_at is not None
    assert await activate_trial(session, panel, user, 3) is None
    assert await trial_status(session, user) is TrialStatus.ALREADY_USED


async def test_trial_unavailable_after_purchase(session: AsyncSession) -> None:
    panel, user = FakePanel(), await make_user(session)
    await extend_subscription(session, panel, user, 30)
    assert await trial_status(session, user) is TrialStatus.ALREADY_USED


async def test_failed_trial_can_be_retried(session: AsyncSession) -> None:
    panel, user = FakePanel(fail=True), await make_user(session)
    with pytest.raises(PanelError):
        await activate_trial(session, panel, user, 3)
    assert user.trial_used_at is None
    panel.fail = False
    assert await activate_trial(session, panel, user, 3) is not None


async def test_paid_extension_clears_trial_flag(session: AsyncSession) -> None:
    panel, user = FakePanel(), await make_user(session)
    await activate_trial(session, panel, user, 3)
    sub = await extend_subscription(session, panel, user, 30)
    assert not sub.is_trial


async def test_active_plans_hide_unpriced_and_disabled(session: AsyncSession) -> None:
    session.add_all(
        [
            Plan(months=3, days=90, price_rub=500, sort_order=2),
            Plan(months=1, days=30, price_rub=200, sort_order=1),
            Plan(months=6, days=180, price_rub=None, sort_order=3),
            Plan(months=12, days=365, price_rub=2000, is_active=False, sort_order=4),
        ]
    )
    await session.flush()
    assert [p.months for p in await active_plans(session)] == [1, 3]
