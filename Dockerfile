FROM python:3.12-slim

# uv ставим из PyPI: ghcr.io с некоторых серверов (в том числе российских) недоступен.
RUN pip install --no-cache-dir "uv>=0.11,<0.12"
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

RUN useradd --system --uid 1000 octo
USER octo

# Перед запуском бота применяем миграции базы.
CMD ["sh", "-c", "alembic upgrade head && python -m app"]
