from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Option
from app.services.options import InvalidOption, OptionKey, load_options, set_option

SETTINGS = Settings(bot_token="1:x", stars_rub_rate="1.5", trial_channel="@octo_news")


async def test_defaults_come_from_settings(session: AsyncSession) -> None:
    options = await load_options(session, SETTINGS)
    assert options.stars_rub_rate == Decimal("1.5")
    assert options.trial_enabled and options.trial_days == 3
    assert options.channel_url == "https://t.me/octo_news"


async def test_saved_values_override_defaults(session: AsyncSession) -> None:
    await set_option(session, OptionKey.STARS_RUB_RATE, "1,8")
    await set_option(session, OptionKey.REFERRAL_FIRST_PERCENT, "25")
    await set_option(session, OptionKey.TRIAL_ENABLED, "0")
    await set_option(session, OptionKey.TRIAL_CHANNEL, "-")
    await set_option(session, OptionKey.STARS_RUB_RATE, "2")

    options = await load_options(session, SETTINGS)
    assert options.stars_rub_rate == Decimal("2")
    assert options.referral_first_percent == 25
    assert not options.trial_enabled
    assert options.trial_channel is None and options.channel_url is None


@pytest.mark.parametrize(
    ("key", "raw"),
    [
        (OptionKey.STARS_RUB_RATE, "0"),
        (OptionKey.STARS_RUB_RATE, "abc"),
        (OptionKey.REFERRAL_NEXT_PERCENT, "101"),
        (OptionKey.TRIAL_DAYS, "0"),
        (OptionKey.TRIAL_CHANNEL, "octo"),
        (OptionKey.TRIAL_CHANNEL_URL, "http://t.me/x"),
    ],
)
async def test_invalid_values_are_rejected(session: AsyncSession, key: OptionKey, raw: str) -> None:
    with pytest.raises(InvalidOption):
        await set_option(session, key, raw)


async def test_broken_row_falls_back_to_default(session: AsyncSession) -> None:
    session.add(Option(key=OptionKey.TRIAL_DAYS.value, value="many"))
    session.add(Option(key="removed_option", value="1"))
    await session.flush()
    assert (await load_options(session, SETTINGS)).trial_days == 3
