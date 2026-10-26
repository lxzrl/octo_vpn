from sqlalchemy import select

from app.config import Settings
from app.db.models import Plan
from app.db.session import create_engine, create_session_factory, prepare_sqlite


async def test_prepare_sqlite_creates_schema_and_plans_once() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await prepare_sqlite(engine)
    await prepare_sqlite(engine)
    async with create_session_factory(engine)() as session:
        plans = (await session.scalars(select(Plan).order_by(Plan.sort_order))).all()
    await engine.dispose()
    assert [(p.months, p.days, p.price_rub) for p in plans] == [
        (1, 30, None),
        (3, 90, None),
        (6, 180, None),
        (12, 365, None),
    ]


def test_empty_redis_url_means_memory_storage() -> None:
    assert Settings(bot_token="1:x", redis_url="").redis_url is None
