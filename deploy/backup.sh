#!/usr/bin/env bash
# Резервная копия баз бота и панели. Хранит копии BACKUP_KEEP_DAYS дней (по умолчанию 14)
# и, если в .env бота задан BACKUP_CHAT_ID, отправляет архив в этот чат Telegram.
#
#   sudo bash deploy/backup.sh
#
# Раз в сутки по cron (в 04:00):
#   echo '0 4 * * * root bash /opt/octo/deploy/backup.sh >> /var/log/octo-backup.log 2>&1' \
#       > /etc/cron.d/octo-backup
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${BACKUP_DIR:-/opt/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
STAMP="$(date -u +%Y%m%d-%H%M)"
TARGET="$OUT/octo-$STAMP"

env_value() {
    grep -E "^$1=" "$ROOT/.env" | tail -1 | cut -d= -f2- | tr -d '"' || true
}

mkdir -p "$TARGET"
chmod 700 "$OUT"

cd "$ROOT"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
    | gzip > "$TARGET/bot.sql.gz"

if docker ps --format '{{.Names}}' | grep -qx remnawave-db; then
    docker exec remnawave-db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
        | gzip > "$TARGET/panel.sql.gz"
    cp /opt/remnawave/.env "$TARGET/panel.env"
fi
cp "$ROOT/.env" "$TARGET/bot.env"

tar -C "$OUT" -czf "$TARGET.tar.gz" "octo-$STAMP"
rm -rf "$TARGET"
chmod 600 "$TARGET.tar.gz"
find "$OUT" -name 'octo-*.tar.gz' -mtime +"$KEEP_DAYS" -delete
echo "$(date -u) копия: $TARGET.tar.gz"

CHAT_ID="$(env_value BACKUP_CHAT_ID)"
if [ -n "$CHAT_ID" ]; then
    TOKEN="$(env_value BOT_TOKEN)"
    curl -fsS -o /dev/null \
        -F chat_id="$CHAT_ID" \
        -F document=@"$TARGET.tar.gz" \
        -F caption="Резервная копия Octo VPN $STAMP" \
        "https://api.telegram.org/bot$TOKEN/sendDocument"
    echo "отправлена в Telegram"
fi
