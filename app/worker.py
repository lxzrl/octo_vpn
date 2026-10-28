import asyncio
import contextlib
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers.subscription import format_date
from app.bot.keyboards import extend_keyboard, to_subscription_keyboard
from app.bot.notify import AdminNotifier, send
from app.config import Settings
from app.db.models import User
from app.i18n import TranslatorHub
from app.services.payments import (
    cancel_payment,
    expired_pending_payments,
    fulfill_payment,
    unfulfilled_payments,
)
from app.services.reminders import collect_due_reminders
from app.services.subscriptions import get_subscription
from app.vpn.panel import PanelError, VpnPanel

logger = logging.getLogger(__name__)


class BackgroundJobs:
    """Периодические задачи: напоминания, отмена старых счетов, довыдача оплаченного."""

    def __init__(
        self,
        bot: Bot,
        session_factory: async_sessionmaker[AsyncSession],
        panel: VpnPanel,
        translators: TranslatorHub,
        settings: Settings,
        admins: AdminNotifier,
        interval_seconds: float = 60,
    ) -> None:
        self.bot = bot
        self.session_factory = session_factory
        self.panel = panel
        self.translators = translators
        self.settings = settings
        self.admins = admins
        self.interval = interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def run_once(self) -> None:
        for job in (self.cancel_expired_payments, self.retry_fulfillment, self.send_reminders):
            try:
                await job()
            except Exception as error:
                logger.exception("Фоновая задача %s упала", job.__name__)
                await self.admins.error(
                    self.bot,
                    f"job:{job.__name__}",
                    f"Фоновая задача {job.__name__} упала: {error!r}",
                )

    async def cancel_expired_payments(self) -> None:
        async with self.session_factory() as session:
            for payment in await expired_pending_payments(session, self.settings):
                await cancel_payment(session, payment)
            await session.commit()

    async def retry_fulfillment(self) -> None:
        async with self.session_factory() as session:
            for payment in await unfulfilled_payments(session):
                user = await session.get(User, payment.user_id)
                assert user is not None
                try:
                    await fulfill_payment(session, self.panel, payment, user)
                except PanelError as error:
                    logger.warning("Панель всё ещё недоступна, платёж %s ждёт", payment.id)
                    await self.admins.error(
                        self.bot,
                        "panel",
                        f"Панель недоступна: оплаченный платёж #{payment.id} ждёт выдачи ({error})",
                    )
                    return
                await session.commit()
                subscription = await get_subscription(session, user.id)
                assert subscription is not None
                i18n = self.translators.get(user.language)
                await send(
                    self.bot,
                    user,
                    i18n(
                        "payment-success",
                        date=format_date(subscription.expires_at, self.settings),
                    ),
                    to_subscription_keyboard(i18n),
                )
                await session.commit()

    async def send_reminders(self) -> None:
        async with self.session_factory() as session:
            due = await collect_due_reminders(session)
            # Сначала фиксируем «отправлено»: лучше потерять напоминание, чем прислать дважды.
            await session.commit()
            for item in due:
                i18n = self.translators.get(item.user.language)
                await send(
                    self.bot,
                    item.user,
                    i18n(
                        f"reminder-{item.reminder.value}",
                        date=format_date(item.subscription.expires_at, self.settings),
                    ),
                    extend_keyboard(i18n),
                )
            await session.commit()

    async def _loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
