import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageMedia, EditMessageText, SendMessage, SendPhoto
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.callbacks import (
    AdminAction,
    AdminCallback,
    LanguageCallback,
    MenuAction,
    MenuCallback,
    ThemeCallback,
)
from app.config import Settings
from app.db.models import Theme, ThemeImage
from app.db.models import User as DbUser
from app.i18n import TranslatorHub
from app.main import build_dispatcher
from app.services.themes import (
    Screen,
    choose_theme,
    create_theme,
    delete_theme,
    ensure_builtin_themes,
    images_for,
    set_theme_image,
)
from tests.fakes import TG_USER, FakePanel, FakeSession, callback, message, photo

ADMIN = TG_USER


@pytest.fixture
async def themes(session_factory: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    async with session_factory() as session:
        await ensure_builtin_themes(session)
        await session.commit()
        rows = await session.scalars(select(Theme))
        return {theme.code or "": theme.id for theme in rows}


@pytest.fixture
def fake() -> FakeSession:
    return FakeSession()


@pytest.fixture
def bot(fake: FakeSession) -> Bot:
    return Bot("42:TEST", session=fake)


@pytest.fixture
def dp(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    settings = Settings(bot_token="42:TEST", admin_ids=str(ADMIN.id), trial_channel=None)
    return build_dispatcher(settings, session_factory, TranslatorHub("ru"), FakePanel())


def keyboard(call: object) -> list[str]:
    markup = getattr(call, "reply_markup", None)
    assert isinstance(markup, InlineKeyboardMarkup)
    return [b.text for row in markup.inline_keyboard for b in row]


async def test_images_fall_back_to_theme_main_then_default_theme(
    session_factory: async_sessionmaker[AsyncSession], themes: dict[str, int]
) -> None:
    async with session_factory() as session:
        user = DbUser(id=5, first_name="U", language="ru")
        session.add(user)
        await set_theme_image(session, themes["light"], Screen.MAIN, "light-main")
        await set_theme_image(session, themes["light"], Screen.BUY, "light-buy")
        await set_theme_image(session, themes["dark"], Screen.PROFILE, "dark-profile")

        images = await images_for(session, user)
        assert images.of(Screen.BUY) == "light-buy"
        assert images.of(Screen.SUPPORT) == "light-main"

        assert await choose_theme(session, user, themes["dark"]) is not None
        images = await images_for(session, user)
        assert images.of(Screen.PROFILE) == "dark-profile"
        # В «Тёмной» нет ни картинки покупки, ни главного меню: берётся «Светлая».
        assert images.of(Screen.BUY) == "light-buy"

        await set_theme_image(session, themes["dark"], Screen.MAIN, "dark-main")
        images = await images_for(session, user)
        assert images.of(Screen.BUY) == "dark-main"


async def test_hidden_and_deleted_themes(
    session_factory: async_sessionmaker[AsyncSession], themes: dict[str, int]
) -> None:
    async with session_factory() as session:
        user = DbUser(id=6, first_name="U", language="ru")
        session.add(user)
        await set_theme_image(session, themes["light"], Screen.MAIN, "light-main")
        halloween = await create_theme(session, "🎃 Хэллоуин", "🎃 Halloween")
        await set_theme_image(session, halloween.id, Screen.MAIN, "pumpkin")
        await choose_theme(session, user, halloween.id)
        assert (await images_for(session, user)).of(Screen.MAIN) == "pumpkin"

        halloween.is_active = False
        assert (await images_for(session, user)).of(Screen.MAIN) == "light-main"
        assert await choose_theme(session, user, halloween.id) is None

        dark = await session.get(Theme, themes["dark"])
        assert dark is not None
        with pytest.raises(ValueError):
            await delete_theme(session, dark)
        await delete_theme(session, halloween)
        await session.refresh(user)
        assert user.theme_id is None
        assert (
            await session.scalars(select(ThemeImage).where(ThemeImage.file_id == "pumpkin"))
        ).first() is None


async def test_theme_is_chosen_after_language_and_in_profile(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    themes: dict[str, int],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await set_theme_image(session, themes["light"], Screen.MAIN, "light-main")
        await set_theme_image(session, themes["dark"], Screen.MAIN, "dark-main")
        await set_theme_image(session, themes["light"], Screen.THEME, "light-theme")
        await session.commit()

    await dp.feed_update(bot, message("/start"))
    await dp.feed_update(bot, callback(LanguageCallback(code="ru").pack()))
    # После языка — выбор темы, а не главное меню.
    screen = fake.calls[-2]
    assert isinstance(screen, SendPhoto) and "оформление" in (screen.caption or "")
    assert screen.photo == "light-theme"
    assert keyboard(screen) == ["✓ ☀️ Светлая", "🌙 Тёмная"]

    fake.calls.clear()
    await dp.feed_update(
        bot,
        callback(ThemeCallback(theme_id=themes["dark"], onboarding=True).pack(), with_photo=True),
    )
    menu = fake.calls[0]
    assert isinstance(menu, EditMessageMedia)
    assert menu.media.media == "dark-main" and "Привет" in (menu.media.caption or "")

    fake.calls.clear()
    await dp.feed_update(
        bot, callback(MenuCallback(action=MenuAction.PROFILE).pack(), with_photo=True)
    )
    profile = fake.calls[0]
    assert isinstance(profile, EditMessageMedia)
    assert "Тема: 🌙 Тёмная" in (profile.media.caption or "")
    assert "🎨 Сменить тему" in keyboard(profile)

    await dp.feed_update(
        bot, callback(MenuCallback(action=MenuAction.THEME).pack(), with_photo=True)
    )
    await dp.feed_update(
        bot, callback(ThemeCallback(theme_id=themes["light"]).pack(), with_photo=True)
    )
    back_to_profile = fake.calls[-2]
    assert isinstance(back_to_profile, EditMessageMedia)
    assert back_to_profile.media.media == "light-main"
    assert "Тема: ☀️ Светлая" in (back_to_profile.media.caption or "")


async def test_without_images_screens_stay_text(
    dp: Dispatcher, bot: Bot, fake: FakeSession, themes: dict[str, int]
) -> None:
    await dp.feed_update(bot, message("/start"))
    await dp.feed_update(bot, callback(LanguageCallback(code="ru").pack()))
    await dp.feed_update(
        bot, callback(ThemeCallback(theme_id=themes["light"], onboarding=True).pack())
    )
    assert isinstance(fake.calls[-2], EditMessageText)
    assert not any(isinstance(call, SendPhoto) for call in fake.calls)


async def test_admin_creates_theme_and_uploads_image(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    themes: dict[str, int],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    def adm(action: AdminAction, id: int = 0, value: str = "") -> str:
        return AdminCallback(action=action, id=id, value=value).pack()

    await dp.feed_update(bot, message("/start"))
    await dp.feed_update(bot, callback(LanguageCallback(code="ru").pack()))
    await dp.feed_update(bot, callback(adm(AdminAction.DESIGN)))
    assert "☀️ Светлая · 🖼 0/8" in keyboard(fake.calls[-2])

    await dp.feed_update(bot, callback(adm(AdminAction.THEME_NEW)))
    await dp.feed_update(bot, message("🎃 Хэллоуин"))
    await dp.feed_update(bot, message("-"))
    created = fake.calls[-1]
    assert isinstance(created, SendMessage) and "Тема создана" in created.text

    async with session_factory() as session:
        theme = await session.scalar(select(Theme).where(Theme.name == "🎃 Хэллоуин"))
        assert theme is not None and theme.name_en == "🎃 Хэллоуин"

    await dp.feed_update(bot, callback(adm(AdminAction.IMAGE, theme.id, Screen.MAIN)))
    await dp.feed_update(bot, photo(None))
    saved = fake.calls[-1]
    assert isinstance(saved, SendPhoto) and saved.photo == "photo-1"
    assert "Картинка сохранена" in (saved.caption or "")

    # Новая тема сразу доступна пользователям.
    await dp.feed_update(bot, callback(MenuCallback(action=MenuAction.THEME).pack()))
    assert "🎃 Хэллоуин" in keyboard(fake.calls[-2])

    await dp.feed_update(bot, callback(adm(AdminAction.THEME_TOGGLE, theme.id), with_photo=True))
    await dp.feed_update(bot, callback(MenuCallback(action=MenuAction.THEME).pack()))
    assert "🎃 Хэллоуин" not in keyboard(fake.calls[-2])
