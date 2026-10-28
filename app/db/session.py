from sqlalchemy import Connection, func, inspect, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.models import Plan
from app.services.themes import ensure_builtin_themes


def create_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


DEFAULT_PLANS = ((1, 30), (3, 90), (6, 180), (12, 365))


def _add_new_columns(conn: Connection) -> None:
    """create_all не меняет существующие таблицы: новые столбцы из обновлений бота добавляем сами.
    ALTER TABLE в SQLite добавляет только столбцы без NOT NULL — новые такими и делаем."""
    inspector = inspect(conn)
    for table in Base.metadata.sorted_tables:
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name not in existing:
                kind = column.type.compile(dialect=conn.dialect)
                conn.exec_driver_sql(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {kind}")


async def prepare_sqlite(engine: AsyncEngine) -> None:
    """Локальный запуск на SQLite: миграции написаны под PostgreSQL, поэтому схему создаём
    по моделям и добавляем стартовые тарифы без цен, как это делает миграция 0002."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_new_columns)
    async with create_session_factory(engine)() as session:
        if not await session.scalar(select(func.count()).select_from(Plan)):
            session.add_all(
                Plan(months=months, days=days, sort_order=index)
                for index, (months, days) in enumerate(DEFAULT_PLANS, 1)
            )
        await ensure_builtin_themes(session)
        await session.commit()
