from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import Settings
from app.services.options import load_options


class OptionsMiddleware(BaseMiddleware):
    """Подставляет настройки из админки: изменения действуют сразу, без перезапуска."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["options"] = await load_options(data["session"], self.settings)
        return await handler(event, data)
