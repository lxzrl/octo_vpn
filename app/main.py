import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.broadcast import Broadcaster
from app.bot.handlers import admin, buy, referral, start, subscription, support
from app.bot.middlewares.db import DbSessionMiddleware
from app.bot.middlewares.options import OptionsMiddleware
from app.bot.middlewares.user import UserMiddleware
from app.bot.notify import AdminNotifier
from app.config import Settings, get_settings
from app.db.session import create_engine, create_session_factory
from app.i18n import TranslatorHub
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
    # Админка первой: её ввод (ответ на обращение, рассылка) не должен уйти в другие разделы.
    dp.include_router(admin.create_router())
    dp.include_router(subscription.create_router())
    dp.include_router(buy.create_router())
    dp.include_router(referral.create_router())
    dp.include_router(support.create_router())
    dp.include_router(start.create_router())
    return dp


async def run(settings: Settings) -> None:
    engine = create_engine(settings.db_url)
    bot = Bot(
        settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
    panel = RemnawaveClient(
        http,
        settings.remnawave_url,
        settings.remnawave_token.get_secret_value(),
        settings.remnawave_caddy_token.get_secret_value()
        if settings.remnawave_caddy_token
        else None,
        settings.remnawave_squads,
    )
    session_factory = create_session_factory(engine)
    translators = TranslatorHub(settings.default_language)
    admins = AdminNotifier(settings.admin_ids)
    dp = build_dispatcher(
        settings,
        session_factory,
        translators,
        panel,
        RedisStorage.from_url(settings.redis_url),
        admins,
    )
    jobs = BackgroundJobs(bot, session_factory, panel, translators, settings, admins)
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
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
