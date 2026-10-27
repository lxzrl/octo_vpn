import html
import logging
import math
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import MenuAction, MenuCallback, PlatformCallback
from app.bot.keyboards import (
    channel_keyboard,
    no_subscription_keyboard,
    platform_keyboard,
    platforms_keyboard,
    subscription_keyboard,
)
from app.bot.notify import AdminNotifier
from app.bot.ui import show
from app.config import Settings
from app.db.models import Subscription, User
from app.i18n import Translator
from app.services.channel import ChannelCheckError, is_subscribed
from app.services.clock import as_utc, utcnow
from app.services.options import Options
from app.services.subscriptions import (
    TrialStatus,
    activate_trial,
    get_subscription,
    trial_status,
)
from app.services.themes import Screen, ThemeImages
from app.vpn.panel import PanelError, VpnPanel

logger = logging.getLogger(__name__)


def format_date(moment: datetime, settings: Settings) -> str:
    return as_utc(moment).astimezone(ZoneInfo(settings.display_timezone)).strftime("%d.%m.%Y %H:%M")


def subscription_text(
    i18n: Translator, subscription: Subscription, settings: Settings, header: str = ""
) -> str:
    expires_at = as_utc(subscription.expires_at)
    date = format_date(expires_at, settings)
    left = expires_at - utcnow()
    if left.total_seconds() <= 0:
        body = i18n("subscription-expired", date=date)
    else:
        body = i18n(
            "subscription-trial" if subscription.is_trial else "subscription-active",
            date=date,
            days=math.ceil(left.total_seconds() / 86400),
            url=html.escape(subscription.subscription_url),
        )
    return f"{header}\n\n{body}" if header else body


async def render_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    settings: Settings,
    options: Options,
    images: ThemeImages,
    header: str = "",
) -> None:
    subscription = await get_subscription(session, user.id)
    if subscription is None:
        available = (
            options.trial_enabled and await trial_status(session, user) is TrialStatus.AVAILABLE
        )
        text = i18n(
            "no-subscription-trial" if available else "no-subscription", days=options.trial_days
        )
        await show(
            callback,
            text,
            no_subscription_keyboard(i18n, available),
            images.of(Screen.SUBSCRIPTION),
        )
        return
    active = as_utc(subscription.expires_at) > utcnow()
    await show(
        callback,
        subscription_text(i18n, subscription, settings, header),
        subscription_keyboard(i18n, subscription.subscription_url, active),
        images.of(Screen.SUBSCRIPTION),
    )


async def on_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    settings: Settings,
    options: Options,
    images: ThemeImages,
) -> None:
    await render_subscription(callback, session, user, i18n, settings, options, images)


async def on_trial(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    settings: Settings,
    options: Options,
    panel: VpnPanel,
    admins: AdminNotifier,
    images: ThemeImages,
) -> None:
    if not options.trial_enabled:
        await callback.answer(i18n("trial-disabled"), show_alert=True)
        return
    if await trial_status(session, user) is not TrialStatus.AVAILABLE:
        await callback.answer(i18n("trial-already-used"), show_alert=True)
        return

    if options.trial_channel:
        try:
            subscribed = await is_subscribed(bot, options.trial_channel, user.id)
        except ChannelCheckError:
            await callback.answer(i18n("error-try-later"), show_alert=True)
            return
        if not subscribed:
            await show(
                callback,
                i18n("trial-need-channel", days=options.trial_days),
                channel_keyboard(i18n, options.channel_url),
                images.of(Screen.SUBSCRIPTION),
            )
            return

    try:
        subscription = await activate_trial(session, panel, user, options.trial_days)
    except PanelError as error:
        logger.exception("Не удалось выдать пробный период пользователю %s", user.id)
        await callback.answer(i18n("error-try-later"), show_alert=True)
        await admins.error(bot, "panel", f"Панель недоступна: не выдан пробный период ({error})")
        return
    if subscription is None:
        await callback.answer(i18n("trial-already-used"), show_alert=True)
        return
    await render_subscription(
        callback, session, user, i18n, settings, options, images, header=i18n("trial-activated")
    )


async def on_connect(callback: CallbackQuery, i18n: Translator, images: ThemeImages) -> None:
    await show(
        callback,
        i18n("connect-choose-platform"),
        platforms_keyboard(i18n),
        images.of(Screen.CONNECT),
    )


async def on_platform(
    callback: CallbackQuery, callback_data: PlatformCallback, i18n: Translator, images: ThemeImages
) -> None:
    platform = callback_data.platform
    await show(
        callback,
        i18n(f"connect-{platform.value}"),
        platform_keyboard(i18n, platform),
        images.of(Screen.CONNECT),
    )


def create_router() -> Router:
    router = Router(name="subscription")
    menu = MenuCallback.filter
    router.callback_query.register(on_subscription, menu(F.action == MenuAction.SUBSCRIPTION))
    router.callback_query.register(on_trial, menu(F.action == MenuAction.TRIAL))
    router.callback_query.register(on_connect, menu(F.action == MenuAction.CONNECT))
    router.callback_query.register(on_platform, PlatformCallback.filter())
    return router
