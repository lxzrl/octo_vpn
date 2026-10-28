import html

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import AdminAction, AdminCallback
from app.bot.handlers.admin.common import AdminInput, button, cancel_keyboard
from app.bot.handlers.support import history_text, user_label
from app.bot.keyboards import support_reply_keyboard
from app.bot.notify import send
from app.bot.ui import show
from app.db.models import Ticket, TicketStatus, User
from app.i18n import Translator, TranslatorHub
from app.services.tickets import add_admin_reply, close_ticket, open_tickets, ticket_messages


async def on_tickets(
    callback: CallbackQuery, session: AsyncSession, translators: TranslatorHub
) -> None:
    i18n = translators.admin
    tickets = await open_tickets(session)
    builder = InlineKeyboardBuilder()
    for ticket in tickets:
        user = await session.get(User, ticket.user_id)
        name = user.first_name if user else str(ticket.user_id)
        mark = "🔴" if ticket.awaiting_reply else "⚪"
        button(builder, f"{mark} #{ticket.id} · {name}", AdminAction.TICKET, ticket.id)
    button(builder, i18n("adm-btn-back"), AdminAction.MENU)
    builder.adjust(1)
    text = i18n("adm-tickets") if tickets else i18n("adm-tickets-empty")
    await show(callback, text, builder.as_markup())


def ticket_keyboard(i18n: Translator, ticket: Ticket) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if ticket.status == TicketStatus.OPEN:
        button(builder, i18n("adm-btn-reply"), AdminAction.TICKET_REPLY, ticket.id)
        button(builder, i18n("adm-btn-close-ticket"), AdminAction.TICKET_CLOSE, ticket.id)
    button(builder, i18n("adm-btn-user-card"), AdminAction.USER, ticket.user_id)
    button(builder, i18n("adm-btn-back"), AdminAction.TICKETS)
    builder.adjust(2, 1, 1)
    return builder.as_markup()


async def ticket_view(
    session: AsyncSession, ticket: Ticket, i18n: Translator
) -> tuple[str, InlineKeyboardMarkup]:
    user = await session.get(User, ticket.user_id)
    history = history_text(i18n, await ticket_messages(session, ticket.id), for_admin=True)
    text = i18n(
        "adm-ticket",
        id=str(ticket.id),
        user=user_label(user) if user else str(ticket.user_id),
        status=ticket.status,
        history=history,
    )
    return text, ticket_keyboard(i18n, ticket)


async def _ticket(
    callback: CallbackQuery, session: AsyncSession, ticket_id: int, i18n: Translator
) -> Ticket | None:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        await callback.answer(i18n("adm-not-found"), show_alert=True)
    return ticket


async def on_ticket(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
) -> None:
    i18n = translators.admin
    if ticket := await _ticket(callback, session, callback_data.id, i18n):
        await show(callback, *await ticket_view(session, ticket, i18n))


async def on_ticket_reply(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    ticket = await _ticket(callback, session, callback_data.id, i18n)
    if ticket is None:
        return
    if ticket.status != TicketStatus.OPEN:
        await callback.answer(i18n("adm-ticket-already-closed"), show_alert=True)
        return
    await state.set_state(AdminInput.ticket_reply)
    await state.set_data({"ticket_id": ticket.id})
    assert callback.message is not None
    await callback.message.answer(
        i18n("adm-ticket-reply-prompt", id=str(ticket.id)),
        reply_markup=cancel_keyboard(i18n, AdminAction.TICKET, ticket.id),
    )
    await callback.answer()


async def on_ticket_reply_message(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    ticket = await session.get(Ticket, int((await state.get_data())["ticket_id"]))
    await state.clear()
    if ticket is None or ticket.status != TicketStatus.OPEN:
        await message.answer(i18n("adm-ticket-already-closed"))
        return
    photo = message.photo[-1].file_id if message.photo else None
    text = (message.text or message.caption or "").strip()
    if not text and not photo:
        await message.answer(i18n("adm-ticket-empty"))
        return
    assert message.from_user is not None
    await add_admin_reply(session, ticket, message.from_user.id, text, photo)
    user = await session.get(User, ticket.user_id)
    assert user is not None
    user_i18n = translators.get(user.language)
    reply = user_i18n("support-reply", id=str(ticket.id), text=html.escape(text))
    if photo:
        try:
            await bot.send_photo(
                user.id, photo, caption=reply, reply_markup=support_reply_keyboard(user_i18n)
            )
            delivered = True
        except TelegramAPIError:
            delivered = False
    else:
        delivered = await send(bot, user, reply, support_reply_keyboard(user_i18n))
    view, markup = await ticket_view(session, ticket, i18n)
    status = i18n("adm-ticket-reply-sent" if delivered else "adm-ticket-reply-failed")
    await message.answer(f"{status}\n\n{view}", reply_markup=markup)


async def on_ticket_close(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    bot: Bot,
    session: AsyncSession,
    translators: TranslatorHub,
) -> None:
    i18n = translators.admin
    ticket = await _ticket(callback, session, callback_data.id, i18n)
    if ticket is None:
        return
    if ticket.status == TicketStatus.OPEN:
        close_ticket(ticket)
        await session.flush()
        user = await session.get(User, ticket.user_id)
        if user is not None:
            user_i18n = translators.get(user.language)
            await send(bot, user, user_i18n("support-closed-by-admin", id=str(ticket.id)))
    text, markup = await ticket_view(session, ticket, i18n)
    await show(callback, text, markup)


def create_router() -> Router:
    router = Router(name="admin-tickets")
    action = AdminCallback.filter
    router.callback_query.register(on_tickets, action(F.action == AdminAction.TICKETS))
    router.callback_query.register(on_ticket, action(F.action == AdminAction.TICKET))
    router.callback_query.register(on_ticket_reply, action(F.action == AdminAction.TICKET_REPLY))
    router.callback_query.register(on_ticket_close, action(F.action == AdminAction.TICKET_CLOSE))
    router.message.register(
        on_ticket_reply_message, StateFilter(AdminInput.ticket_reply), ~F.text.startswith("/")
    )
    return router
