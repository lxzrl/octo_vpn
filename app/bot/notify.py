import asyncio
import logging
from collections.abc import Iterable
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardMarkup

from app.db.models import User
from app.services.clock import utcnow

logger = logging.getLogger(__name__)


async def send(bot: Bot, user: User, text: str, markup: InlineKeyboardMarkup | None = None) -> bool:
    """Сообщение пользователю по инициативе бота. Заблокировавших бота помечаем и пропускаем."""
    for _ in range(2):
        try:
            await bot.send_message(user.id, text, reply_markup=markup)
            return True
        except TelegramRetryAfter as error:
            await asyncio.sleep(error.retry_after)
        except TelegramForbiddenError:
            user.is_blocked_bot = True
            return False
        except TelegramBadRequest as error:
            logger.warning("Не удалось написать пользователю %s: %s", user.id, error)
            return False
    return False


class AdminNotifier:
    """Сообщения админам: оплаты, обращения, сбои. Сбой одного типа — не чаще раза в полчаса."""

    def __init__(
        self, admin_ids: Iterable[int], error_cooldown: timedelta = timedelta(minutes=30)
    ) -> None:
        self.admin_ids = tuple(admin_ids)
        self.error_cooldown = error_cooldown
        self._last_error: dict[str, datetime] = {}

    async def send(
        self,
        bot: Bot,
        text: str,
        markup: InlineKeyboardMarkup | None = None,
        photo: str | None = None,
    ) -> None:
        for admin_id in self.admin_ids:
            try:
                if photo:
                    await bot.send_photo(admin_id, photo, caption=text, reply_markup=markup)
                else:
                    await bot.send_message(admin_id, text, reply_markup=markup)
            except TelegramAPIError as error:
                logger.warning("Не удалось уведомить админа %s: %s", admin_id, error)

    async def error(self, bot: Bot, key: str, text: str) -> None:
        now = utcnow()
        last = self._last_error.get(key)
        if last is not None and now - last < self.error_cooldown:
            return
        self._last_error[key] = now
        await self.send(bot, f"⚠️ {text}")
