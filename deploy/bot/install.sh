#!/usr/bin/env bash
# Запуск бота на управляющем сервере, рядом с панелью Remnawave.
#
#   sudo bash deploy/bot/install.sh
#
# Запускать из папки с кодом бота (например, /opt/octo). При первом запуске создаёт .env
# из .env.example со случайным паролем базы и останавливается: заполните его и запустите снова.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [ "$(id -u)" -ne 0 ]; then
    echo "Запустите через sudo" >&2
    exit 1
fi

if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sh
fi

if [ ! -f .env ]; then
    cp .env.example .env
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" .env
    # Бот ходит в API панели напрямую по внутренней сети Docker.
    sed -i "s|^REMNAWAVE_URL=.*|REMNAWAVE_URL=http://remnawave:3000|" .env
    chmod 600 .env
    echo "Создан $ROOT/.env. Заполните BOT_TOKEN, ADMIN_IDS, REMNAWAVE_TOKEN, TRIAL_CHANNEL"
    echo "и запустите скрипт ещё раз."
    exit 0
fi

compose=(docker compose -f docker-compose.yml)
if docker network inspect remnawave-network >/dev/null 2>&1; then
    compose+=(-f deploy/bot/panel-network.yml)
fi

"${compose[@]}" up -d --build
"${compose[@]}" exec -T bot python -m app.check
echo
echo "Бот запущен. Логи: ${compose[*]} logs -f bot"
