from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class PanelError(Exception):
    """Панель недоступна или ответила ошибкой."""


@dataclass(frozen=True, slots=True)
class PanelUser:
    id: int
    username: str
    subscription_url: str
    expire_at: datetime
    status: str


class VpnPanel(Protocol):
    """То, что бот умеет делать с VPN-панелью. Реализация для Remnawave в remnawave.py."""

    async def get_user_by_username(self, username: str) -> PanelUser | None: ...

    async def create_user(
        self, username: str, telegram_id: int, expire_at: datetime
    ) -> PanelUser: ...

    async def update_user(self, user_id: int, expire_at: datetime) -> PanelUser: ...
