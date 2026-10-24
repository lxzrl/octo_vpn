import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

os.environ.setdefault("BOT_TOKEN", "42:TEST")

from app.config import Settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import create_engine, create_session_factory

# Тесты не должны зависеть от локального .env разработчика или CI.
Settings.model_config["env_file"] = None

# По умолчанию тесты идут на SQLite в памяти; в CI можно указать PostgreSQL.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield create_session_factory(engine)
    await engine.dispose()


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
