from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(moment: datetime) -> datetime:
    """SQLite отдаёт даты без часового пояса; в базе всё хранится в UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
