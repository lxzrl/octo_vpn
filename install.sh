#!/usr/bin/env bash
# Быстрая установка бота на один сервер для теста, без панели Remnawave.
#
#   sudo bash install.sh
#
# Спросит токен бота, ваш Telegram ID и VLESS-ссылку. Через эту ссылку бот ходит в Telegram
# (полезно на российском сервере), и её же бот выдаёт пользователям как ключ VPN.
# Боевая установка с панелью и нодами описана в deploy/README.md.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
COMPOSE=(docker compose -f docker-compose.yml -f deploy/quick/compose.yml)

if [ "$(id -u)" -ne 0 ]; then
    echo "Запустите через sudo: sudo bash install.sh" >&2
    exit 1
fi

ask() {
    # ask <подсказка> <регулярка> <ошибка>: спрашивает, пока ответ не подойдёт.
    local answer
    while true; do
        read -r -p "$1 " answer </dev/tty
        answer="$(printf '%s' "$answer" | tr -d '[:space:]')"
        if [[ "$answer" =~ $2 ]]; then
            printf '%s' "$answer"
            return
        fi
        echo "  $3" >/dev/tty
    done
}

add_swap() {
    # На сервере с 1–2 ГБ памяти сборка образа и apt могут съесть всю RAM, и сервер зависает.
    local mem_mb
    mem_mb="$(awk '/MemTotal/ {print int($2 / 1024)}' /proc/meminfo)"
    if [ "$mem_mb" -ge 3000 ] || [ -n "$(swapon --show --noheadings 2>/dev/null)" ]; then
        return
    fi
    echo "Памяти ${mem_mb} МБ, добавляю файл подкачки 2 ГБ…"
    if fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none; then
        chmod 600 /swapfile
        if ! { mkswap /swapfile >/dev/null && swapon /swapfile; }; then
            echo "Подкачку включить не вышло, продолжаю без неё"
            rm -f /swapfile
            return
        fi
        grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
}

install_docker() {
    if command -v docker >/dev/null && docker compose version >/dev/null 2>&1; then
        return
    fi
    echo "Ставлю Docker (1–3 минуты)…"
    if command -v apt-get >/dev/null; then
        # Без этого apt может молча ждать ответа в окне «перезапустить службы?» (needrestart).
        export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a NEEDRESTART_SUSPEND=1
        # На свежем сервере apt часто занят автообновлениями: ждём до 10 минут, а не падаем.
        local apt=(apt-get -y -o DPkg::Lock::Timeout=600 -o Dpkg::Options::=--force-confdef
            -o Dpkg::Options::=--force-confold)
        "${apt[@]}" update || true
        # В репозиториях Ubuntu есть свой Docker: download.docker.com из России открывается не всегда.
        "${apt[@]}" install docker.io || true
        "${apt[@]}" install docker-compose-v2 || "${apt[@]}" install docker-compose-plugin || true
    fi
    if ! command -v docker >/dev/null; then
        echo "Docker из репозитория не встал, пробую get.docker.com…"
        curl -fsSL --max-time 60 https://get.docker.com -o /tmp/get-docker.sh
        sh /tmp/get-docker.sh
    fi
    if ! docker compose version >/dev/null 2>&1; then
        echo "Ставлю docker compose с GitHub…"
        mkdir -p /usr/local/lib/docker/cli-plugins
        curl -fL --max-time 300 -o /usr/local/lib/docker/cli-plugins/docker-compose \
            "https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-$(uname -m)"
        chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    fi
    # Docker Hub из России часто отвечает ошибкой, зеркало Google отдаёт те же образы.
    if [ ! -f /etc/docker/daemon.json ]; then
        mkdir -p /etc/docker
        echo '{"registry-mirrors": ["https://mirror.gcr.io"]}' > /etc/docker/daemon.json
    fi
    systemctl enable docker >/dev/null 2>&1 || true
    systemctl restart docker
    docker compose version
}

configure() {
    echo
    echo "1. Токен бота от @BotFather"
    local token admin_id vless password
    token="$(ask "Токен бота от @BotFather:" '^[0-9]+:[A-Za-z0-9_-]{30,}$' \
        "Не похоже на токен. Он выглядит так: 123456789:AAH…")"
    echo
    echo "2. Ваш Telegram ID (узнать: @userinfobot), вы будете админом бота"
    admin_id="$(ask "Ваш Telegram ID (несколько админов — через запятую):" '^[0-9]{5,15}(,[0-9]{5,15})*$' \
        "Нужно число, например 123456789, или несколько через запятую")"
    echo
    echo "3. VLESS-ссылка: через неё бот ходит в Telegram, её же получат пользователи"
    vless="$(ask "VLESS-ссылка:" "^vless://[^']+$" "Ссылка должна начинаться с vless://")"

    if [ -f .env ]; then
        # Пароль уже записан в базе (том postgres), менять его нельзя.
        password="$(grep -E '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)"
        cp .env .env.bak
    else
        password="$(openssl rand -hex 24)"
    fi
    # Ключи, которые задаёт установщик, убираем из шаблона и дописываем в конец.
    local keys='^(BOT_TOKEN|ADMIN_IDS|POSTGRES_PASSWORD|VPN_PANEL|DEMO_SUBSCRIPTION_URL|TELEGRAM_PROXY)='
    {
        grep -Ev "$keys" .env.example
        echo
        echo "# Задано install.sh"
        echo "BOT_TOKEN='$token'"
        echo "ADMIN_IDS=$admin_id"
        echo "POSTGRES_PASSWORD=$password"
        echo "VPN_PANEL=demo"
        echo "DEMO_SUBSCRIPTION_URL='$vless'"
        echo "TELEGRAM_PROXY=socks5://xray:1080"
    } > .env
    chmod 600 .env
}

rollback() {
    if [ -f .env.bak ]; then
        mv .env.bak .env
    else
        rm -f .env
    fi
}

add_swap
install_docker

rm -f .env.bak
if [ -f .env ]; then
    read -r -p "Бот уже настроен. Ввести токен, ID и ссылку заново? [y/N] " again </dev/tty
    if [[ "$again" =~ ^[YyДд] ]]; then
        configure
    fi
else
    configure
fi

echo
echo "Собираю бота (первый раз несколько минут)…"
"${COMPOSE[@]}" build bot

# Конфиг Xray-клиента из ссылки в .env. Неверная ссылка — возвращаем прежний .env.
mkdir -p xray
# shellcheck disable=SC2016  # переменная раскрывается внутри контейнера
if ! "${COMPOSE[@]}" run --rm --no-deps -T bot \
        sh -c 'python -m app.vpn.vless "$DEMO_SUBSCRIPTION_URL"' > xray/config.new; then
    rm -f xray/config.new
    rollback
    echo "Проверьте ссылку и запустите install.sh ещё раз." >&2
    exit 1
fi
mv xray/config.new xray/config.json
rm -f .env.bak

# xray пересоздаём, чтобы он подхватил новый конфиг.
"${COMPOSE[@]}" up -d --force-recreate xray postgres redis
"${COMPOSE[@]}" run --rm -T bot alembic upgrade head >/dev/null
echo
echo "Проверяю…"
checked=true
"${COMPOSE[@]}" run --rm -T bot python -m app.check || checked=false
"${COMPOSE[@]}" up -d --force-recreate bot

if [ "$checked" = false ]; then
    cat >&2 <<FAIL

Бот запущен, но проверка выше нашла проблемы. Если нет связи с Telegram — проверьте, что
VLESS-ссылка рабочая (например, в Happ на телефоне), и запустите sudo bash install.sh заново.
Логи: cd $ROOT && ${COMPOSE[*]} logs --tail 50 bot xray
FAIL
    exit 1
fi
cat <<DONE

Готово, бот работает в тестовом режиме: сроки и оплаты настоящие, а ключ у всех один —
ваша VLESS-ссылка.

  • В Telegram: /start, затем /admin — меню админа.
  • /admin → Тарифы: задайте цены, иначе купить будет нечего.
  • /admin → Настройки: курс звезды, пробный период, канал.

Логи:        cd $ROOT && ${COMPOSE[*]} logs -f bot
Перезапуск:  cd $ROOT && ${COMPOSE[*]} restart
Обновление:  cd $ROOT && git pull && sudo bash install.sh
Остановить:  cd $ROOT && ${COMPOSE[*]} down
DONE
