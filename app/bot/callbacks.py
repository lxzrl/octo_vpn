from enum import StrEnum

from aiogram.filters.callback_data import CallbackData


class MenuAction(StrEnum):
    MAIN = "main"
    SUBSCRIPTION = "sub"
    BUY = "buy"
    REFERRALS = "ref"
    SUPPORT = "support"
    PROFILE = "profile"
    LANGUAGE = "lang"


class MenuCallback(CallbackData, prefix="menu"):
    action: MenuAction


class LanguageCallback(CallbackData, prefix="setlang"):
    code: str
