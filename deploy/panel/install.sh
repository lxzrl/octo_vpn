#!/usr/bin/env bash
# Установка панели Remnawave и Caddy на управляющий сервер (Ubuntu/Debian).
#
#   sudo bash deploy/panel/install.sh panel.example.com
#
# Файлы панели берутся из официального репозитория Remnawave (docs.rw/install/remnawave-panel),
# секреты и пароль базы генерируются автоматически. Повторный запуск не перезаписывает .env.
set -euo pipefail

DOMAIN="${1:?Укажите домен панели, например: sudo bash install.sh panel.example.com}"
SSH_PORT="${SSH_PORT:-22}"
DIR=/opt/remnawave
RAW=https://raw.githubusercontent.com/remnawave/backend/refs/heads/main
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo "Запустите через sudo" >&2
    exit 1
fi

if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sh
fi

mkdir -p "$DIR/caddy"
cd "$DIR"

if [ ! -f .env ]; then
    curl -fsSL -o docker-compose.yml "$RAW/docker-compose-prod.yml"
    curl -fsSL -o .env "$RAW/.env.sample"
    sed -i "s|^APP_SECRET=.*|APP_SECRET=$(openssl rand -hex 64)|" .env
    sed -i "s|^METRICS_PASS=.*|METRICS_PASS=$(openssl rand -hex 64)|" .env
    sed -i "s|^WEBHOOK_SECRET_HEADER=.*|WEBHOOK_SECRET_HEADER=$(openssl rand -hex 64)|" .env
    pw="$(openssl rand -hex 24)"
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$pw|" .env
    sed -i "s|^\(DATABASE_URL=\"postgresql://postgres:\)[^@]*\(@.*\)|\1$pw\2|" .env
    sed -i "s|^PANEL_DOMAIN=.*|PANEL_DOMAIN=$DOMAIN|" .env
    sed -i "s|^FRONT_END_DOMAIN=.*|FRONT_END_DOMAIN=$DOMAIN|" .env
    sed -i "s|^SUB_PUBLIC_DOMAIN=.*|SUB_PUBLIC_DOMAIN=$DOMAIN/api/sub|" .env
    chmod 600 .env
    echo "Создан $DIR/.env"
else
    echo "$DIR/.env уже есть, оставляю как есть"
fi

cp "$HERE/Caddyfile" caddy/Caddyfile
cp "$HERE/caddy-compose.yml" caddy/docker-compose.yml
echo "PANEL_DOMAIN=$DOMAIN" > caddy/.env

docker compose up -d
(cd caddy && docker compose up -d)

if command -v ufw >/dev/null; then
    ufw allow "$SSH_PORT"/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
fi

echo
echo "Готово. Откройте https://$DOMAIN и зарегистрируйте администратора панели:"
echo "первый зарегистрированный пользователь становится админом, сделайте это сразу."
