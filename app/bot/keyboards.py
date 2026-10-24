from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks import (
    AdminAction,
    AdminCallback,
    LanguageCallback,
    MenuAction,
    MenuCallback,
    PayCallback,
    PlanCallback,
    Platform,
    PlatformCallback,
)
from app.db.models import Plan
from app.i18n import Translator
from app.services.money import rub

LANGUAGE_BUTTONS = (("ru", "🇷🇺 Русский"), ("en", "🇬🇧 English"))

# Рекомендуемый клиент — Happ: есть на всех платформах и умеет импорт подписки.
APP_LINKS = {
    Platform.IOS: "https://apps.apple.com/app/happ-proxy-utility/id6504287215",
    Platform.MACOS: "https://apps.apple.com/app/happ-proxy-utility/id6504287215",
    Platform.ANDROID: "https://github.com/Happ-proxy/happ-android/releases/latest",
    Platform.WINDOWS: "https://github.com/Happ-proxy/happ-desktop/releases/latest",
}


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, title in LANGUAGE_BUTTONS:
        builder.button(text=title, callback_data=LanguageCallback(code=code))
    builder.adjust(2)
    return builder.as_markup()


def main_menu_keyboard(i18n: Translator, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for action, key in (
        (MenuAction.SUBSCRIPTION, "btn-subscription"),
        (MenuAction.BUY, "btn-buy"),
        (MenuAction.REFERRALS, "btn-referrals"),
        (MenuAction.SUPPORT, "btn-support"),
        (MenuAction.PROFILE, "btn-profile"),
    ):
        builder.button(text=i18n(key), callback_data=MenuCallback(action=action))
    if is_admin:
        builder.button(text=i18n("btn-admin"), callback_data=AdminCallback(action=AdminAction.MENU))
    builder.adjust(1, 1, 2, 1, 1)
    return builder.as_markup()


def back_keyboard(i18n: Translator) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n("btn-back"), callback_data=MenuCallback(action=MenuAction.MAIN))
    return builder.as_markup()


def profile_keyboard(i18n: Translator) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=i18n("btn-change-language"), callback_data=MenuCallback(action=MenuAction.LANGUAGE)
    )
    builder.button(text=i18n("btn-back"), callback_data=MenuCallback(action=MenuAction.MAIN))
    builder.adjust(1)
    return builder.as_markup()


def _menu_button(
    builder: InlineKeyboardBuilder, i18n: Translator, key: str, action: MenuAction
) -> None:
    builder.button(text=i18n(key), callback_data=MenuCallback(action=action))


def no_subscription_keyboard(i18n: Translator, trial_available: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if trial_available:
        _menu_button(builder, i18n, "btn-trial", MenuAction.TRIAL)
    _menu_button(builder, i18n, "btn-buy", MenuAction.BUY)
    _menu_button(builder, i18n, "btn-back", MenuAction.MAIN)
    builder.adjust(1)
    return builder.as_markup()


def subscription_keyboard(
    i18n: Translator, subscription_url: str, active: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if active:
        _menu_button(builder, i18n, "btn-connect", MenuAction.CONNECT)
        builder.button(text=i18n("btn-subscription-page"), url=subscription_url)
    _menu_button(builder, i18n, "btn-extend", MenuAction.BUY)
    _menu_button(builder, i18n, "btn-back", MenuAction.MAIN)
    builder.adjust(1)
    return builder.as_markup()


def channel_keyboard(i18n: Translator, channel_url: str | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if channel_url:
        builder.button(text=i18n("btn-open-channel"), url=channel_url)
    _menu_button(builder, i18n, "btn-check-subscription", MenuAction.TRIAL)
    _menu_button(builder, i18n, "btn-back", MenuAction.SUBSCRIPTION)
    builder.adjust(1)
    return builder.as_markup()


def platforms_keyboard(i18n: Translator) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for platform in Platform:
        builder.button(
            text=i18n(f"platform-{platform.value}"),
            callback_data=PlatformCallback(platform=platform),
        )
    _menu_button(builder, i18n, "btn-back", MenuAction.SUBSCRIPTION)
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def platform_keyboard(i18n: Translator, platform: Platform) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n("btn-download-app"), url=APP_LINKS[platform])
    _menu_button(builder, i18n, "btn-back", MenuAction.CONNECT)
    builder.adjust(1)
    return builder.as_markup()


def plans_keyboard(i18n: Translator, plans: list[Plan]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        assert plan.price_rub is not None
        builder.button(
            text=i18n(
                "btn-plan",
                plan=i18n("plan-name", months=plan.months),
                price=rub(plan.price_rub * 100),
            ),
            callback_data=PlanCallback(plan_id=plan.id),
        )
    _menu_button(builder, i18n, "btn-promo", MenuAction.PROMO)
    _menu_button(builder, i18n, "btn-back", MenuAction.MAIN)
    builder.adjust(1)
    return builder.as_markup()


def checkout_keyboard(i18n: Translator, plan_id: int, stars: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    text = i18n("btn-pay-stars", stars=stars) if stars else i18n("btn-pay-balance")
    builder.button(text=text, callback_data=PayCallback(plan_id=plan_id))
    _menu_button(builder, i18n, "btn-back", MenuAction.BUY)
    builder.adjust(1)
    return builder.as_markup()


def to_subscription_keyboard(i18n: Translator) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _menu_button(builder, i18n, "btn-subscription", MenuAction.SUBSCRIPTION)
    return builder.as_markup()


def extend_keyboard(i18n: Translator) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _menu_button(builder, i18n, "btn-extend", MenuAction.BUY)
    return builder.as_markup()


def cancel_keyboard(i18n: Translator, back_to: MenuAction) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _menu_button(builder, i18n, "btn-cancel", back_to)
    return builder.as_markup()


def referral_keyboard(i18n: Translator, share_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n("btn-share"), url=share_url)
    _menu_button(builder, i18n, "btn-back", MenuAction.MAIN)
    builder.adjust(1)
    return builder.as_markup()


def support_keyboard(i18n: Translator, has_ticket: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_ticket:
        _menu_button(builder, i18n, "btn-support-write", MenuAction.SUPPORT_WRITE)
        _menu_button(builder, i18n, "btn-support-close", MenuAction.SUPPORT_CLOSE)
    else:
        _menu_button(builder, i18n, "btn-support-new", MenuAction.SUPPORT_WRITE)
    _menu_button(builder, i18n, "btn-back", MenuAction.MAIN)
    builder.adjust(1)
    return builder.as_markup()


def support_reply_keyboard(i18n: Translator) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _menu_button(builder, i18n, "btn-support-reply", MenuAction.SUPPORT_WRITE)
    return builder.as_markup()
