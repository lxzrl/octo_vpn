import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup

from app.db.models import User

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
