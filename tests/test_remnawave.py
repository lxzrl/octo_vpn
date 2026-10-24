from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from app.vpn.panel import PanelError
from app.vpn.remnawave import RemnawaveClient

SQUAD = "11111111-1111-4111-8111-111111111111"


def panel_user(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 7,
        "username": "tg_1",
        "subscriptionUrl": "https://sub.example/abc",
        "expireAt": "2026-02-01T00:00:00.000Z",
        "status": "ACTIVE",
        **overrides,
    }


class Panel:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict[str, Any] | None, dict[str, str]]] = []
        self.fail_status: int | None = None

    async def handle(self, request: web.Request) -> web.Response:
        body = await request.json() if request.can_read_body else None
        self.requests.append((request.method, request.path, body, dict(request.headers)))
        if self.fail_status:
            return web.json_response({"message": "boom"}, status=self.fail_status)
        if request.path == "/api/internal-squads":
            return web.json_response(
                {"response": {"total": 1, "internalSquads": [{"uuid": SQUAD, "name": "all"}]}}
            )
        if request.path == "/api/users/by-username/missing":
            return web.json_response({"message": "not found"}, status=404)
        if request.path.startswith("/api/users/by-username/"):
            return web.json_response({"response": panel_user()})
        expire = body["expireAt"] if body else "2026-02-01T00:00:00.000Z"
        return web.json_response({"response": panel_user(expireAt=expire)})


@pytest.fixture
async def panel() -> AsyncIterator[tuple[Panel, RemnawaveClient]]:
    fake = Panel()
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", fake.handle)
    server = TestServer(app)
    await server.start_server()
    async with aiohttp.ClientSession() as http:
        yield fake, RemnawaveClient(http, str(server.make_url("/")), "secret", caddy_token="caddy")
    await server.close()


async def test_create_user_sends_contract_fields(panel: tuple[Panel, RemnawaveClient]) -> None:
    fake, client = panel
    expire = datetime(2026, 2, 1, tzinfo=UTC)
    user = await client.create_user("tg_1", 1, expire)

    assert user.id == 7 and user.subscription_url == "https://sub.example/abc"
    assert user.expire_at == expire
    method, path, body, headers = fake.requests[-1]
    assert (method, path) == ("POST", "/api/users")
    assert body == {
        "username": "tg_1",
        "telegramId": 1,
        "expireAt": "2026-02-01T00:00:00.000Z",
        "trafficLimitBytes": 0,
        "trafficLimitStrategy": "NO_RESET",
        "activeInternalSquads": [SQUAD],
    }
    assert headers["Authorization"] == "Bearer secret"
    assert headers["X-Api-Key"] == "caddy"


async def test_update_user_reactivates(panel: tuple[Panel, RemnawaveClient]) -> None:
    fake, client = panel
    await client.update_user(7, datetime(2026, 3, 1, tzinfo=UTC))
    method, path, body, _ = fake.requests[-1]
    assert (method, path) == ("PATCH", "/api/users")
    assert body is not None and body["id"] == 7 and body["status"] == "ACTIVE"


async def test_get_user_by_username(panel: tuple[Panel, RemnawaveClient]) -> None:
    _, client = panel
    assert (await client.get_user_by_username("tg_1")) is not None
    assert await client.get_user_by_username("missing") is None


async def test_http_error_becomes_panel_error(panel: tuple[Panel, RemnawaveClient]) -> None:
    fake, client = panel
    fake.fail_status = 500
    with pytest.raises(PanelError, match="HTTP 500"):
        await client.update_user(7, datetime(2026, 3, 1, tzinfo=UTC))


async def test_unreachable_panel_becomes_panel_error() -> None:
    async with aiohttp.ClientSession() as http:
        client = RemnawaveClient(http, "http://127.0.0.1:9", "t", squads=(SQUAD,))
        with pytest.raises(PanelError):
            await client.update_user(7, datetime(2026, 3, 1, tzinfo=UTC))
