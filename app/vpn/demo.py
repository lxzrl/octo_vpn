from dataclasses import dataclass
from datetime import datetime

from app.vpn.panel import PanelUser

DEMO_STATUS = "ACTIVE"
DEMO_USER_ID = 0


@dataclass
class DemoPanel:
    """Тестовый режим без панели: ничего не хранит и никуда не ходит.

    Срок подписки ведёт база бота, а ссылка у всех одна (например, VLESS-ключ владельца),
    чтобы можно было пройти весь путь до подключения.
    """

    subscription_url: str

    def _user(self, expire_at: datetime) -> PanelUser:
        return PanelUser(DEMO_USER_ID, "demo", self.subscription_url, expire_at, DEMO_STATUS)

    async def get_user_by_username(self, username: str) -> PanelUser | None:
        return None

    async def create_user(self, username: str, telegram_id: int, expire_at: datetime) -> PanelUser:
        return self._user(expire_at)

    async def update_user(self, user_id: int, expire_at: datetime) -> PanelUser:
        return self._user(expire_at)
