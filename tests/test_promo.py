from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PromoCode, PromoKind, User
from app.services.clock import utcnow
from app.services.promo import PromoApplied, PromoError, apply_promo
from app.services.subscriptions import get_subscription
from app.services.users import TelegramProfile, get_or_create_user
from tests.fakes import FakePanel


async def make_user(session: AsyncSession, user_id: int = 1) -> User:
    user, _ = await get_or_create_user(session, TelegramProfile(user_id, None, "U"))
    return user


async def add_code(session: AsyncSession, **kwargs: object) -> PromoCode:
    promo = PromoCode(**{"code": "CODE", "kind": PromoKind.BALANCE, "value": 10000, **kwargs})
    session.add(promo)
    await session.flush()
    return promo


async def test_balance_code(session: AsyncSession) -> None:
    user = await make_user(session)
    await add_code(session)
    result = await apply_promo(session, FakePanel(), user, " code ")
    assert result == PromoApplied(PromoKind.BALANCE, 10000)
    assert user.balance_kop == 10000
    assert await apply_promo(session, FakePanel(), user, "CODE") is PromoError.ALREADY_USED


async def test_days_code_extends_subscription(session: AsyncSession) -> None:
    user = await make_user(session)
    await add_code(session, kind=PromoKind.DAYS, value=7)
    panel = FakePanel()
    assert isinstance(await apply_promo(session, panel, user, "CODE"), PromoApplied)
    assert await get_subscription(session, user.id) is not None and len(panel.users) == 1


async def test_unknown_expired_and_exhausted(session: AsyncSession) -> None:
    first, second = await make_user(session, 1), await make_user(session, 2)
    await add_code(session, code="OLD", expires_at=utcnow() - timedelta(days=1))
    await add_code(session, code="ONE", max_uses=1)
    await add_code(session, code="OFF", is_active=False)
    panel = FakePanel()
    assert await apply_promo(session, panel, first, "nope") is PromoError.NOT_FOUND
    assert await apply_promo(session, panel, first, "OFF") is PromoError.NOT_FOUND
    assert await apply_promo(session, panel, first, "OLD") is PromoError.EXPIRED
    assert isinstance(await apply_promo(session, panel, first, "ONE"), PromoApplied)
    assert await apply_promo(session, panel, second, "ONE") is PromoError.EXHAUSTED


async def test_only_one_pending_discount(session: AsyncSession) -> None:
    user = await make_user(session)
    await add_code(session, code="A", kind=PromoKind.DISCOUNT, value=10)
    await add_code(session, code="B", kind=PromoKind.DISCOUNT, value=20)
    assert isinstance(await apply_promo(session, FakePanel(), user, "A"), PromoApplied)
    assert await apply_promo(session, FakePanel(), user, "B") is PromoError.DISCOUNT_PENDING
