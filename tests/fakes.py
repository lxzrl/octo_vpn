from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import count
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import (
    CopyMessage,
    EditMessageText,
    GetChatMember,
    GetMe,
    SendInvoice,
    SendMessage,
    SendPhoto,
    TelegramMethod,
)
from aiogram.methods.base import TelegramType
from aiogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberLeft,
    ChatMemberMember,
    Message,
    MessageId,
    PhotoSize,
    Update,
    User,
)

from app.vpn.panel import PanelError, PanelUser


@dataclass
class FakePanel:
    """Панель в памяти: хранит пользователей и может имитировать недоступность."""

    users: dict[int, PanelUser] = field(default_factory=dict)
    fail: bool = False
    ids: count[int] = field(default_factory=lambda: count(1))

    def _check(self) -> None:
        if self.fail:
            raise PanelError("panel is down")

    async def get_user_by_username(self, username: str) -> PanelUser | None:
        self._check()
        return next((u for u in self.users.values() if u.username == username), None)

    async def create_user(self, username: str, telegram_id: int, expire_at: datetime) -> PanelUser:
        self._check()
        user_id = next(self.ids)
        user = PanelUser(user_id, username, f"https://sub.example/{username}", expire_at, "ACTIVE")
        self.users[user_id] = user
        return user

    async def update_user(self, user_id: int, expire_at: datetime) -> PanelUser:
        self._check()
        old = self.users[user_id]
        user = PanelUser(user_id, old.username, old.subscription_url, expire_at, "ACTIVE")
        self.users[user_id] = user
        return user


CHAT = Chat(id=100, type="private")
TG_USER = User(id=100, is_bot=False, first_name="Alice", language_code="ru")


class FakeSession(BaseSession):
    """Вместо Telegram API запоминает вызовы бота и возвращает правдоподобные ответы."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.channel_member = False
        # Чаты, где бот заблокирован: отправка в них падает с Forbidden.
        self.blocked: set[int] = set()

    # Сигнатура задана BaseSession, поэтому timeout оставляем.
    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,  # noqa: ASYNC109
    ) -> TelegramType:
        self.calls.append(method)
        chat_id = getattr(method, "chat_id", None)
        if chat_id in self.blocked:
            raise TelegramForbiddenError(method, "bot was blocked by the user")
        if isinstance(method, SendMessage | EditMessageText):
            return Message(  # type: ignore[return-value]
                message_id=1, date=datetime.now(UTC), chat=CHAT, text=method.text
            )
        if isinstance(method, SendInvoice):
            return Message(  # type: ignore[return-value]
                message_id=1, date=datetime.now(UTC), chat=CHAT, text=method.title
            )
        if isinstance(method, SendPhoto):
            return Message(  # type: ignore[return-value]
                message_id=1, date=datetime.now(UTC), chat=CHAT, caption=method.caption
            )
        if isinstance(method, CopyMessage):
            return MessageId(message_id=1)  # type: ignore[return-value]
        if isinstance(method, GetMe):
            return User(id=1, is_bot=True, first_name="Octo", username="octo_bot")  # type: ignore[return-value]
        if isinstance(method, GetChatMember):
            member = ChatMemberMember if self.channel_member else ChatMemberLeft
            return member(user=TG_USER)  # type: ignore[return-value]
        return True  # type: ignore[return-value]

    async def stream_content(self, *args: Any, **kwargs: Any) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError
        yield b""

    async def close(self) -> None:
        pass


def sent_to(session: FakeSession, chat_id: int) -> list[str]:
    """Тексты сообщений (и подписи к фото), которые бот отправил в чат."""
    texts = []
    for call in session.calls:
        if isinstance(call, SendMessage) and call.chat_id == chat_id:
            texts.append(call.text)
        elif isinstance(call, SendPhoto) and call.chat_id == chat_id:
            texts.append(call.caption or "")
    return texts


ids = count(1)


def message(text: str, from_user: User = TG_USER) -> Update:
    return Update(
        update_id=next(ids),
        message=Message(
            message_id=next(ids),
            date=datetime.now(UTC),
            chat=Chat(id=from_user.id, type="private"),
            from_user=from_user,
            text=text,
        ),
    )


def photo(caption: str | None, from_user: User = TG_USER) -> Update:
    return Update(
        update_id=next(ids),
        message=Message(
            message_id=next(ids),
            date=datetime.now(UTC),
            chat=Chat(id=from_user.id, type="private"),
            from_user=from_user,
            caption=caption,
            photo=[PhotoSize(file_id="photo-1", file_unique_id="u1", width=10, height=10)],
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
            message=Message(
                message_id=1,
                date=datetime.now(UTC),
                chat=Chat(id=from_user.id, type="private"),
                text="old",
            ),
        ),
    )
