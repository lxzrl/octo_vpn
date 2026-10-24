import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.users import (
    TelegramProfile,
    get_or_create_user,
    parse_referrer,
    referral_link,
    set_language,
)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [("ref_123", 123), ("ref_", None), ("ref_12a", None), ("promo", None), (None, None)],
)
def test_parse_referrer(payload: str | None, expected: int | None) -> None:
    assert parse_referrer(payload) == expected


def test_referral_link() -> None:
    assert referral_link("octo_bot", 7) == "https://t.me/octo_bot?start=ref_7"


async def test_creates_user_once(session: AsyncSession) -> None:
    profile = TelegramProfile(1, "alice", "Alice")
    user, created = await get_or_create_user(session, profile)
    assert created and user.language is None and user.created_at is not None

    user, created = await get_or_create_user(session, TelegramProfile(1, "alice2", "Alice"))
    assert not created and user.username == "alice2"


async def test_referrer_saved_only_if_exists(session: AsyncSession) -> None:
    await get_or_create_user(session, TelegramProfile(1, None, "Ref"))
    invited, _ = await get_or_create_user(session, TelegramProfile(2, None, "B"), referrer_id=1)
    unknown, _ = await get_or_create_user(session, TelegramProfile(3, None, "C"), referrer_id=999)
    itself, _ = await get_or_create_user(session, TelegramProfile(4, None, "D"), referrer_id=4)
    assert invited.referrer_id == 1
    assert unknown.referrer_id is None
    assert itself.referrer_id is None


async def test_referrer_not_overwritten_for_existing_user(session: AsyncSession) -> None:
    await get_or_create_user(session, TelegramProfile(1, None, "Ref"))
    user, _ = await get_or_create_user(session, TelegramProfile(2, None, "B"))
    user, _ = await get_or_create_user(session, TelegramProfile(2, None, "B"), referrer_id=1)
    assert user.referrer_id is None


async def test_set_language(session: AsyncSession) -> None:
    user, _ = await get_or_create_user(session, TelegramProfile(1, None, "A"))
    assert set_language(user, "en") == "en"
    with pytest.raises(ValueError):
        set_language(user, "de")
