import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import AdminAction, AdminCallback
from app.bot.handlers.admin.common import AdminInput, back_keyboard, button, cancel_keyboard
from app.bot.handlers.subscription import format_date
from app.bot.handlers.support import user_label
from app.bot.notify import send
from app.bot.ui import show
from app.config import Settings
from app.db.models import BalanceOperation, User
from app.i18n import Translator, TranslatorHub
from app.services.admin import UserCard, find_user, parse_amount_kop, user_card
from app.services.balance import InsufficientBalance, change_balance
from app.services.clock import as_utc, utcnow
from app.services.money import rub
from app.services.subscriptions import extend_subscription
from app.vpn.panel import PanelError, VpnPanel

logger = logging.getLogger(__name__)

MAX_EXTEND_DAYS = 3650


def card_text(i18n: Translator, card: UserCard, settings: Settings) -> str:
    user = card.user
    subscription = card.subscription
    if subscription is None:
        sub = i18n("adm-user-no-sub")
    else:
        key = (
            "adm-user-sub-active"
            if as_utc(subscription.expires_at) > utcnow()
            else "adm-user-sub-expired"
        )
        sub = i18n(
            key,
            date=format_date(subscription.expires_at, settings),
            trial="yes" if subscription.is_trial else "no",
        )
    flags = []
    if user.is_banned:
        flags.append(i18n("adm-user-banned"))
    if user.is_blocked_bot:
        flags.append(i18n("adm-user-blocked-bot"))
    return i18n(
        "adm-user-card",
        user=user_label(user),
        language=user.language or "—",
        registered=format_date(user.created_at, settings),
        subscription=sub,
        trial=format_date(user.trial_used_at, settings) if user.trial_used_at else "—",
        balance=rub(user.balance_kop),
        payments=card.payments,
        paid=rub(card.paid_kop),
        referrer=user_label(card.referrer) if card.referrer else "—",
        invited=card.referrals.invited,
        earned=rub(card.referrals.earned_kop),
        ticket=f"#{card.ticket.id}" if card.ticket else "—",
        flags="\n".join(flags),
    )


def card_keyboard(i18n: Translator, card: UserCard) -> InlineKeyboardMarkup:
    user_id = card.user.id
    builder = InlineKeyboardBuilder()
    button(builder, i18n("adm-btn-extend"), AdminAction.EXTEND, user_id)
    button(builder, i18n("adm-btn-balance"), AdminAction.BALANCE, user_id)
    if card.ticket:
        button(builder, i18n("adm-btn-open-ticket"), AdminAction.TICKET, card.ticket.id)
    button(
        builder,
        i18n("adm-btn-unban" if card.user.is_banned else "adm-btn-ban"),
        AdminAction.BAN,
        user_id,
    )
    button(builder, i18n("adm-btn-back"), AdminAction.MENU)
    builder.adjust(2, 1)
    return builder.as_markup()


async def render_card(
    session: AsyncSession, user: User, i18n: Translator, settings: Settings
) -> tuple[str, InlineKeyboardMarkup]:
    card = await user_card(session, user)
    return card_text(i18n, card, settings), card_keyboard(i18n, card)


async def on_find(callback: CallbackQuery, translators: TranslatorHub, state: FSMContext) -> None:
    i18n = translators.admin
    await state.set_state(AdminInput.find_user)
    await show(callback, i18n("adm-find-user"), cancel_keyboard(i18n))


async def on_find_query(
    message: Message,
    session: AsyncSession,
    translators: TranslatorHub,
    settings: Settings,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    user = await find_user(session, message.text or "")
    if user is None:
        await message.answer(i18n("adm-user-not-found"), reply_markup=cancel_keyboard(i18n))
        return
    await state.clear()
    text, markup = await render_card(session, user, i18n, settings)
    await message.answer(text, reply_markup=markup)


async def _target(
    callback: CallbackQuery, session: AsyncSession, user_id: int, i18n: Translator
) -> User | None:
    user = await session.get(User, user_id)
    if user is None:
        await callback.answer(i18n("adm-user-not-found"), show_alert=True)
    return user


async def on_user(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
    settings: Settings,
) -> None:
    i18n = translators.admin
    user = await _target(callback, session, callback_data.id, i18n)
    if user is not None:
        await show(callback, *await render_card(session, user, i18n, settings))


async def on_ban(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
    settings: Settings,
) -> None:
    i18n = translators.admin
    user = await _target(callback, session, callback_data.id, i18n)
    if user is None:
        return
    if user.id in settings.admin_ids:
        await callback.answer(i18n("adm-cannot-ban-admin"), show_alert=True)
        return
    user.is_banned = not user.is_banned
    await session.flush()
    await show(callback, *await render_card(session, user, i18n, settings))


async def on_extend(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    await state.set_state(AdminInput.extend_days)
    await state.update_data(user_id=callback_data.id)
    await show(
        callback,
        i18n("adm-extend-prompt"),
        cancel_keyboard(i18n, AdminAction.USER, callback_data.id),
    )


async def on_extend_days(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    translators: TranslatorHub,
    settings: Settings,
    state: FSMContext,
    panel: VpnPanel,
) -> None:
    i18n = translators.admin
    user_id = int((await state.get_data())["user_id"])
    raw = (message.text or "").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= MAX_EXTEND_DAYS:
        await message.answer(
            i18n("adm-extend-invalid"),
            reply_markup=cancel_keyboard(i18n, AdminAction.USER, user_id),
        )
        return
    user = await session.get(User, user_id)
    if user is None:
        await state.clear()
        await message.answer(i18n("adm-user-not-found"), reply_markup=back_keyboard(i18n))
        return
    try:
        subscription = await extend_subscription(session, panel, user, int(raw))
    except PanelError:
        logger.exception("Админ не смог продлить подписку %s", user_id)
        await message.answer(
            i18n("adm-panel-error"), reply_markup=cancel_keyboard(i18n, AdminAction.USER, user_id)
        )
        return
    await state.clear()
    await session.commit()
    date = format_date(subscription.expires_at, settings)
    user_i18n = translators.get(user.language)
    await send(bot, user, user_i18n("admin-extended", days=int(raw), date=date))
    text, markup = await render_card(session, user, i18n, settings)
    await message.answer(f"{i18n('adm-extend-done', date=date)}\n\n{text}", reply_markup=markup)


async def on_balance(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    await state.set_state(AdminInput.balance)
    await state.update_data(user_id=callback_data.id)
    await show(
        callback,
        i18n("adm-balance-prompt"),
        cancel_keyboard(i18n, AdminAction.USER, callback_data.id),
    )


async def on_balance_amount(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    translators: TranslatorHub,
    settings: Settings,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    user_id = int((await state.get_data())["user_id"])
    amount = parse_amount_kop(message.text or "")
    cancel = cancel_keyboard(i18n, AdminAction.USER, user_id)
    if amount is None:
        await message.answer(i18n("adm-balance-invalid"), reply_markup=cancel)
        return
    user = await session.get(User, user_id, with_for_update=True)
    if user is None:
        await state.clear()
        await message.answer(i18n("adm-user-not-found"), reply_markup=back_keyboard(i18n))
        return
    try:
        await change_balance(session, user, amount, BalanceOperation.ADMIN)
    except InsufficientBalance:
        await message.answer(
            i18n("adm-balance-insufficient", balance=rub(user.balance_kop)), reply_markup=cancel
        )
        return
    await state.clear()
    await session.commit()
    if amount > 0:
        user_i18n = translators.get(user.language)
        await send(bot, user, user_i18n("admin-balance-added", amount=rub(amount)))
    text, markup = await render_card(session, user, i18n, settings)
    done = i18n("adm-balance-done", balance=rub(user.balance_kop))
    await message.answer(f"{done}\n\n{text}", reply_markup=markup)


def create_router() -> Router:
    router = Router(name="admin-users")
    action = AdminCallback.filter
    text = F.text & ~F.text.startswith("/")
    router.callback_query.register(on_find, action(F.action == AdminAction.FIND_USER))
    router.callback_query.register(on_user, action(F.action == AdminAction.USER))
    router.callback_query.register(on_ban, action(F.action == AdminAction.BAN))
    router.callback_query.register(on_extend, action(F.action == AdminAction.EXTEND))
    router.callback_query.register(on_balance, action(F.action == AdminAction.BALANCE))
    router.message.register(on_find_query, StateFilter(AdminInput.find_user), text)
    router.message.register(on_extend_days, StateFilter(AdminInput.extend_days), text)
    router.message.register(on_balance_amount, StateFilter(AdminInput.balance), text)
    return router
