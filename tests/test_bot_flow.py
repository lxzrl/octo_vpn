from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from itertools import count
from typing import Any

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.callbacks import LanguageCallback, MenuAction, MenuCallback
from app.db.models import User as DbUser
from app.i18n import TranslatorHub
from app.main import build_dispatcher

CHAT = Chat(id=100, type="private")
TG_USER = User(id=100, is_bot=False, first_name="Alice", language_code="ru")


class FakeSession(BaseSession):
    """Вместо Telegram API запоминает вызовы бота и возвращает правдоподобные ответы."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []

    # Сигнатура задана BaseSession, поэтому timeout оставляем.
    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,  # noqa: ASYNC109
    ) -> TelegramType:
        self.calls.append(method)
        if isinstance(method, SendMessage | EditMessageText):
            return Message(  # type: ignore[return-value]
                message_id=1, date=datetime.now(UTC), chat=CHAT, text=method.text
            )
        return True  # type: ignore[return-value]

    async def stream_content(self, *args: Any, **kwargs: Any) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError
        yield b""

    async def close(self) -> None:
        pass


ids = count(1)


def message(text: str, from_user: User = TG_USER) -> Update:
    return Update(
        update_id=next(ids),
        message=Message(
            message_id=next(ids), date=datetime.now(UTC), chat=CHAT, from_user=from_user, text=text
        ),
    )


def callback(data: str, from_user: User = TG_USER) -> Update:
    return Update(
        update_id=next(ids),
        callback_query=CallbackQuery(
            id=str(next(ids)),
            from_user=from_user,
            chat_instance="x",
            data=data,
            message=Message(message_id=1, date=datetime.now(UTC), chat=CHAT, text="old"),
        ),
    )


@pytest.fixture
def fake() -> FakeSession:
    return FakeSession()


@pytest.fixture
def bot(fake: FakeSession) -> Bot:
    return Bot("42:TEST", session=fake)


@pytest.fixture
def dp(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    return build_dispatcher(session_factory, TranslatorHub("ru"))


def last_text(fake: FakeSession) -> str:
    sent = [c for c in fake.calls if isinstance(c, SendMessage | EditMessageText)]
    return sent[-1].text


async def test_first_start_asks_language_then_shows_menu(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await dp.feed_update(bot, message("/start"))
    assert "Выберите язык" in last_text(fake)

    await dp.feed_update(bot, callback(LanguageCallback(code="en").pack()))
    assert "Hi, Alice" in last_text(fake)

    async with session_factory() as session:
        user = await session.get(DbUser, TG_USER.id)
        assert user is not None and user.language == "en"

    await dp.feed_update(bot, message("/start"))
    assert "Hi, Alice" in last_text(fake)


async def test_change_language_from_profile(dp: Dispatcher, bot: Bot, fake: FakeSession) -> None:
    await dp.feed_update(bot, message("/start"))
    await dp.feed_update(bot, callback(LanguageCallback(code="ru").pack()))
    await dp.feed_update(bot, callback(MenuCallback(action=MenuAction.PROFILE).pack()))
    assert "Профиль" in last_text(fake) and "Русский" in last_text(fake)

    await dp.feed_update(bot, callback(MenuCallback(action=MenuAction.LANGUAGE).pack()))
    await dp.feed_update(bot, callback(LanguageCallback(code="en").pack()))
    assert "Profile" in last_text(fake) and "English" in last_text(fake)


async def test_referral_start_payload(
    dp: Dispatcher, bot: Bot, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session:
        session.add(DbUser(id=7, first_name="Ref"))
        await session.commit()

    await dp.feed_update(bot, message("/start ref_7"))

    async with session_factory() as session:
        user = await session.get(DbUser, TG_USER.id)
        assert user is not None and user.referrer_id == 7


async def test_banned_user_is_ignored(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session:
        session.add(DbUser(id=TG_USER.id, first_name="Alice", is_banned=True))
        await session.commit()

    await dp.feed_update(bot, message("/start"))
    assert fake.calls == []


async def test_unfinished_sections_answer_with_alert(
    dp: Dispatcher, bot: Bot, fake: FakeSession
) -> None:
    await dp.feed_update(bot, message("/start"))
    await dp.feed_update(bot, callback(MenuCallback(action=MenuAction.BUY).pack()))
    answer = fake.calls[-1]
    assert isinstance(answer, AnswerCallbackQuery) and answer.show_alert


async def test_name_with_html_chars_is_escaped(dp: Dispatcher, bot: Bot, fake: FakeSession) -> None:
    user = User(id=101, is_bot=False, first_name="<Bob & Co>")
    await dp.feed_update(bot, message("/start", user))
    await dp.feed_update(bot, callback(LanguageCallback(code="en").pack(), user))
    assert "&lt;Bob &amp; Co&gt;" in last_text(fake)
