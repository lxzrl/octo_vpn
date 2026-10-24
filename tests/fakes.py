from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from itertools import count

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
