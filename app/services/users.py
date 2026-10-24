from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LANGUAGES, Language
from app.db.models import User

REF_PREFIX = "ref_"


@dataclass(frozen=True, slots=True)
class TelegramProfile:
    id: int
    username: str | None
    first_name: str


def parse_referrer(start_payload: str | None) -> int | None:
    """Достаёт ID пригласившего из payload вида ref_123456."""
    if not start_payload or not start_payload.startswith(REF_PREFIX):
        return None
    raw = start_payload.removeprefix(REF_PREFIX)
    return int(raw) if raw.isdigit() else None


def referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start={REF_PREFIX}{user_id}"


async def get_or_create_user(
    session: AsyncSession, profile: TelegramProfile, referrer_id: int | None = None
) -> tuple[User, bool]:
    """Возвращает пользователя и флаг «создан сейчас».

    Пригласивший фиксируется только при создании пользователя.
    """
    user = await session.get(User, profile.id)
    if user is not None:
        user.username = profile.username
        user.first_name = profile.first_name
        return user, False

    if referrer_id == profile.id or (
        referrer_id is not None and await session.get(User, referrer_id) is None
    ):
        referrer_id = None

    user = User(
        id=profile.id,
        username=profile.username,
        first_name=profile.first_name,
        referrer_id=referrer_id,
    )
    session.add(user)
    await session.flush()
    return user, True


def set_language(user: User, language: str) -> Language:
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    user.language = language
    return language
