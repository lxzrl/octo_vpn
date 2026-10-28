import html

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import AdminAction, AdminCallback, MenuAction, MenuCallback
from app.bot.keyboards import cancel_keyboard, support_keyboard
from app.bot.notify import AdminNotifier
from app.bot.ui import show
from app.db.models import TicketMessage, User
from app.i18n import Translator, TranslatorHub
from app.services.themes import Screen, ThemeImages
from app.services.tickets import add_user_message, close_ticket, open_ticket, ticket_messages

# В истории обращения каждое сообщение укорачиваем, чтобы экран влез в лимит Telegram.
HISTORY_SNIPPET = 300


class SupportInput(StatesGroup):
    waiting_message = State()


def snippet(text: str, limit: int = HISTORY_SNIPPET) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def history_text(i18n: Translator, messages: list[TicketMessage], *, for_admin: bool) -> str:
    lines = []
    for item in messages:
        body = html.escape(snippet(item.text))
        if item.photo_file_id:
            body = f"{i18n('support-photo')} {body}".strip()
        if item.from_admin:
            author = i18n("support-author-support")
        else:
            author = i18n("support-author-user" if for_admin else "support-author-you")
        lines.append(f"<b>{author}:</b> {body}")
    return "\n\n".join(lines)


def user_label(user: User) -> str:
    name = html.escape(user.first_name or "—")
    username = f" @{html.escape(user.username)}" if user.username else ""
    return f"{name}{username} (<code>{user.id}</code>)"


def admin_ticket_keyboard(admin_i18n: Translator, ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=admin_i18n("adm-btn-reply"),
        callback_data=AdminCallback(action=AdminAction.TICKET_REPLY, id=ticket_id),
    )
    builder.button(
        text=admin_i18n("adm-btn-open-ticket"),
        callback_data=AdminCallback(action=AdminAction.TICKET, id=ticket_id),
    )
    builder.adjust(2)
    return builder.as_markup()


async def on_support(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    state: FSMContext,
    images: ThemeImages,
) -> None:
    await state.clear()
    image = images.of(Screen.SUPPORT)
    ticket = await open_ticket(session, user.id)
    if ticket is None:
        await show(callback, i18n("support-intro"), support_keyboard(i18n, has_ticket=False), image)
        return
    history = history_text(i18n, await ticket_messages(session, ticket.id), for_admin=False)
    # Длинная переписка не влезет в подпись к фото: тогда show() покажет её текстом.
    await show(
        callback,
        i18n("support-ticket", id=str(ticket.id), history=history),
        support_keyboard(i18n, has_ticket=True),
        image,
    )


async def on_support_write(
    callback: CallbackQuery, i18n: Translator, state: FSMContext, images: ThemeImages
) -> None:
    await state.set_state(SupportInput.waiting_message)
    await show(
        callback,
        i18n("support-write"),
        cancel_keyboard(i18n, MenuAction.SUPPORT),
        images.of(Screen.SUPPORT),
    )


async def on_support_message(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    state: FSMContext,
    translators: TranslatorHub,
    admins: AdminNotifier,
) -> None:
    photo = message.photo[-1].file_id if message.photo else None
    text = (message.text or message.caption or "").strip()
    if not text and not photo:
        await message.answer(i18n("support-empty"))
        return
    ticket, created = await add_user_message(session, user, text, photo)
    await session.commit()
    await state.clear()
    await message.answer(i18n("support-sent"))

    admin_i18n = translators.admin
    key = "adm-ticket-new" if created else "adm-ticket-message"
    header = admin_i18n(key, id=str(ticket.id), user=user_label(user))
    body = html.escape(snippet(text, 800))
    await admins.send(
        bot,
        f"{header}\n\n{body}" if body else header,
        admin_ticket_keyboard(admin_i18n, ticket.id),
        photo=photo,
    )


async def on_support_close(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    translators: TranslatorHub,
    admins: AdminNotifier,
    images: ThemeImages,
) -> None:
    ticket = await open_ticket(session, user.id)
    if ticket is not None:
        close_ticket(ticket)
        notice = translators.admin(
            "adm-ticket-closed-by-user", id=str(ticket.id), user=user_label(user)
        )
        await admins.send(bot, notice)
    await show(
        callback,
        i18n("support-closed"),
        support_keyboard(i18n, has_ticket=False),
        images.of(Screen.SUPPORT),
    )


def create_router() -> Router:
    router = Router(name="support")
    menu = MenuCallback.filter
    router.callback_query.register(on_support, menu(F.action == MenuAction.SUPPORT))
    router.callback_query.register(on_support_write, menu(F.action == MenuAction.SUPPORT_WRITE))
    router.callback_query.register(on_support_close, menu(F.action == MenuAction.SUPPORT_CLOSE))
    router.message.register(
        on_support_message,
        StateFilter(SupportInput.waiting_message),
        ~F.text.startswith("/"),
    )
    return router
