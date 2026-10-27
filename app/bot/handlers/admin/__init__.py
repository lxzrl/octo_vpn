"""Админка в боте. Доступна только пользователям из ADMIN_IDS; тексты только на русском."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, TelegramObject

from app.bot.callbacks import AdminAction, AdminCallback
from app.bot.handlers.admin import broadcast, catalog, design, menu, settings, tickets, users
from app.bot.handlers.admin.common import AdminInput, IsAdmin

# Кнопки, которые продолжают начатый ввод: на них состояние не сбрасывается.
KEEP_STATE = frozenset({AdminAction.PROMO_SKIP})


class ResetInputMiddleware(BaseMiddleware):
    """Нажатие любой кнопки, кроме продолжающих ввод, отменяет незавершённый ввод в админке."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext | None = data.get("state")
        if isinstance(event, CallbackQuery) and state is not None:
            current = await state.get_state()
            if current in AdminInput.__all_states_names__ and _action(event) not in KEEP_STATE:
                await state.clear()
        return await handler(event, data)


def _action(callback: CallbackQuery) -> AdminAction | None:
    try:
        return AdminCallback.unpack(callback.data or "").action
    except (TypeError, ValueError):
        return None


def create_router() -> Router:
    router = Router(name="admin")
    router.message.filter(IsAdmin())
    router.callback_query.filter(IsAdmin())
    router.callback_query.outer_middleware(ResetInputMiddleware())
    for module in (menu, users, catalog, settings, design, broadcast, tickets):
        router.include_router(module.create_router())
    return router
