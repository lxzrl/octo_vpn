import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BalanceOperation, PromoActivation, PromoCode, PromoKind, User
from app.services.balance import change_balance
from app.services.clock import as_utc, utcnow
from app.services.subscriptions import extend_subscription
from app.vpn.panel import VpnPanel


class PromoError(StrEnum):
    NOT_FOUND = "not-found"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"
    ALREADY_USED = "already-used"
    DISCOUNT_PENDING = "discount-pending"


@dataclass(frozen=True, slots=True)
class PromoApplied:
    kind: PromoKind
    value: int


def normalize(code: str) -> str:
    return code.strip().upper()


async def pending_discount(
    session: AsyncSession, user_id: int
) -> tuple[PromoActivation, int] | None:
    """Скидка по введённому, но ещё не потраченному промокоду: активация и процент."""
    row = (
        await session.execute(
            select(PromoActivation, PromoCode.value)
            .join(PromoCode, PromoCode.id == PromoActivation.promo_id)
            .where(
                PromoActivation.user_id == user_id,
                PromoActivation.used_at.is_(None),
                PromoCode.kind == PromoKind.DISCOUNT,
            )
            .order_by(PromoActivation.id)
            .limit(1)
        )
    ).first()
    return (row[0], int(row[1])) if row else None


async def apply_promo(
    session: AsyncSession, panel: VpnPanel, user: User, raw_code: str
) -> PromoApplied | PromoError:
    """Активирует промокод. Баланс и дни начисляются сразу, скидка ждёт следующей покупки."""
    promo = await session.scalar(
        select(PromoCode).where(func.upper(PromoCode.code) == normalize(raw_code)).with_for_update()
    )
    if promo is None or not promo.is_active:
        return PromoError.NOT_FOUND
    if promo.expires_at is not None and as_utc(promo.expires_at) <= utcnow():
        return PromoError.EXPIRED
    if promo.max_uses is not None and promo.uses >= promo.max_uses:
        return PromoError.EXHAUSTED
    already = await session.scalar(
        select(PromoActivation.id).where(
            PromoActivation.promo_id == promo.id, PromoActivation.user_id == user.id
        )
    )
    if already is not None:
        return PromoError.ALREADY_USED
    if promo.kind == PromoKind.DISCOUNT and await pending_discount(session, user.id):
        return PromoError.DISCOUNT_PENDING

    activation = PromoActivation(promo_id=promo.id, user_id=user.id)
    if promo.kind == PromoKind.DAYS:
        # Сначала панель: если она недоступна, PanelError уйдёт наверх и ничего не запишется.
        await extend_subscription(session, panel, user, promo.value)
        activation.used_at = utcnow()
    elif promo.kind == PromoKind.BALANCE:
        await change_balance(session, user, promo.value, BalanceOperation.PROMO)
        activation.used_at = utcnow()
    session.add(activation)
    await session.execute(
        update(PromoCode).where(PromoCode.id == promo.id).values(uses=PromoCode.uses + 1)
    )
    await session.flush()
    return PromoApplied(PromoKind(promo.kind), promo.value)


CODE = re.compile(r"^[A-Z0-9_-]{3,32}$")
# Без похожих символов (0/O, 1/I), чтобы код было легко ввести руками.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class PromoCodeTaken(Exception):
    pass


def random_code(length: int = 8) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def valid_code(raw: str) -> str | None:
    code = normalize(raw)
    return code if CODE.match(code) else None


async def create_promo(
    session: AsyncSession,
    code: str,
    kind: PromoKind,
    value: int,
    max_uses: int | None,
    expires_at: datetime | None,
) -> PromoCode:
    code = normalize(code)
    taken = await session.scalar(select(PromoCode.id).where(func.upper(PromoCode.code) == code))
    if taken is not None:
        raise PromoCodeTaken(code)
    promo = PromoCode(code=code, kind=kind, value=value, max_uses=max_uses, expires_at=expires_at)
    session.add(promo)
    await session.flush()
    return promo


async def recent_promos(session: AsyncSession, limit: int = 20) -> list[PromoCode]:
    return list(await session.scalars(select(PromoCode).order_by(PromoCode.id.desc()).limit(limit)))
