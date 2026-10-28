"""Настройки, которые админ меняет прямо в боте. Значения по умолчанию берутся из окружения."""

import re
from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Option


class OptionKey(StrEnum):
    STARS_RUB_RATE = "stars_rub_rate"
    REFERRAL_FIRST_PERCENT = "referral_first_percent"
    REFERRAL_NEXT_PERCENT = "referral_next_percent"
    TRIAL_ENABLED = "trial_enabled"
    TRIAL_DAYS = "trial_days"
    TRIAL_CHANNEL = "trial_channel"
    TRIAL_CHANNEL_URL = "trial_channel_url"


@dataclass(frozen=True, slots=True)
class Options:
    stars_rub_rate: Decimal
    referral_first_percent: int
    referral_next_percent: int
    trial_enabled: bool
    trial_days: int
    # Канал для пробного периода: @username или -100…; None = проверка выключена.
    trial_channel: str | None
    trial_channel_url: str | None

    @property
    def channel_url(self) -> str | None:
        if self.trial_channel_url:
            return self.trial_channel_url
        if self.trial_channel and self.trial_channel.startswith("@"):
            return f"https://t.me/{self.trial_channel[1:]}"
        return None


class InvalidOption(ValueError):
    pass


# «-» в поле канала или ссылки выключает его.
EMPTY = "-"
CHANNEL = re.compile(r"^(@[A-Za-z0-9_]{4,32}|-100\d{5,})$")


def _rate(raw: str) -> Decimal:
    try:
        value = Decimal(raw.replace(",", "."))
    except InvalidOperation as error:
        raise InvalidOption(raw) from error
    if not value.is_finite() or value <= 0 or value > 1000:
        raise InvalidOption(raw)
    return value


def _int_range(low: int, high: int) -> Callable[[str], int]:
    def parse(raw: str) -> int:
        if not raw.strip().isdigit() or not low <= int(raw) <= high:
            raise InvalidOption(raw)
        return int(raw)

    return parse


def _bool(raw: str) -> bool:
    if raw not in ("0", "1"):
        raise InvalidOption(raw)
    return raw == "1"


def _channel(raw: str) -> str | None:
    if raw == EMPTY:
        return None
    if not CHANNEL.match(raw):
        raise InvalidOption(raw)
    return raw


def _url(raw: str) -> str | None:
    if raw == EMPTY:
        return None
    if not raw.startswith("https://") or len(raw) > 255:
        raise InvalidOption(raw)
    return raw


PARSERS: dict[OptionKey, Callable[[str], Any]] = {
    OptionKey.STARS_RUB_RATE: _rate,
    OptionKey.REFERRAL_FIRST_PERCENT: _int_range(0, 100),
    OptionKey.REFERRAL_NEXT_PERCENT: _int_range(0, 100),
    OptionKey.TRIAL_ENABLED: _bool,
    OptionKey.TRIAL_DAYS: _int_range(1, 30),
    OptionKey.TRIAL_CHANNEL: _channel,
    OptionKey.TRIAL_CHANNEL_URL: _url,
}


def defaults(settings: Settings) -> Options:
    return Options(
        stars_rub_rate=settings.stars_rub_rate,
        referral_first_percent=settings.referral_first_percent,
        referral_next_percent=settings.referral_next_percent,
        trial_enabled=True,
        trial_days=settings.trial_days,
        trial_channel=settings.trial_channel,
        trial_channel_url=settings.trial_channel_url,
    )


async def load_options(session: AsyncSession, settings: Settings) -> Options:
    options = defaults(settings)
    names = {f.name for f in fields(Options)}
    overrides: dict[str, Any] = {}
    for row in await session.scalars(select(Option)):
        if row.key not in names:
            continue
        try:
            overrides[row.key] = PARSERS[OptionKey(row.key)](row.value)
        except InvalidOption:
            # Испорченное значение в базе не должно ронять бота: остаётся значение по умолчанию.
            continue
    return replace(options, **overrides)


async def set_option(session: AsyncSession, key: OptionKey, raw: str) -> None:
    """Проверяет и сохраняет значение. Неверное значение — InvalidOption."""
    raw = raw.strip()
    PARSERS[key](raw)
    row = await session.get(Option, key.value)
    if row is None:
        session.add(Option(key=key.value, value=raw))
    else:
        row.value = raw
    await session.flush()
