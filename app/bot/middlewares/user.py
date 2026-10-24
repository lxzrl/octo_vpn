from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from aiogram.types import User as TgUser

from app.i18n import TranslatorHub
from app.services.users import TelegramProfile, get_or_create_user, parse_referrer


def _start_payload(event: TelegramObject) -> str | None:
    if isinstance(event, Update) and event.message and event.message.text:
        command, _, payload = event.message.text.partition(" ")
        if command.split("@")[0] == "/start":
            return payload.strip() or None
    return None


def _is_successful_payment(event: TelegramObject) -> bool:
    # Звёзды уже списаны: такой апдейт обрабатываем даже у забаненного.
    return isinstance(event, Update) and bool(event.message and event.message.successful_payment)


class UserMiddleware(BaseMiddleware):
    """Находит или регистрирует пользователя, подставляет язык. Забаненных молча игнорирует."""

    def __init__(self, translators: TranslatorHub) -> None:
        self.translators = translators

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        user, _ = await get_or_create_user(
            data["session"],
            TelegramProfile(tg_user.id, tg_user.username, tg_user.first_name),
            referrer_id=parse_referrer(_start_payload(event)),
        )
        if user.is_banned and not _is_successful_payment(event):
            return None

        data["user"] = user
        data["i18n"] = self.translators.get(user.language or tg_user.language_code)
        return await handler(event, data)
