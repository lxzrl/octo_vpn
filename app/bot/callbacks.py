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
    PROMO = "promo"
    SUPPORT_WRITE = "sup_write"
    SUPPORT_CLOSE = "sup_close"
    THEME = "theme"


class MenuCallback(CallbackData, prefix="menu"):
    action: MenuAction


class LanguageCallback(CallbackData, prefix="setlang"):
    code: str


class ThemeCallback(CallbackData, prefix="settheme"):
    theme_id: int
    # Выбор при первом запуске: после него показываем главное меню, а не профиль.
    onboarding: bool = False


class Platform(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    WINDOWS = "windows"
    MACOS = "macos"


class PlatformCallback(CallbackData, prefix="platform"):
    platform: Platform


class PlanCallback(CallbackData, prefix="plan"):
    plan_id: int


class PayCallback(CallbackData, prefix="pay"):
    plan_id: int


class AdminAction(StrEnum):
    MENU = "menu"
    STATS = "stats"
    FIND_USER = "find"
    USER = "user"
    EXTEND = "extend"
    BALANCE = "balance"
    BAN = "ban"
    PLANS = "plans"
    PLAN = "plan"
    PLAN_PRICE = "plan_price"
    PLAN_TOGGLE = "plan_toggle"
    PROMOS = "promos"
    PROMO = "promo"
    PROMO_TOGGLE = "promo_toggle"
    PROMO_NEW = "promo_new"
    PROMO_KIND = "promo_kind"
    PROMO_SKIP = "promo_skip"
    OPTIONS = "options"
    OPTION = "option"
    TRIAL_TOGGLE = "trial_toggle"
    BROADCAST = "bcast"
    BROADCAST_AUDIENCE = "bcast_aud"
    BROADCAST_SEND = "bcast_send"
    TICKETS = "tickets"
    TICKET = "ticket"
    TICKET_REPLY = "ticket_reply"
    TICKET_CLOSE = "ticket_close"
    DESIGN = "design"
    THEME = "theme"
    THEME_NEW = "theme_new"
    THEME_TOGGLE = "theme_tgl"
    THEME_DELETE = "theme_del"
    IMAGE = "image"
    IMAGE_REMOVE = "image_rm"


class AdminCallback(CallbackData, prefix="adm"):
    action: AdminAction
    id: int = 0
    value: str = ""
