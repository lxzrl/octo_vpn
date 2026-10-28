from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.services.themes import images_for


class ThemeMiddleware(BaseMiddleware):
    """Подставляет картинки темы, которую выбрал пользователь."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["images"] = await images_for(data["session"], data.get("user"))
        return await handler(event, data)
