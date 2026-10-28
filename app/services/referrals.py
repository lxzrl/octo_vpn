from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BalanceOperation, BalanceTransaction, User


@dataclass(frozen=True, slots=True)
class ReferralStats:
    invited: int
    earned_kop: int


async def referral_stats(session: AsyncSession, user_id: int) -> ReferralStats:
    invited = await session.scalar(select(func.count()).where(User.referrer_id == user_id))
    earned = await session.scalar(
        select(func.coalesce(func.sum(BalanceTransaction.amount_kop), 0)).where(
            BalanceTransaction.user_id == user_id,
            BalanceTransaction.operation == BalanceOperation.REFERRAL,
        )
    )
    return ReferralStats(int(invited or 0), int(earned or 0))
