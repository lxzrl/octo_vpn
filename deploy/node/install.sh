#!/usr/bin/env bash
# Установка ноды Remnawave на VPN-сервер локации (Ubuntu/Debian).
#
#   sudo bash install.sh <IP панели> <NODE_PORT> '<SECRET_KEY>'
#
# NODE_PORT и SECRET_KEY берутся в панели: Nodes → Management → «+» → Copy docker-compose.yml.
# Скрипт ставит Docker, ноду, включает BBR и закрывает порт API ноды для всех, кроме панели.
set -euo pipefail

PANEL_IP="${1:?Укажите IP управляющего сервера}"
NODE_PORT="${2:?Укажите NODE_PORT из панели}"
SECRET_KEY="${3:?Укажите SECRET_KEY из панели}"
SSH_PORT="${SSH_PORT:-22}"
# Порт входящих VPN-подключений: тот же, что в профиле Xray (обычно 443).
VPN_PORT="${VPN_PORT:-443}"
DIR=/opt/remnanode

if [ "$(id -u)" -ne 0 ]; then
    echo "Запустите через sudo" >&2
    exit 1
fi

if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sh
fi

mkdir -p "$DIR"
cat > "$DIR/docker-compose.yml" <<YAML
services:
  remnanode:
    container_name: remnanode
    hostname: remnanode
    image: remnawave/node:latest
    restart: always
    network_mode: host
    environment:
      - NODE_PORT=$NODE_PORT
      - SECRET_KEY=$SECRET_KEY
    logging:
      driver: json-file
      options:
        max-size: 20m
        max-file: "5"
YAML
chmod 600 "$DIR/docker-compose.yml"

# BBR заметно ускоряет TCP на дальних маршрутах.
cat > /etc/sysctl.d/99-octo-vpn.conf <<SYSCTL
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
SYSCTL
sysctl --system >/dev/null

if command -v ufw >/dev/null; then
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow "$SSH_PORT"/tcp
    ufw allow "$VPN_PORT"/tcp
    ufw allow from "$PANEL_IP" to any port "$NODE_PORT" proto tcp
    ufw --force enable
else
    echo "ufw не найден: закройте порт $NODE_PORT для всех, кроме $PANEL_IP, вручную" >&2
fi

cd "$DIR"
docker compose up -d
echo
echo "Нода запущена. Вернитесь в панель, нажмите Next, выберите профиль и Create."
