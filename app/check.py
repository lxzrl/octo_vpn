"""Проверка окружения после деплоя: python -m app.check

Проверяет токен бота, базу, Redis, доступ к API панели и права бота в канале пробного периода.
Ничего не меняет. Код выхода 1, если что-то не работает.
"""

import asyncio
import sys

import aiohttp
from aiogram.exceptions import TelegramAPIError
from redis.asyncio import Redis
from sqlalchemy import func, select

from app.config import Settings, get_settings
from app.db.models import User
from app.db.session import create_engine, create_session_factory, prepare_sqlite
from app.main import create_bot, create_panel
from app.services.options import load_options
from app.vpn.panel import PanelError
from app.vpn.remnawave import RemnawaveClient


def report(ok: bool, text: str) -> bool:
    print(f"{'✅' if ok else '❌'} {text}")
    return ok


async def check(settings: Settings) -> bool:
    results = []
    bot = create_bot(settings)
    engine = create_engine(settings.db_url)
    if engine.dialect.name == "sqlite":
        await prepare_sqlite(engine)
    try:
        try:
            me = await bot.get_me()
            results.append(report(True, f"Telegram: бот @{me.username}"))
        except TelegramAPIError as error:
            results.append(report(False, f"Telegram: {error}"))
            me = None
        except Exception as error:  # ошибки прокси (aiohttp_socks) — не TelegramAPIError
            via = f" через {settings.telegram_proxy}" if settings.telegram_proxy else ""
            results.append(report(False, f"Telegram: нет связи{via}: {error!r}"))
            me = None
        results.append(report(bool(settings.admin_ids), f"ADMIN_IDS: {len(settings.admin_ids)}"))

        session_factory = create_session_factory(engine)
        options = None
        try:
            async with session_factory() as session:
                users = await session.scalar(select(func.count()).select_from(User))
                options = await load_options(session, settings)
            results.append(report(True, f"База: пользователей {users}"))
        except Exception as error:
            results.append(report(False, f"База: {error!r}"))

        if settings.redis_url:
            redis = Redis.from_url(settings.redis_url)
            try:
                await redis.ping()
                results.append(report(True, "Redis"))
            except Exception as error:
                results.append(report(False, f"Redis: {error!r}"))
            finally:
                await redis.aclose()
        else:
            print("➖ Redis не задан: состояния диалогов в памяти")

        url = settings.remnawave_url
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as http:
            panel = create_panel(settings, http)
            if not isinstance(panel, RemnawaveClient):
                print("➖ Тестовый режим без панели: всем выдаётся DEMO_SUBSCRIPTION_URL")
                results.append(
                    report(bool(settings.demo_subscription_url), "DEMO_SUBSCRIPTION_URL задан")
                )
            else:
                try:
                    squads = await panel.squad_uuids()
                    # Несуществующий пользователь: проверяем, что токен принимается для users.
                    await panel.get_user_by_username("tg_0")
                    results.append(report(True, f"Панель {url}: сквадов {len(squads)}"))
                except PanelError as error:
                    results.append(report(False, f"Панель {url}: {error}"))

        channel = options.trial_channel if options else settings.trial_channel
        if channel and me is None:
            results.append(report(False, f"Канал {channel}: не проверен, бот не подключился"))
        elif channel and me is not None:
            try:
                member = await bot.get_chat_member(channel, me.id)
                results.append(
                    report(
                        member.status in ("administrator", "creator"),
                        f"Канал {channel}: бот {member.status}, нужен administrator",
                    )
                )
            except TelegramAPIError as error:
                results.append(report(False, f"Канал {channel}: {error}"))
        else:
            print("➖ Канал для пробного периода не задан, проверка подписки выключена")
    finally:
        await bot.session.close()
        await engine.dispose()
    return all(results)


def main() -> None:
    ok = asyncio.run(check(get_settings()))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
