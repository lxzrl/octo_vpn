"""Темы оформления: наборы картинок к экранам бота."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Theme, ThemeImage, User

# Тема по умолчанию: у новых пользователей и у тех, чья тема скрыта или удалена.
DEFAULT_THEME = "light"
BUILTIN_THEMES = (
    ("light", "☀️ Светлая", "☀️ Light"),
    ("dark", "🌙 Тёмная", "🌙 Dark"),
)
NAME_MAX = 64


class Screen(StrEnum):
    """Экраны бота, к которым в теме может быть картинка."""

    MAIN = "main"
    PROFILE = "profile"
    THEME = "theme"
    SUBSCRIPTION = "subscription"
    CONNECT = "connect"
    BUY = "buy"
    REFERRAL = "referral"
    SUPPORT = "support"


@dataclass(frozen=True, slots=True)
class ThemeImages:
    """Картинки для одного пользователя: его тема, а чего в ней нет — из темы по умолчанию."""

    layers: tuple[dict[str, str], ...] = field(default_factory=tuple)

    def of(self, screen: Screen) -> str | None:
        # Сначала картинка экрана, потом картинка главного меню той же темы: так тема,
        # где загружена только одна картинка, всё равно выглядит единообразно.
        for images in self.layers:
            if found := images.get(screen) or images.get(Screen.MAIN):
                return found
        return None


def theme_name(theme: Theme, language: str | None) -> str:
    return theme.name_en if language == "en" else theme.name


async def active_themes(session: AsyncSession) -> Sequence[Theme]:
    query = select(Theme).where(Theme.is_active).order_by(Theme.sort_order, Theme.id)
    return (await session.scalars(query)).all()


async def all_themes(session: AsyncSession) -> Sequence[Theme]:
    return (await session.scalars(select(Theme).order_by(Theme.sort_order, Theme.id))).all()


async def default_theme(session: AsyncSession) -> Theme | None:
    return await session.scalar(select(Theme).where(Theme.code == DEFAULT_THEME))


async def user_theme(
    session: AsyncSession, user: User, default: Theme | None = None
) -> Theme | None:
    """Тема пользователя, если её ещё можно показывать, иначе тема по умолчанию."""
    if user.theme_id is not None:
        theme = await session.get(Theme, user.theme_id)
        if theme is not None and theme.is_active:
            return theme
    return default or await default_theme(session)


async def theme_images(session: AsyncSession, theme_id: int) -> dict[str, str]:
    rows = await session.scalars(select(ThemeImage).where(ThemeImage.theme_id == theme_id))
    return {row.screen: row.file_id for row in rows}


async def images_for(session: AsyncSession, user: User | None) -> ThemeImages:
    default = await default_theme(session)
    theme = await user_theme(session, user, default) if user is not None else default
    layers = []
    if theme is not None:
        layers.append(await theme_images(session, theme.id))
    if default is not None and (theme is None or theme.id != default.id):
        layers.append(await theme_images(session, default.id))
    return ThemeImages(tuple(layers))


async def choose_theme(session: AsyncSession, user: User, theme_id: int) -> Theme | None:
    """Выбор пользователя. Скрытую или несуществующую тему выбрать нельзя — None."""
    theme = await session.get(Theme, theme_id)
    if theme is None or not theme.is_active:
        return None
    user.theme_id = theme.id
    await session.flush()
    return theme


async def create_theme(session: AsyncSession, name: str, name_en: str) -> Theme:
    last = await session.scalar(select(func.max(Theme.sort_order)))
    theme = Theme(name=name[:NAME_MAX], name_en=name_en[:NAME_MAX], sort_order=(last or 0) + 1)
    session.add(theme)
    await session.flush()
    return theme


async def ensure_builtin_themes(session: AsyncSession) -> None:
    """Для SQLite без миграций: создаёт «Светлую» и «Тёмную», если их нет."""
    for order, (code, name, name_en) in enumerate(BUILTIN_THEMES, 1):
        if await session.scalar(select(Theme).where(Theme.code == code)) is None:
            session.add(Theme(code=code, name=name, name_en=name_en, sort_order=order))
    await session.flush()


async def set_theme_image(
    session: AsyncSession, theme_id: int, screen: Screen, file_id: str | None
) -> None:
    """Сохраняет картинку экрана в теме; None — убрать картинку."""
    row = await session.get(ThemeImage, (theme_id, screen.value))
    if file_id is None:
        if row is not None:
            await session.delete(row)
    elif row is None:
        session.add(ThemeImage(theme_id=theme_id, screen=screen.value, file_id=file_id))
    else:
        row.file_id = file_id
    await session.flush()


async def delete_theme(session: AsyncSession, theme: Theme) -> None:
    """Удаляет сезонную тему. Встроенные не удаляются, их можно только скрыть."""
    if theme.code is not None:
        raise ValueError("встроенную тему удалить нельзя")
    await session.execute(update(User).where(User.theme_id == theme.id).values(theme_id=None))
    # Картинки удаляем сами: в SQLite (локальный запуск) внешние ключи не каскадят.
    await session.execute(delete(ThemeImage).where(ThemeImage.theme_id == theme.id))
    await session.delete(theme)
    await session.flush()
