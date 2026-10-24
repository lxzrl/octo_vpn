from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from itertools import count
from typing import Any

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageText,
    GetChatMember,
    SendMessage,
    TelegramMethod,
)
from aiogram.methods.base import TelegramType
from aiogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberLeft,
    ChatMemberMember,
    Message,
    Update,
    User,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.callbacks import LanguageCallback, MenuAction, MenuCallback, Platform, PlatformCallback
from app.config import Settings
from app.db.models import Subscription
from app.db.models import User as DbUser
from app.i18n import TranslatorHub
from app.main import build_dispatcher
from tests.fakes import FakePanel

CHAT = Chat(id=100, type="private")
TG_USER = User(id=100, is_bot=False, first_name="Alice", language_code="ru")


class FakeSession(BaseSession):
    """Вместо Telegram API запоминает вызовы бота и возвращает правдоподобные ответы."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.channel_member = False

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
        if isinstance(method, GetChatMember):
            member = ChatMemberMember if self.channel_member else ChatMemberLeft
            return member(user=TG_USER)  # type: ignore[return-value]
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
def settings() -> Settings:
    return Settings(bot_token="42:TEST", trial_channel=None)


@pytest.fixture
def panel() -> FakePanel:
    return FakePanel()


@pytest.fixture
def dp(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession], panel: FakePanel
) -> Dispatcher:
    return build_dispatcher(settings, session_factory, TranslatorHub("ru"), panel)


def menu(action: MenuAction) -> Update:
    return callback(MenuCallback(action=action).pack())


async def registered(dp: Dispatcher, bot: Bot) -> None:
    await dp.feed_update(bot, message("/start"))
    await dp.feed_update(bot, callback(LanguageCallback(code="ru").pack()))


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


async def test_trial_flow(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    panel: FakePanel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await registered(dp, bot)
    await dp.feed_update(bot, menu(MenuAction.SUBSCRIPTION))
    assert "нет подписки" in last_text(fake) and "3 дня" in last_text(fake)

    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    text = last_text(fake)
    assert "Пробный период активирован" in text and "https://sub.example/tg_100" in text
    assert len(panel.users) == 1

    async with session_factory() as session:
        sub = await session.get(Subscription, 1)
        assert sub is not None and sub.is_trial

    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    answer = fake.calls[-1]
    assert isinstance(answer, AnswerCallbackQuery) and answer.show_alert
    assert len(panel.users) == 1


async def test_trial_requires_channel(
    settings: Settings, dp: Dispatcher, bot: Bot, fake: FakeSession, panel: FakePanel
) -> None:
    settings.trial_channel = "@octo_news"
    await registered(dp, bot)

    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    assert "подпишитесь на наш канал" in last_text(fake)
    assert panel.users == {}

    fake.channel_member = True
    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    assert "Пробный период активирован" in last_text(fake)


async def test_trial_when_panel_is_down(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    panel: FakePanel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await registered(dp, bot)
    panel.fail = True
    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    answer = fake.calls[-1]
    assert (
        isinstance(answer, AnswerCallbackQuery)
        and answer.text
        and "попробуйте" in answer.text.lower()
    )

    async with session_factory() as session:
        user = await session.get(DbUser, TG_USER.id)
        assert user is not None and user.trial_used_at is None


async def test_connect_instructions(dp: Dispatcher, bot: Bot, fake: FakeSession) -> None:
    await registered(dp, bot)
    await dp.feed_update(bot, menu(MenuAction.CONNECT))
    assert "Выберите устройство" in last_text(fake)
    await dp.feed_update(bot, callback(PlatformCallback(platform=Platform.ANDROID).pack()))
    assert "Android" in last_text(fake) and "Happ" in last_text(fake)


async def test_expired_subscription_screen(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await registered(dp, bot)
    async with session_factory() as session:
        session.add(
            Subscription(
                user_id=TG_USER.id,
                panel_user_id=1,
                panel_username="tg_100",
                subscription_url="https://sub.example/tg_100",
                expires_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        await session.commit()
    await dp.feed_update(bot, menu(MenuAction.SUBSCRIPTION))
    assert "Подписка закончилась" in last_text(fake) and "01.01.2020" in last_text(fake)
