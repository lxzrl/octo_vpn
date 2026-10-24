"""Тарифы и промокоды."""

from datetime import timedelta

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import AdminAction, AdminCallback
from app.bot.handlers.admin.common import AdminInput, button, cancel_keyboard
from app.bot.handlers.subscription import format_date
from app.bot.ui import show
from app.config import Settings
from app.db.models import Plan, PromoCode, PromoKind
from app.i18n import Translator, TranslatorHub
from app.services.admin import parse_amount_kop
from app.services.clock import utcnow
from app.services.money import rub
from app.services.promo import PromoCodeTaken, create_promo, random_code, recent_promos, valid_code

MAX_PRICE_RUB = 100_000
MAX_DAYS = 3650


# --- Тарифы ---


def plan_title(i18n: Translator, plan: Plan) -> str:
    price = rub(plan.price_rub * 100) if plan.price_rub is not None else i18n("adm-plan-no-price")
    status = "✅" if plan.is_active and plan.price_rub is not None else "⛔"
    return i18n("adm-plan-title", months=plan.months, days=plan.days, price=price, status=status)


async def on_plans(
    callback: CallbackQuery, session: AsyncSession, translators: TranslatorHub
) -> None:
    i18n = translators.admin
    plans = list(await session.scalars(select(Plan).order_by(Plan.sort_order, Plan.months)))
    builder = InlineKeyboardBuilder()
    for plan in plans:
        button(builder, plan_title(i18n, plan), AdminAction.PLAN, plan.id)
    button(builder, i18n("adm-btn-back"), AdminAction.MENU)
    builder.adjust(1)
    await show(callback, i18n("adm-plans"), builder.as_markup())


def plan_keyboard(i18n: Translator, plan: Plan) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button(builder, i18n("adm-btn-plan-price"), AdminAction.PLAN_PRICE, plan.id)
    button(
        builder,
        i18n("adm-btn-plan-hide" if plan.is_active else "adm-btn-plan-show"),
        AdminAction.PLAN_TOGGLE,
        plan.id,
    )
    button(builder, i18n("adm-btn-back"), AdminAction.PLANS)
    builder.adjust(1)
    return builder.as_markup()


def plan_text(i18n: Translator, plan: Plan) -> str:
    return i18n(
        "adm-plan",
        title=plan_title(i18n, plan),
        active="yes" if plan.is_active else "no",
        priced="yes" if plan.price_rub is not None else "no",
    )


async def _plan(
    callback: CallbackQuery, session: AsyncSession, plan_id: int, i18n: Translator
) -> Plan | None:
    plan = await session.get(Plan, plan_id)
    if plan is None:
        await callback.answer(i18n("adm-not-found"), show_alert=True)
    return plan


async def on_plan(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
) -> None:
    i18n = translators.admin
    if plan := await _plan(callback, session, callback_data.id, i18n):
        await show(callback, plan_text(i18n, plan), plan_keyboard(i18n, plan))


async def on_plan_toggle(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
) -> None:
    i18n = translators.admin
    if plan := await _plan(callback, session, callback_data.id, i18n):
        plan.is_active = not plan.is_active
        await session.flush()
        await show(callback, plan_text(i18n, plan), plan_keyboard(i18n, plan))


async def on_plan_price(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    await state.set_state(AdminInput.plan_price)
    await state.update_data(plan_id=callback_data.id)
    await show(
        callback,
        i18n("adm-plan-price-prompt"),
        cancel_keyboard(i18n, AdminAction.PLAN, callback_data.id),
    )


async def on_plan_price_input(
    message: Message, session: AsyncSession, translators: TranslatorHub, state: FSMContext
) -> None:
    i18n = translators.admin
    plan_id = int((await state.get_data())["plan_id"])
    raw = (message.text or "").strip()
    if raw == "-":
        price = None
    elif raw.isdigit() and 1 <= int(raw) <= MAX_PRICE_RUB:
        price = int(raw)
    else:
        await message.answer(
            i18n("adm-plan-price-invalid"),
            reply_markup=cancel_keyboard(i18n, AdminAction.PLAN, plan_id),
        )
        return
    plan = await session.get(Plan, plan_id)
    await state.clear()
    if plan is None:
        await message.answer(i18n("adm-not-found"))
        return
    plan.price_rub = price
    await session.flush()
    await message.answer(plan_text(i18n, plan), reply_markup=plan_keyboard(i18n, plan))


# --- Промокоды ---


def promo_value(i18n: Translator, promo: PromoCode) -> str:
    if promo.kind == PromoKind.DISCOUNT:
        return i18n("adm-promo-value-discount", value=promo.value)
    if promo.kind == PromoKind.BALANCE:
        return i18n("adm-promo-value-balance", value=rub(promo.value))
    return i18n("adm-promo-value-days", value=promo.value)


def promo_text(i18n: Translator, promo: PromoCode, settings: Settings) -> str:
    return i18n(
        "adm-promo",
        code=promo.code,
        value=promo_value(i18n, promo),
        uses=promo.uses,
        max_uses=str(promo.max_uses) if promo.max_uses is not None else "∞",
        expires=format_date(promo.expires_at, settings) if promo.expires_at else "—",
        active="yes" if promo.is_active else "no",
    )


def promo_keyboard(i18n: Translator, promo: PromoCode) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button(
        builder,
        i18n("adm-btn-promo-off" if promo.is_active else "adm-btn-promo-on"),
        AdminAction.PROMO_TOGGLE,
        promo.id,
    )
    button(builder, i18n("adm-btn-back"), AdminAction.PROMOS)
    builder.adjust(1)
    return builder.as_markup()


async def on_promos(
    callback: CallbackQuery, session: AsyncSession, translators: TranslatorHub
) -> None:
    i18n = translators.admin
    builder = InlineKeyboardBuilder()
    button(builder, i18n("adm-btn-promo-new"), AdminAction.PROMO_NEW)
    for promo in await recent_promos(session):
        mark = "✅" if promo.is_active else "⛔"
        button(
            builder,
            f"{mark} {promo.code} · {promo_value(i18n, promo)} · {promo.uses}",
            AdminAction.PROMO,
            promo.id,
        )
    button(builder, i18n("adm-btn-back"), AdminAction.MENU)
    builder.adjust(1)
    await show(callback, i18n("adm-promos"), builder.as_markup())


async def on_promo(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
    settings: Settings,
) -> None:
    i18n = translators.admin
    promo = await session.get(PromoCode, callback_data.id)
    if promo is None:
        await callback.answer(i18n("adm-not-found"), show_alert=True)
        return
    if callback_data.action == AdminAction.PROMO_TOGGLE:
        promo.is_active = not promo.is_active
        await session.flush()
    await show(callback, promo_text(i18n, promo, settings), promo_keyboard(i18n, promo))


async def on_promo_new(callback: CallbackQuery, translators: TranslatorHub) -> None:
    i18n = translators.admin
    builder = InlineKeyboardBuilder()
    for kind in PromoKind:
        button(builder, i18n(f"adm-promo-kind-{kind.value}"), AdminAction.PROMO_KIND, value=kind)
    button(builder, i18n("adm-btn-cancel"), AdminAction.PROMOS)
    builder.adjust(1)
    await show(callback, i18n("adm-promo-choose-kind"), builder.as_markup())


async def on_promo_kind(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    kind = PromoKind(callback_data.value)
    await state.set_state(AdminInput.promo_value)
    await state.set_data({"kind": kind.value})
    await show(
        callback,
        i18n(f"adm-promo-value-prompt-{kind.value}"),
        cancel_keyboard(i18n, AdminAction.PROMOS),
    )


def parse_promo_value(kind: PromoKind, raw: str) -> int | None:
    if kind == PromoKind.BALANCE:
        amount = parse_amount_kop(raw)
        return amount if amount is not None and amount > 0 else None
    if not raw.isdigit():
        return None
    value = int(raw)
    limit = 100 if kind == PromoKind.DISCOUNT else MAX_DAYS
    return value if 1 <= value <= limit else None


def skip_keyboard(i18n: Translator, skip_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button(builder, i18n(skip_key), AdminAction.PROMO_SKIP)
    button(builder, i18n("adm-btn-cancel"), AdminAction.PROMOS)
    builder.adjust(1)
    return builder.as_markup()


# Шаги мастера после ввода значения: состояние, подсказка, кнопка «пропустить».
PROMO_STEPS = (
    (AdminInput.promo_max_uses, "adm-promo-max-uses-prompt", "adm-btn-unlimited"),
    (AdminInput.promo_lifetime, "adm-promo-lifetime-prompt", "adm-btn-no-expiry"),
    (AdminInput.promo_code, "adm-promo-code-prompt", "adm-btn-generate-code"),
)


async def _next_step(
    target: Message, i18n: Translator, state: FSMContext, step: int, *, edit: bool
) -> None:
    next_state, prompt, skip = PROMO_STEPS[step]
    await state.set_state(next_state)
    if edit:
        await target.edit_text(i18n(prompt), reply_markup=skip_keyboard(i18n, skip))
    else:
        await target.answer(i18n(prompt), reply_markup=skip_keyboard(i18n, skip))


async def on_promo_value(message: Message, translators: TranslatorHub, state: FSMContext) -> None:
    i18n = translators.admin
    kind = PromoKind((await state.get_data())["kind"])
    value = parse_promo_value(kind, (message.text or "").strip())
    if value is None:
        await message.answer(
            i18n(f"adm-promo-value-prompt-{kind.value}"),
            reply_markup=cancel_keyboard(i18n, AdminAction.PROMOS),
        )
        return
    await state.update_data(value=value)
    await _next_step(message, i18n, state, 0, edit=False)


async def on_promo_number(message: Message, translators: TranslatorHub, state: FSMContext) -> None:
    """Лимит активаций или срок действия в днях."""
    i18n = translators.admin
    raw = (message.text or "").strip()
    current = await state.get_state()
    step = 0 if current == AdminInput.promo_max_uses.state else 1
    if not raw.isdigit() or not 1 <= int(raw) <= 1_000_000:
        await _next_step(message, i18n, state, step, edit=False)
        return
    await state.update_data({"max_uses" if step == 0 else "lifetime_days": int(raw)})
    await _next_step(message, i18n, state, step + 1, edit=False)


async def on_promo_skip(
    callback: CallbackQuery,
    session: AsyncSession,
    translators: TranslatorHub,
    settings: Settings,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    current = await state.get_state()
    if current == AdminInput.promo_code.state:
        await _finish_promo(callback, session, i18n, settings, state, random_code())
        return
    if current not in (AdminInput.promo_max_uses.state, AdminInput.promo_lifetime.state):
        await callback.answer()
        return
    step = 0 if current == AdminInput.promo_max_uses.state else 1
    assert isinstance(callback.message, Message)
    await _next_step(callback.message, i18n, state, step + 1, edit=True)
    await callback.answer()


async def on_promo_code(
    message: Message,
    session: AsyncSession,
    translators: TranslatorHub,
    settings: Settings,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    code = valid_code(message.text or "")
    if code is None:
        await _next_step(message, i18n, state, 2, edit=False)
        return
    await _finish_promo(message, session, i18n, settings, state, code)


async def _finish_promo(
    event: Message | CallbackQuery,
    session: AsyncSession,
    i18n: Translator,
    settings: Settings,
    state: FSMContext,
    code: str,
) -> None:
    data = await state.get_data()
    lifetime = data.get("lifetime_days")
    try:
        promo = await create_promo(
            session,
            code,
            PromoKind(data["kind"]),
            int(data["value"]),
            data.get("max_uses"),
            utcnow() + timedelta(days=lifetime) if lifetime else None,
        )
    except PromoCodeTaken:
        target = event.message if isinstance(event, CallbackQuery) else event
        assert isinstance(target, Message)
        await target.answer(i18n("adm-promo-code-taken", code=code))
        if isinstance(event, CallbackQuery):
            await event.answer()
        return
    await state.clear()
    text = f"{i18n('adm-promo-created')}\n\n{promo_text(i18n, promo, settings)}"
    if isinstance(event, CallbackQuery):
        await show(event, text, promo_keyboard(i18n, promo))
    else:
        await event.answer(text, reply_markup=promo_keyboard(i18n, promo))


def create_router() -> Router:
    router = Router(name="admin-catalog")
    action = AdminCallback.filter
    text = F.text & ~F.text.startswith("/")
    router.callback_query.register(on_plans, action(F.action == AdminAction.PLANS))
    router.callback_query.register(on_plan, action(F.action == AdminAction.PLAN))
    router.callback_query.register(on_plan_toggle, action(F.action == AdminAction.PLAN_TOGGLE))
    router.callback_query.register(on_plan_price, action(F.action == AdminAction.PLAN_PRICE))
    router.callback_query.register(on_promos, action(F.action == AdminAction.PROMOS))
    router.callback_query.register(
        on_promo, action(F.action.in_({AdminAction.PROMO, AdminAction.PROMO_TOGGLE}))
    )
    router.callback_query.register(on_promo_new, action(F.action == AdminAction.PROMO_NEW))
    router.callback_query.register(on_promo_kind, action(F.action == AdminAction.PROMO_KIND))
    router.callback_query.register(on_promo_skip, action(F.action == AdminAction.PROMO_SKIP))
    router.message.register(on_plan_price_input, StateFilter(AdminInput.plan_price), text)
    router.message.register(on_promo_value, StateFilter(AdminInput.promo_value), text)
    router.message.register(
        on_promo_number,
        StateFilter(AdminInput.promo_max_uses, AdminInput.promo_lifetime),
        text,
    )
    router.message.register(on_promo_code, StateFilter(AdminInput.promo_code), text)
    return router
