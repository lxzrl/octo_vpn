# Octo VPN Bot

Telegram-бот для продажи VPN-подписок. Подписки выдаются через панель
[Remnawave](https://github.com/remnawave) (VLESS + Reality): пользователь получает одну ссылку
сразу на все локации и переключается между ними в клиенте.

Проект пишется по этапам:

1. **Каркас** — Docker, база и миграции, выбор языка (ru/en), главное меню, профиль, CI.
2. **Подписки** — интеграция с Remnawave, тарифы, пробный период, инструкции по подключению. ← сейчас
3. Деньги: оплата Telegram Stars, баланс, рефералка, промокоды, напоминания.
4. Админка в боте и тикеты поддержки.
5. Запуск на серверах.

## Стек

Python 3.12, aiogram 3, PostgreSQL + SQLAlchemy 2 + Alembic, Redis, Fluent для переводов,
Docker Compose. Зависимости ставятся через [uv](https://docs.astral.sh/uv/).

## Запуск через Docker

```bash
cp .env.example .env   # заполнить BOT_TOKEN, ADMIN_IDS, POSTGRES_PASSWORD
docker compose up -d --build
docker compose logs -f bot
```

При старте контейнер сам применяет миграции базы.

## Настройка панели Remnawave

Бот работает с панелью Remnawave 3.x через REST API.

1. В панели создайте API-токен (Настройки → API-токены) и пропишите его в `REMNAWAVE_TOKEN`.
2. Создайте внутренний сквад со всеми инбаундами (локациями). Новые ноды добавляйте в этот же
   сквад: пользователи получат их при следующем обновлении подписки в приложении.
   Если сквадов несколько, а выдавать нужно не все, перечислите нужные в `REMNAWAVE_SQUADS`.
3. Лимит устройств (HWID) по плану не нужен: выключите его в настройках панели.

Каждый пользователь бота — это пользователь панели с именем `tg_<telegram id>`, без лимита
трафика. Бот меняет в панели только дату окончания; отключает доступ по истечении сама панель.

## Локальная разработка

```bash
uv sync                         # зависимости, включая dev
uv run pytest                   # тесты (по умолчанию на SQLite в памяти)
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

Тесты на PostgreSQL: `TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db uv run pytest`.

Новая миграция после изменения моделей:

```bash
uv run alembic revision --autogenerate -m "что изменилось"
```

## Структура

```
app/
  bot/
    handlers/     экраны и кнопки
    middlewares/  сессия БД, пользователь и язык для каждого апдейта
    keyboards.py  клавиатуры
    callbacks.py  данные кнопок
  services/       бизнес-логика: пользователи, подписки и триал, проверка канала
  vpn/            клиент панели Remnawave
  db/             модели SQLAlchemy и подключение
  locales/        тексты бота: ru/main.ftl, en/main.ftl
migrations/       миграции Alembic
tests/
```

Тексты бота лежат в `app/locales/*/main.ftl`; набор ключей в обоих языках должен совпадать,
это проверяет тест.
