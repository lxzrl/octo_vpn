from aiogram.filters import Filter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, TelegramObject
from aiogram.types import User as TgUser
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks import AdminAction, AdminCallback
from app.config import Settings
from app.i18n import Translator


class IsAdmin(Filter):
    """Пропускает только тех, чей Telegram ID указан в ADMIN_IDS."""

    async def __call__(
        self, event: TelegramObject, settings: Settings, event_from_user: TgUser | None = None
    ) -> bool:
        return event_from_user is not None and event_from_user.id in settings.admin_ids


class AdminInput(StatesGroup):
    find_user = State()
    extend_days = State()
    balance = State()
    plan_price = State()
    promo_value = State()
    promo_max_uses = State()
    promo_lifetime = State()
    promo_code = State()
    option = State()
    broadcast = State()
    ticket_reply = State()


def button(
    builder: InlineKeyboardBuilder,
    text: str,
    action: AdminAction,
    id: int = 0,
    value: str = "",
) -> None:
    builder.button(text=text, callback_data=AdminCallback(action=action, id=id, value=value))


def back_keyboard(
    i18n: Translator, action: AdminAction = AdminAction.MENU, id: int = 0
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button(builder, i18n("adm-btn-back"), action, id)
    return builder.as_markup()


def cancel_keyboard(
    i18n: Translator, action: AdminAction = AdminAction.MENU, id: int = 0
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button(builder, i18n("adm-btn-cancel"), action, id)
    return builder.as_markup()
