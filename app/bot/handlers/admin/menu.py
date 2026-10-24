from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import AdminAction, AdminCallback, MenuAction, MenuCallback
from app.bot.handlers.admin.common import back_keyboard, button
from app.bot.ui import show
from app.i18n import Translator, TranslatorHub
from app.services.money import rub
from app.services.stats import Revenue, collect_stats
from app.services.tickets import count_open_tickets


def menu_keyboard(i18n: Translator, open_tickets: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button(builder, i18n("adm-btn-stats"), AdminAction.STATS)
    button(builder, i18n("adm-btn-find-user"), AdminAction.FIND_USER)
    button(builder, i18n("adm-btn-tickets", count=open_tickets), AdminAction.TICKETS)
    button(builder, i18n("adm-btn-plans"), AdminAction.PLANS)
    button(builder, i18n("adm-btn-promos"), AdminAction.PROMOS)
    button(builder, i18n("adm-btn-options"), AdminAction.OPTIONS)
    button(builder, i18n("adm-btn-broadcast"), AdminAction.BROADCAST)
    builder.button(text=i18n("adm-btn-to-bot"), callback_data=MenuCallback(action=MenuAction.MAIN))
    builder.adjust(2, 1, 2, 1, 1, 1)
    return builder.as_markup()


async def cmd_admin(
    message: Message, session: AsyncSession, translators: TranslatorHub, state: FSMContext
) -> None:
    await state.clear()
    i18n = translators.admin
    await message.answer(
        i18n("adm-menu"), reply_markup=menu_keyboard(i18n, await count_open_tickets(session))
    )


async def on_menu(
    callback: CallbackQuery, session: AsyncSession, translators: TranslatorHub
) -> None:
    i18n = translators.admin
    await show(callback, i18n("adm-menu"), menu_keyboard(i18n, await count_open_tickets(session)))


def revenue_line(i18n: Translator, period: str, revenue: Revenue) -> str:
    return i18n(
        "adm-stats-revenue",
        period=i18n(f"adm-period-{period}"),
        count=revenue.payments,
        amount=rub(revenue.paid_kop),
        stars=revenue.stars,
    )


async def on_stats(
    callback: CallbackQuery, session: AsyncSession, translators: TranslatorHub
) -> None:
    i18n = translators.admin
    stats = await collect_stats(session)
    revenue = "\n".join(
        revenue_line(i18n, period, value)
        for period, value in (
            ("day", stats.revenue_day),
            ("week", stats.revenue_week),
            ("month", stats.revenue_month),
            ("total", stats.revenue_total),
        )
    )
    text = i18n(
        "adm-stats",
        users=stats.users,
        users_day=stats.users_day,
        users_week=stats.users_week,
        blocked=stats.blocked,
        active_paid=stats.active_paid,
        active_trial=stats.active_trial,
        trials_used=stats.trials_used,
        revenue=revenue,
        balances=rub(stats.balances_kop),
        tickets=stats.open_tickets,
    )
    await show(callback, text, back_keyboard(i18n))


def create_router() -> Router:
    router = Router(name="admin-menu")
    action = AdminCallback.filter
    router.message.register(cmd_admin, Command("admin"))
    router.callback_query.register(on_menu, action(F.action == AdminAction.MENU))
    router.callback_query.register(on_stats, action(F.action == AdminAction.STATS))
    return router
