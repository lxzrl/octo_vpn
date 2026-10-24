import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import MenuAction, MenuCallback, PayCallback, PlanCallback
from app.bot.handlers.subscription import format_date
from app.bot.handlers.support import user_label
from app.bot.keyboards import (
    cancel_keyboard,
    checkout_keyboard,
    plans_keyboard,
    to_subscription_keyboard,
)
from app.bot.notify import AdminNotifier, send
from app.bot.ui import show
from app.config import Settings
from app.db.models import Payment, PaymentProvider, Plan, PromoKind, User
from app.i18n import Translator, TranslatorHub
from app.services.money import rub
from app.services.options import Options
from app.services.payments import (
    ReferralReward,
    can_checkout,
    complete_stars_payment,
    create_payment,
    fulfill_payment,
    make_quote,
    parse_payload,
    payload,
)
from app.services.promo import PromoApplied, apply_promo, pending_discount
from app.services.subscriptions import active_plans, get_subscription
from app.vpn.panel import PanelError, VpnPanel

logger = logging.getLogger(__name__)


class PromoInput(StatesGroup):
    waiting_code = State()


async def buy_screen_text(
    session: AsyncSession, user: User, i18n: Translator, has_plans: bool
) -> str:
    lines = [i18n("buy-title") if has_plans else i18n("buy-no-plans")]
    discount = await pending_discount(session, user.id)
    if discount:
        lines.append(i18n("buy-discount-pending", percent=discount[1]))
    if user.balance_kop:
        lines.append(i18n("buy-balance", balance=rub(user.balance_kop)))
    return "\n\n".join(lines)


async def on_buy(
    callback: CallbackQuery, session: AsyncSession, user: User, i18n: Translator, state: FSMContext
) -> None:
    await state.clear()
    plans = await active_plans(session)
    await show(
        callback,
        await buy_screen_text(session, user, i18n, bool(plans)),
        plans_keyboard(i18n, plans),
    )


async def on_plan(
    callback: CallbackQuery,
    callback_data: PlanCallback,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    options: Options,
) -> None:
    plan = await session.get(Plan, callback_data.plan_id)
    if plan is None or not plan.is_active or plan.price_rub is None:
        await callback.answer(i18n("plan-unavailable"), show_alert=True)
        return
    quote = await make_quote(session, user, plan, options.stars_rub_rate)
    lines = [
        i18n("checkout-plan", plan=i18n("plan-name", months=plan.months)),
        i18n("checkout-price", price=rub(quote.price_kop)),
    ]
    if quote.discount_kop:
        lines.append(
            i18n(
                "checkout-discount", percent=quote.discount_percent, amount=rub(quote.discount_kop)
            )
        )
    if quote.balance_used_kop:
        lines.append(i18n("checkout-balance", amount=rub(quote.balance_used_kop)))
    if quote.to_pay_kop:
        lines.append(i18n("checkout-total-stars", amount=rub(quote.to_pay_kop), stars=quote.stars))
    else:
        lines.append(i18n("checkout-total-balance"))
    await show(callback, "\n".join(lines), checkout_keyboard(i18n, plan.id, quote.stars))


async def finish_payment(
    bot: Bot,
    session: AsyncSession,
    panel: VpnPanel,
    payment: Payment,
    user: User,
    i18n: Translator,
    settings: Settings,
    reward: ReferralReward | None,
    translators: TranslatorHub,
    admins: AdminNotifier,
) -> None:
    """После фиксации оплаты: продлить подписку и сообщить пользователю и пригласившему."""
    # Оплата уже записана; сохраняем её до обращения к панели, чтобы не потерять при сбое.
    await session.commit()
    plan = await session.get(Plan, payment.plan_id)
    await admins.send(
        bot,
        translators.admin(
            "adm-payment",
            id=str(payment.id),
            user=user_label(user),
            plan=translators.admin("plan-name", months=plan.months) if plan else "—",
            price=rub(payment.price_kop),
            paid=rub(payment.paid_kop),
            stars=payment.stars if payment.provider == PaymentProvider.STARS else 0,
            balance=rub(payment.balance_used_kop),
            discount=rub(payment.discount_kop),
        ),
    )
    if reward is not None:
        referrer_i18n = translators.get(reward.referrer.language)
        await send(
            bot,
            reward.referrer,
            referrer_i18n("referral-reward", amount=rub(reward.amount_kop)),
        )
    try:
        await fulfill_payment(session, panel, payment, user)
    except PanelError as error:
        logger.exception("Оплата %s получена, но панель не продлила подписку", payment.id)
        await bot.send_message(user.id, i18n("payment-delayed"))
        await admins.error(
            bot, "panel", f"Панель недоступна: платёж #{payment.id} оплачен, но не выдан ({error})"
        )
        return
    await session.commit()
    subscription = await get_subscription(session, user.id)
    assert subscription is not None
    await bot.send_message(
        user.id,
        i18n("payment-success", date=format_date(subscription.expires_at, settings)),
        reply_markup=to_subscription_keyboard(i18n),
    )


async def on_pay(
    callback: CallbackQuery,
    callback_data: PayCallback,
    bot: Bot,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    settings: Settings,
    options: Options,
    panel: VpnPanel,
    translators: TranslatorHub,
    admins: AdminNotifier,
) -> None:
    plan = await session.get(Plan, callback_data.plan_id)
    if plan is None or not plan.is_active or plan.price_rub is None:
        await callback.answer(i18n("plan-unavailable"), show_alert=True)
        return
    payment = await create_payment(session, user, plan, options)
    await callback.answer()
    if payment.provider == PaymentProvider.BALANCE:
        await finish_payment(
            bot, session, panel, payment, user, i18n, settings, None, translators, admins
        )
        return
    plan_name = i18n("plan-name", months=plan.months)
    await bot.send_invoice(
        chat_id=user.id,
        title=i18n("invoice-title", plan=plan_name),
        description=i18n("invoice-description", plan=plan_name),
        payload=payload(payment),
        currency="XTR",
        prices=[LabeledPrice(label=plan_name, amount=payment.stars)],
    )


async def on_pre_checkout(
    query: PreCheckoutQuery, session: AsyncSession, user: User, i18n: Translator, settings: Settings
) -> None:
    ok = await can_checkout(
        session, parse_payload(query.invoice_payload), user.id, query.total_amount, settings
    )
    if ok:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message=i18n("invoice-outdated"))


async def on_successful_payment(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    settings: Settings,
    options: Options,
    panel: VpnPanel,
    translators: TranslatorHub,
    admins: AdminNotifier,
) -> None:
    paid = message.successful_payment
    assert paid is not None
    result = await complete_stars_payment(
        session,
        parse_payload(paid.invoice_payload),
        user,
        paid.telegram_payment_charge_id,
        options,
    )
    if result is None:
        logger.warning("Повторное или неизвестное подтверждение оплаты: %s", paid.invoice_payload)
        return
    payment, reward = result
    await finish_payment(
        bot, session, panel, payment, user, i18n, settings, reward, translators, admins
    )


async def on_promo(callback: CallbackQuery, i18n: Translator, state: FSMContext) -> None:
    await state.set_state(PromoInput.waiting_code)
    await show(callback, i18n("promo-enter"), cancel_keyboard(i18n, MenuAction.BUY))


async def on_promo_code(
    message: Message,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    state: FSMContext,
    panel: VpnPanel,
) -> None:
    try:
        result = await apply_promo(session, panel, user, message.text or "")
    except PanelError:
        logger.exception("Не удалось применить промокод для %s", user.id)
        await message.answer(i18n("error-try-later"))
        return
    if not isinstance(result, PromoApplied):
        await message.answer(
            i18n(f"promo-error-{result.value}"), reply_markup=cancel_keyboard(i18n, MenuAction.BUY)
        )
        return
    await state.clear()
    if result.kind == PromoKind.DISCOUNT:
        text = i18n("promo-discount", percent=result.value)
    elif result.kind == PromoKind.BALANCE:
        text = i18n("promo-balance", amount=rub(result.value))
    else:
        text = i18n("promo-days", days=result.value)
    await message.answer(text, reply_markup=to_subscription_keyboard(i18n))


def create_router() -> Router:
    router = Router(name="buy")
    menu = MenuCallback.filter
    router.callback_query.register(on_buy, menu(F.action == MenuAction.BUY))
    router.callback_query.register(on_promo, menu(F.action == MenuAction.PROMO))
    router.callback_query.register(on_plan, PlanCallback.filter())
    router.callback_query.register(on_pay, PayCallback.filter())
    router.pre_checkout_query.register(on_pre_checkout)
    router.message.register(on_successful_payment, F.successful_payment)
    router.message.register(
        on_promo_code, StateFilter(PromoInput.waiting_code), F.text, ~F.text.startswith("/")
    )
    return router
