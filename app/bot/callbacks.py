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
    TRIAL = "trial"
    CONNECT = "connect"


class MenuCallback(CallbackData, prefix="menu"):
    action: MenuAction


class LanguageCallback(CallbackData, prefix="setlang"):
    code: str


class Platform(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    WINDOWS = "windows"
    MACOS = "macos"


class PlatformCallback(CallbackData, prefix="platform"):
    platform: Platform
