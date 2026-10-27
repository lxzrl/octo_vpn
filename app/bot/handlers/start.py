import html

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import LanguageCallback, MenuAction, MenuCallback, ThemeCallback
from app.bot.keyboards import (
    language_keyboard,
    main_menu_keyboard,
    profile_keyboard,
    theme_keyboard,
)
from app.bot.ui import send_screen, show
from app.config import Settings
from app.db.models import User
from app.i18n import Translator, TranslatorHub
from app.services.money import rub
from app.services.themes import (
    Screen,
    ThemeImages,
    active_themes,
    choose_theme,
    images_for,
    theme_name,
    user_theme,
)
from app.services.users import set_language


def main_menu_text(i18n: Translator, user: User) -> str:
    # Режим разметки HTML: имя из Telegram может содержать < и &.
    return i18n("main-menu", name=html.escape(user.first_name))


def main_menu(i18n: Translator, user: User, settings: Settings) -> InlineKeyboardMarkup:
    return main_menu_keyboard(i18n, is_admin=user.id in settings.admin_ids)


async def profile_text(session: AsyncSession, i18n: Translator, user: User) -> str:
    theme = await user_theme(session, user)
    return i18n(
        "profile",
        id=str(user.id),
        registered=user.created_at.strftime("%d.%m.%Y"),
        language=i18n("language-name"),
        balance=rub(user.balance_kop),
        theme=html.escape(theme_name(theme, user.language)) if theme else "—",
    )


async def show_profile(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: Translator,
    user: User,
    images: ThemeImages,
) -> None:
    await show(
        callback,
        await profile_text(session, i18n, user),
        profile_keyboard(i18n),
        images.of(Screen.PROFILE),
    )


async def show_themes(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: Translator,
    user: User,
    images: ThemeImages,
    onboarding: bool,
) -> bool:
    """Экран выбора темы. Если выбирать не из чего, возвращает False и ничего не показывает."""
    themes = await active_themes(session)
    if onboarding and len(themes) < 2:
        return False
    current = await user_theme(session, user)
    await show(
        callback,
        i18n("choose-theme"),
        theme_keyboard(i18n, themes, current.id if current else None, user.language, onboarding),
        images.of(Screen.THEME),
    )
    return True


async def cmd_start(
    message: Message,
    user: User,
    i18n: Translator,
    state: FSMContext,
    settings: Settings,
    images: ThemeImages,
) -> None:
    await state.clear()
    if user.language is None:
        await message.answer(i18n("choose-language"), reply_markup=language_keyboard())
        return
    await send_screen(
        message,
        main_menu_text(i18n, user),
        main_menu(i18n, user, settings),
        images.of(Screen.MAIN),
    )


async def on_language(
    callback: CallbackQuery,
    callback_data: LanguageCallback,
    session: AsyncSession,
    user: User,
    translators: TranslatorHub,
    settings: Settings,
    images: ThemeImages,
) -> None:
    first_choice = user.language is None
    i18n = translators.get(set_language(user, callback_data.code))
    if not first_choice:
        await show_profile(callback, session, i18n, user, images)
    # При первом запуске следующий шаг — выбор темы, если тем больше одной.
    elif not await show_themes(callback, session, i18n, user, images, onboarding=True):
        await show(
            callback,
            main_menu_text(i18n, user),
            main_menu(i18n, user, settings),
            images.of(Screen.MAIN),
        )


async def on_theme_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    images: ThemeImages,
) -> None:
    await show_themes(callback, session, i18n, user, images, onboarding=False)


async def on_theme(
    callback: CallbackQuery,
    callback_data: ThemeCallback,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    settings: Settings,
) -> None:
    if await choose_theme(session, user, callback_data.theme_id) is None:
        await callback.answer(i18n("theme-unavailable"), show_alert=True)
        return
    # Картинки в апдейте — от прежней темы: берём картинки только что выбранной.
    images = await images_for(session, user)
    if callback_data.onboarding:
        await show(
            callback,
            main_menu_text(i18n, user),
            main_menu(i18n, user, settings),
            images.of(Screen.MAIN),
        )
    else:
        await show_profile(callback, session, i18n, user, images)


async def on_main_menu(
    callback: CallbackQuery,
    user: User,
    i18n: Translator,
    state: FSMContext,
    settings: Settings,
    images: ThemeImages,
) -> None:
    await state.clear()
    await show(
        callback,
        main_menu_text(i18n, user),
        main_menu(i18n, user, settings),
        images.of(Screen.MAIN),
    )


async def on_profile(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    images: ThemeImages,
) -> None:
    await show_profile(callback, session, i18n, user, images)


async def on_change_language(
    callback: CallbackQuery, i18n: Translator, images: ThemeImages
) -> None:
    await show(callback, i18n("choose-language"), language_keyboard(), images.of(Screen.PROFILE))


async def cmd_admin_denied(message: Message, user: User, i18n: Translator) -> None:
    # Сюда /admin доходит, только если IsAdmin не пропустил: подсказываем ID для ADMIN_IDS.
    await message.answer(i18n("admin-denied", id=str(user.id)))


def create_router() -> Router:
    router = Router(name="start")
    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_admin_denied, Command("admin"))
    router.callback_query.register(on_language, LanguageCallback.filter())
    router.callback_query.register(on_main_menu, MenuCallback.filter(F.action == MenuAction.MAIN))
    router.callback_query.register(on_profile, MenuCallback.filter(F.action == MenuAction.PROFILE))
    router.callback_query.register(
        on_change_language, MenuCallback.filter(F.action == MenuAction.LANGUAGE)
    )
    router.callback_query.register(on_theme_menu, MenuCallback.filter(F.action == MenuAction.THEME))
    router.callback_query.register(on_theme, ThemeCallback.filter())
    return router
