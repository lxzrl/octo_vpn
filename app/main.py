import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers import start, subscription
from app.bot.middlewares.db import DbSessionMiddleware
from app.bot.middlewares.user import UserMiddleware
from app.config import Settings, get_settings
from app.db.session import create_engine, create_session_factory
from app.i18n import TranslatorHub
from app.vpn.panel import VpnPanel
from app.vpn.remnawave import RemnawaveClient


def build_dispatcher(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    translators: TranslatorHub,
    panel: VpnPanel,
    storage: BaseStorage | None = None,
) -> Dispatcher:
    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    dp["settings"] = settings
    dp["translators"] = translators
    dp["panel"] = panel
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.update.outer_middleware(UserMiddleware(translators))
    dp.include_router(subscription.create_router())
    # Роутер start последним: в нём заглушка для ещё не готовых разделов меню.
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
    dp = build_dispatcher(
        settings,
        create_session_factory(engine),
        TranslatorHub(settings.default_language),
        panel,
        RedisStorage.from_url(settings.redis_url),
    )
    try:
        await dp.start_polling(bot)
    finally:
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
