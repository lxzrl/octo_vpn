import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import User

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BroadcastReport:
    total: int
    delivered: int
    blocked: int
    failed: int


class Broadcaster:
    """Рассылки в фоне: копирует сообщение админа каждому получателю с паузой под лимиты."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        delay_seconds: float = 0.05,
    ) -> None:
        self.session_factory = session_factory
        self.delay = delay_seconds
        self._tasks: set[asyncio.Task[None]] = set()
        # Уже запущенные сообщения: повторное нажатие «Отправить» не дублирует рассылку.
        self._started: set[tuple[int, int]] = set()

    def start(
        self,
        bot: Bot,
        user_ids: list[int],
        from_chat_id: int,
        message_id: int,
        on_done: Callable[[BroadcastReport], Awaitable[None]],
    ) -> bool:
        if (from_chat_id, message_id) in self._started:
            return False
        self._started.add((from_chat_id, message_id))

        async def job() -> None:
            report = await self.run(bot, user_ids, from_chat_id, message_id)
            await on_done(report)

        task = asyncio.create_task(job())
        # Держим ссылку, иначе задачу может собрать сборщик мусора.
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return True

    async def run(
        self, bot: Bot, user_ids: list[int], from_chat_id: int, message_id: int
    ) -> BroadcastReport:
        delivered = failed = 0
        blocked: list[int] = []
        for user_id in user_ids:
            for attempt in range(2):
                try:
                    await bot.copy_message(user_id, from_chat_id, message_id)
                    delivered += 1
                except TelegramRetryAfter as error:
                    if attempt == 0:
                        await asyncio.sleep(error.retry_after)
                        continue
                    failed += 1
                except TelegramForbiddenError:
                    blocked.append(user_id)
                except TelegramAPIError as error:
                    logger.warning("Рассылка не дошла до %s: %s", user_id, error)
                    failed += 1
                break
            await asyncio.sleep(self.delay)
        if blocked:
            async with self.session_factory() as session:
                await session.execute(
                    update(User).where(User.id.in_(blocked)).values(is_blocked_bot=True)
                )
                await session.commit()
        return BroadcastReport(len(user_ids), delivered, len(blocked), failed)

    async def join(self) -> None:
        """Дождаться всех запущенных рассылок (для тестов и остановки бота)."""
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
