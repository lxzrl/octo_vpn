from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks import LanguageCallback, MenuAction, MenuCallback
from app.i18n import Translator

LANGUAGE_BUTTONS = (("ru", "🇷🇺 Русский"), ("en", "🇬🇧 English"))


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, title in LANGUAGE_BUTTONS:
        builder.button(text=title, callback_data=LanguageCallback(code=code))
    builder.adjust(2)
    return builder.as_markup()


def main_menu_keyboard(i18n: Translator) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for action, key in (
        (MenuAction.SUBSCRIPTION, "btn-subscription"),
        (MenuAction.BUY, "btn-buy"),
        (MenuAction.REFERRALS, "btn-referrals"),
        (MenuAction.SUPPORT, "btn-support"),
        (MenuAction.PROFILE, "btn-profile"),
    ):
        builder.button(text=i18n(key), callback_data=MenuCallback(action=action))
    builder.adjust(1, 1, 2, 1)
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
