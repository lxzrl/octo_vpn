import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers import start
from app.bot.middlewares.db import DbSessionMiddleware
from app.bot.middlewares.user import UserMiddleware
from app.config import Settings, get_settings
from app.db.session import create_engine, create_session_factory
from app.i18n import TranslatorHub


def build_dispatcher(
    session_factory: async_sessionmaker[AsyncSession],
    translators: TranslatorHub,
    storage: BaseStorage | None = None,
) -> Dispatcher:
    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    dp["translators"] = translators
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.update.outer_middleware(UserMiddleware(translators))
    dp.include_router(start.create_router())
    return dp


async def run(settings: Settings) -> None:
    engine = create_engine(settings.db_url)
    bot = Bot(
        settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher(
        create_session_factory(engine),
        TranslatorHub(settings.default_language),
        RedisStorage.from_url(settings.redis_url),
    )
    try:
        await dp.start_polling(bot)
    finally:
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
