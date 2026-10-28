import json
import subprocess
import sys

import pytest

from app.vpn.vless import InvalidLink, client_config, parse_vless

UUID = "3f1c2d4e-5a6b-4c7d-8e9f-0a1b2c3d4e5f"
REALITY = (
    f"vless://{UUID}@203.0.113.7:443?type=tcp&security=reality&flow=xtls-rprx-vision"
    "&sni=www.example.com&fp=chrome&pbk=PUBKEY&sid=ab12&spx=%2F#%F0%9F%87%AB%F0%9F%87%AE%20FI"
)


def test_reality_link() -> None:
    outbound = parse_vless(REALITY)
    server = outbound["settings"]["vnext"][0]
    assert (server["address"], server["port"]) == ("203.0.113.7", 443)
    assert server["users"] == [{"id": UUID, "encryption": "none", "flow": "xtls-rprx-vision"}]
    stream = outbound["streamSettings"]
    assert stream["network"] == "tcp" and stream["security"] == "reality"
    assert stream["realitySettings"] == {
        "serverName": "www.example.com",
        "fingerprint": "chrome",
        "publicKey": "PUBKEY",
        "shortId": "ab12",
        "spiderX": "/",
    }


def test_ws_tls_link() -> None:
    link = f"vless://{UUID}@cdn.example.com:8443?type=ws&security=tls&path=%2Fws&host=h.example&alpn=h2,http/1.1"
    stream = parse_vless(link)["streamSettings"]
    assert stream["wsSettings"] == {"path": "/ws", "host": "h.example"}
    assert stream["tlsSettings"]["serverName"] == "h.example"
    assert stream["tlsSettings"]["alpn"] == ["h2", "http/1.1"]


@pytest.mark.parametrize(
    "link",
    [
        "https://example.com",
        "vless://not-a-uuid@1.2.3.4:443",
        f"vless://{UUID}@1.2.3.4",
        f"vless://{UUID}@1.2.3.4:443?type=kcp",
        f"vless://{UUID}@1.2.3.4:443?security=reality",
    ],
)
def test_invalid_links(link: str) -> None:
    with pytest.raises(InvalidLink):
        parse_vless(link)


def test_client_config_has_socks_inbound() -> None:
    config = client_config(REALITY)
    assert config["inbounds"][0]["protocol"] == "socks"
    assert config["inbounds"][0]["port"] == 1080
    assert [o["tag"] for o in config["outbounds"]] == ["proxy", "direct"]


def test_cli() -> None:
    ok = subprocess.run(
        [sys.executable, "-m", "app.vpn.vless", REALITY], capture_output=True, text=True
    )
    assert ok.returncode == 0 and json.loads(ok.stdout)["outbounds"][0]["tag"] == "proxy"
    bad = subprocess.run(
        [sys.executable, "-m", "app.vpn.vless", "vless://x"], capture_output=True, text=True
    )
    assert bad.returncode == 1 and "vless" not in bad.stdout and bad.stderr
