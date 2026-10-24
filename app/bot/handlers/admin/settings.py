"""Настройки бота: курс звёзд, проценты рефералки, пробный период."""

import html

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import AdminAction, AdminCallback
from app.bot.handlers.admin.common import AdminInput, button, cancel_keyboard
from app.bot.ui import show
from app.config import Settings
from app.i18n import Translator, TranslatorHub
from app.services.options import InvalidOption, OptionKey, Options, load_options, set_option

# Что можно ввести текстом. Пробный период включается и выключается кнопкой.
EDITABLE = (
    OptionKey.STARS_RUB_RATE,
    OptionKey.REFERRAL_FIRST_PERCENT,
    OptionKey.REFERRAL_NEXT_PERCENT,
    OptionKey.TRIAL_DAYS,
    OptionKey.TRIAL_CHANNEL,
    OptionKey.TRIAL_CHANNEL_URL,
)


def options_text(i18n: Translator, options: Options) -> str:
    return i18n(
        "adm-options",
        rate=str(options.stars_rub_rate).replace(".", ","),
        first=options.referral_first_percent,
        next=options.referral_next_percent,
        trial="yes" if options.trial_enabled else "no",
        days=options.trial_days,
        channel=html.escape(options.trial_channel or "—"),
        url=html.escape(options.channel_url or "—"),
    )


def options_keyboard(i18n: Translator, options: Options) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button(
        builder,
        i18n("adm-btn-trial-off" if options.trial_enabled else "adm-btn-trial-on"),
        AdminAction.TRIAL_TOGGLE,
    )
    for key in EDITABLE:
        button(builder, i18n(f"adm-option-{key.value}"), AdminAction.OPTION, value=key)
    button(builder, i18n("adm-btn-back"), AdminAction.MENU)
    builder.adjust(1, 1, 2, 1, 2, 1)
    return builder.as_markup()


async def on_options(callback: CallbackQuery, translators: TranslatorHub, options: Options) -> None:
    i18n = translators.admin
    await show(callback, options_text(i18n, options), options_keyboard(i18n, options))


async def on_trial_toggle(
    callback: CallbackQuery,
    session: AsyncSession,
    translators: TranslatorHub,
    options: Options,
    settings: Settings,
) -> None:
    await set_option(session, OptionKey.TRIAL_ENABLED, "0" if options.trial_enabled else "1")
    options = await load_options(session, settings)
    i18n = translators.admin
    await show(callback, options_text(i18n, options), options_keyboard(i18n, options))


async def on_option(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    key = OptionKey(callback_data.value)
    await state.set_state(AdminInput.option)
    await state.set_data({"key": key.value})
    await show(
        callback, i18n(f"adm-option-prompt-{key.value}"), cancel_keyboard(i18n, AdminAction.OPTIONS)
    )


async def on_option_value(
    message: Message,
    session: AsyncSession,
    translators: TranslatorHub,
    settings: Settings,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    key = OptionKey((await state.get_data())["key"])
    try:
        await set_option(session, key, message.text or "")
    except InvalidOption:
        await message.answer(
            i18n(f"adm-option-prompt-{key.value}"),
            reply_markup=cancel_keyboard(i18n, AdminAction.OPTIONS),
        )
        return
    await state.clear()
    options = await load_options(session, settings)
    text = f"{i18n('adm-option-saved')}\n\n{options_text(i18n, options)}"
    await message.answer(text, reply_markup=options_keyboard(i18n, options))


def create_router() -> Router:
    router = Router(name="admin-settings")
    action = AdminCallback.filter
    router.callback_query.register(on_options, action(F.action == AdminAction.OPTIONS))
    router.callback_query.register(on_trial_toggle, action(F.action == AdminAction.TRIAL_TOGGLE))
    router.callback_query.register(on_option, action(F.action == AdminAction.OPTION))
    router.message.register(
        on_option_value, StateFilter(AdminInput.option), F.text & ~F.text.startswith("/")
    )
    return router
