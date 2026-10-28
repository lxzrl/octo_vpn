import asyncio
import contextlib
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.broadcast import Broadcaster
from app.bot.handlers import admin, buy, referral, start, subscription, support
from app.bot.middlewares.db import DbSessionMiddleware
from app.bot.middlewares.options import OptionsMiddleware
from app.bot.middlewares.theme import ThemeMiddleware
from app.bot.middlewares.user import UserMiddleware
from app.bot.notify import AdminNotifier
from app.config import Settings, get_settings
from app.db.session import create_engine, create_session_factory, prepare_sqlite
from app.i18n import TranslatorHub
from app.vpn.demo import DemoPanel
from app.vpn.panel import VpnPanel
from app.vpn.remnawave import RemnawaveClient
from app.worker import BackgroundJobs


def build_dispatcher(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    translators: TranslatorHub,
    panel: VpnPanel,
    storage: BaseStorage | None = None,
    admins: AdminNotifier | None = None,
    broadcaster: Broadcaster | None = None,
) -> Dispatcher:
    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    dp["settings"] = settings
    dp["translators"] = translators
    dp["panel"] = panel
    dp["admins"] = admins or AdminNotifier(settings.admin_ids)
    dp["broadcaster"] = broadcaster or Broadcaster(session_factory)
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.update.outer_middleware(UserMiddleware(translators))
    dp.update.outer_middleware(OptionsMiddleware(settings))
    dp.update.outer_middleware(ThemeMiddleware())
    # Админка первой: её ввод (ответ на обращение, рассылка) не должен уйти в другие разделы.
    dp.include_router(admin.create_router())
    dp.include_router(subscription.create_router())
    dp.include_router(buy.create_router())
    dp.include_router(referral.create_router())
    dp.include_router(support.create_router())
    dp.include_router(start.create_router())
    return dp


async def set_commands(bot: Bot) -> None:
    """Меню команд в Telegram. /admin не показываем: о нём знают только админы."""
    await bot.set_my_commands([BotCommand(command="start", description="Главное меню")])
    await bot.set_my_commands(
        [BotCommand(command="start", description="Main menu")], language_code="en"
    )


def create_bot(settings: Settings) -> Bot:
    # Прокси нужен, если сервер стоит там, где api.telegram.org заблокирован.
    session = AiohttpSession(proxy=settings.telegram_proxy) if settings.telegram_proxy else None
    return Bot(
        settings.bot_token.get_secret_value(),
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_panel(settings: Settings, http: aiohttp.ClientSession) -> VpnPanel:
    if settings.vpn_panel == "demo":
        return DemoPanel(settings.demo_subscription_url)
    caddy = settings.remnawave_caddy_token
    return RemnawaveClient(
        http,
        settings.remnawave_url,
        settings.remnawave_token.get_secret_value(),
        caddy.get_secret_value() if caddy else None,
        settings.remnawave_squads,
    )


async def run(settings: Settings) -> None:
    engine = create_engine(settings.db_url)
    if engine.dialect.name == "sqlite":
        await prepare_sqlite(engine)
    bot = create_bot(settings)
    http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
    panel = create_panel(settings, http)
    session_factory = create_session_factory(engine)
    translators = TranslatorHub(settings.default_language)
    admins = AdminNotifier(settings.admin_ids)
    dp = build_dispatcher(
        settings,
        session_factory,
        translators,
        panel,
        RedisStorage.from_url(settings.redis_url) if settings.redis_url else MemoryStorage(),
        admins,
    )
    logging.getLogger(__name__).info(
        "Админы (ADMIN_IDS): %s", ", ".join(map(str, sorted(settings.admin_ids))) or "нет"
    )
    jobs = BackgroundJobs(bot, session_factory, panel, translators, settings, admins)
    await set_commands(bot)
    jobs.start()
    try:
        await dp.start_polling(bot)
    finally:
        await jobs.stop()
        await http.close()
        await bot.session.close()
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Ctrl+C — обычная остановка, без трассировки в консоли.
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run(settings))


if __name__ == "__main__":
    main()
