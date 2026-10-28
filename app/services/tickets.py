from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ticket, TicketMessage, TicketStatus, User
from app.services.clock import utcnow

# Длинные сообщения обрезаем: в Telegram у подписи к фото предел 1024 символа.
MAX_TEXT = 900


async def open_ticket(session: AsyncSession, user_id: int) -> Ticket | None:
    return await session.scalar(
        select(Ticket).where(Ticket.user_id == user_id, Ticket.status == TicketStatus.OPEN)
    )


async def add_user_message(
    session: AsyncSession, user: User, text: str, photo_file_id: str | None = None
) -> tuple[Ticket, bool]:
    """Пишет в открытое обращение или открывает новое. Возвращает обращение и «новое ли оно»."""
    await session.refresh(user, with_for_update=True)
    ticket = await open_ticket(session, user.id)
    created = ticket is None
    if ticket is None:
        ticket = Ticket(user_id=user.id, status=TicketStatus.OPEN)
        session.add(ticket)
        await session.flush()
    ticket.awaiting_reply = True
    ticket.updated_at = utcnow()
    session.add(
        TicketMessage(
            ticket_id=ticket.id,
            author_id=user.id,
            from_admin=False,
            text=text[:MAX_TEXT],
            photo_file_id=photo_file_id,
        )
    )
    await session.flush()
    return ticket, created


async def add_admin_reply(
    session: AsyncSession,
    ticket: Ticket,
    admin_id: int,
    text: str,
    photo_file_id: str | None = None,
) -> None:
    ticket.awaiting_reply = False
    ticket.updated_at = utcnow()
    session.add(
        TicketMessage(
            ticket_id=ticket.id,
            author_id=admin_id,
            from_admin=True,
            text=text[:MAX_TEXT],
            photo_file_id=photo_file_id,
        )
    )
    await session.flush()


def close_ticket(ticket: Ticket) -> None:
    ticket.status = TicketStatus.CLOSED
    ticket.awaiting_reply = False


async def ticket_messages(
    session: AsyncSession, ticket_id: int, limit: int = 10
) -> list[TicketMessage]:
    """Последние сообщения обращения в хронологическом порядке."""
    rows = await session.scalars(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.id.desc())
        .limit(limit)
    )
    return list(reversed(list(rows)))


async def open_tickets(session: AsyncSession, limit: int = 20) -> list[Ticket]:
    """Открытые обращения: сначала ждущие ответа, затем по давности последнего движения."""
    rows = await session.scalars(
        select(Ticket)
        .where(Ticket.status == TicketStatus.OPEN)
        .order_by(Ticket.awaiting_reply.desc(), Ticket.updated_at)
        .limit(limit)
    )
    return list(rows)


async def count_open_tickets(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.status == TicketStatus.OPEN)
        )
        or 0
    )
