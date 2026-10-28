"""VLESS-ссылка → конфиг Xray-клиента с локальным SOCKS5-прокси.

Нужен быстрой установке на сервер, откуда Telegram недоступен: бот ходит в api.telegram.org
через этот прокси. Только стандартная библиотека, чтобы запускаться где угодно:

    python -m app.vpn.vless 'vless://…' > xray/config.json
"""

import json
import sys
import uuid
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

SOCKS_PORT = 1080
NETWORKS = ("tcp", "raw", "ws", "grpc", "xhttp", "httpupgrade")
SECURITIES = ("none", "tls", "reality")


class InvalidLink(ValueError):
    pass


def parse_vless(link: str) -> dict[str, Any]:
    """Разбирает ссылку и возвращает outbound Xray. Неподдерживаемое — InvalidLink."""
    link = link.strip()
    if not link.startswith("vless://"):
        raise InvalidLink("ссылка должна начинаться с vless://")
    parts = urlsplit(link)
    user_id = unquote(parts.username or "")
    try:
        uuid.UUID(user_id)
    except ValueError as error:
        raise InvalidLink("в ссылке нет корректного UUID пользователя") from error
    try:
        port = parts.port
    except ValueError as error:
        raise InvalidLink("неверный порт") from error
    if not parts.hostname or port is None:
        raise InvalidLink("в ссылке нет адреса сервера или порта")

    query = {key: values[-1] for key, values in parse_qs(parts.query).items()}
    network = query.get("type", "tcp")
    security = query.get("security", "none")
    if network not in NETWORKS:
        raise InvalidLink(f"транспорт {network} не поддерживается")
    if security not in SECURITIES:
        raise InvalidLink(f"шифрование {security} не поддерживается")

    user: dict[str, Any] = {"id": user_id, "encryption": query.get("encryption", "none")}
    if query.get("flow"):
        user["flow"] = query["flow"]

    stream: dict[str, Any] = {"network": network, "security": security}
    sni = query.get("sni") or query.get("host") or ""
    fingerprint = query.get("fp", "chrome")
    if security == "reality":
        if not query.get("pbk"):
            raise InvalidLink("для Reality нужен публичный ключ (pbk)")
        stream["realitySettings"] = {
            "serverName": sni,
            "fingerprint": fingerprint,
            "publicKey": query["pbk"],
            "shortId": query.get("sid", ""),
            "spiderX": query.get("spx", ""),
        }
    elif security == "tls":
        tls: dict[str, Any] = {"serverName": sni, "fingerprint": fingerprint}
        if query.get("alpn"):
            tls["alpn"] = query["alpn"].split(",")
        stream["tlsSettings"] = tls

    path = query.get("path", "/")
    host = query.get("host", "")
    if network == "ws":
        stream["wsSettings"] = {"path": path, "host": host}
    elif network == "grpc":
        stream["grpcSettings"] = {"serviceName": query.get("serviceName", "")}
    elif network == "xhttp":
        stream["xhttpSettings"] = {"path": path, "host": host, "mode": query.get("mode", "auto")}
    elif network == "httpupgrade":
        stream["httpupgradeSettings"] = {"path": path, "host": host}

    return {
        "tag": "proxy",
        "protocol": "vless",
        "settings": {"vnext": [{"address": parts.hostname, "port": port, "users": [user]}]},
        "streamSettings": stream,
    }


def client_config(link: str) -> dict[str, Any]:
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "socks",
                "listen": "0.0.0.0",
                "port": SOCKS_PORT,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": False},
            }
        ],
        "outbounds": [parse_vless(link), {"tag": "direct", "protocol": "freedom"}],
    }


def main() -> None:
    if len(sys.argv) != 2:
        print("Использование: python -m app.vpn.vless 'vless://…'", file=sys.stderr)
        sys.exit(2)
    try:
        config = client_config(sys.argv[1])
    except InvalidLink as error:
        print(f"Не получилось разобрать ссылку: {error}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
