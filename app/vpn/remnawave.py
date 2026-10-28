import logging
from datetime import UTC, datetime
from typing import Any

import aiohttp

from app.vpn.panel import PanelError, PanelUser

logger = logging.getLogger(__name__)


def _parse_user(data: dict[str, Any]) -> PanelUser:
    return PanelUser(
        id=int(data["id"]),
        username=str(data["username"]),
        subscription_url=str(data["subscriptionUrl"]),
        expire_at=datetime.fromisoformat(str(data["expireAt"]).replace("Z", "+00:00")),
        status=str(data["status"]),
    )


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class RemnawaveClient:
    """Клиент REST API панели Remnawave 3.x (контракт @remnawave/backend-contract)."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        token: str,
        caddy_token: str | None = None,
        squads: tuple[str, ...] = (),
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            # Панель принимает API-запросы только по HTTPS; внутри docker-сети
            # ходим по HTTP, поэтому сообщаем ей, что снаружи был HTTPS.
            "X-Forwarded-Proto": "https",
            "X-Forwarded-For": "127.0.0.1",
        }
        if caddy_token:
            self._headers["X-Api-Key"] = caddy_token
        self._squads = squads

    async def _request(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        url = f"{self._base_url}/api/{path}"
        try:
            async with self._session.request(
                method, url, json=json, headers=self._headers
            ) as response:
                if response.status == 404:
                    return None
                body = await response.text()
                if response.status >= 400:
                    raise PanelError(f"{method} {path}: HTTP {response.status}: {body[:500]}")
                data: dict[str, Any] = (await response.json(content_type=None))["response"]
                return data
        except (aiohttp.ClientError, TimeoutError) as error:
            raise PanelError(f"{method} {path}: {error!r}") from error

    async def squad_uuids(self) -> list[str]:
        if self._squads:
            return list(self._squads)
        data = await self._request("GET", "internal-squads")
        if not data or not data["internalSquads"]:
            raise PanelError("В панели нет ни одного внутреннего сквада")
        return [str(squad["uuid"]) for squad in data["internalSquads"]]

    async def get_user_by_username(self, username: str) -> PanelUser | None:
        data = await self._request("GET", f"users/by-username/{username}")
        return _parse_user(data) if data else None

    async def create_user(self, username: str, telegram_id: int, expire_at: datetime) -> PanelUser:
        data = await self._request(
            "POST",
            "users",
            json={
                "username": username,
                "telegramId": telegram_id,
                "expireAt": _iso(expire_at),
                "trafficLimitBytes": 0,
                "trafficLimitStrategy": "NO_RESET",
                "activeInternalSquads": await self.squad_uuids(),
            },
        )
        if data is None:
            raise PanelError("POST users: HTTP 404")
        return _parse_user(data)

    async def update_user(self, user_id: int, expire_at: datetime) -> PanelUser:
        data = await self._request(
            "PATCH",
            "users",
            json={
                "id": user_id,
                "expireAt": _iso(expire_at),
                "status": "ACTIVE",
                # Заодно подключаем новые локации, если они появились в панели.
                "activeInternalSquads": await self.squad_uuids(),
            },
        )
        if data is None:
            raise PanelError(f"PATCH users: пользователь {user_id} не найден")
        return _parse_user(data)
