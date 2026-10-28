from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BalanceOperation, BalanceTransaction, User


class InsufficientBalance(Exception):
    pass


async def change_balance(
    session: AsyncSession,
    user: User,
    amount_kop: int,
    operation: BalanceOperation,
    *,
    payment_id: int | None = None,
    source_user_id: int | None = None,
) -> None:
    """Меняет баланс и пишет запись в журнал. Отрицательная сумма — списание."""
    if amount_kop == 0:
        return
    if user.balance_kop + amount_kop < 0:
        raise InsufficientBalance
    user.balance_kop += amount_kop
    session.add(
        BalanceTransaction(
            user_id=user.id,
            amount_kop=amount_kop,
            operation=operation,
            payment_id=payment_id,
            source_user_id=source_user_id,
        )
    )
    await session.flush()


async def ledger_total(session: AsyncSession, user_id: int) -> int:
    total = await session.scalar(
        select(func.coalesce(func.sum(BalanceTransaction.amount_kop), 0)).where(
            BalanceTransaction.user_id == user_id
        )
    )
    return int(total or 0)
