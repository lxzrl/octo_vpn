"""Оформление бота: темы (наборы картинок к экранам) и картинки в них."""

import html

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    Document,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import AdminAction, AdminCallback
from app.bot.handlers.admin.common import AdminInput, button, cancel_keyboard
from app.bot.ui import send_screen, show
from app.db.models import Theme
from app.i18n import Translator, TranslatorHub
from app.services.themes import (
    DEFAULT_THEME,
    NAME_MAX,
    Screen,
    all_themes,
    create_theme,
    delete_theme,
    set_theme_image,
    theme_images,
)

CONFIRM = "ok"
# Картинки файлом: форматы, которые Telegram принимает как фото, и его лимит на фото.
IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
PHOTO_MAX_BYTES = 10 * 1024 * 1024


def design_keyboard(i18n: Translator, themes: list[tuple[Theme, int]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for theme, count in themes:
        mark = "" if theme.is_active else "🙈 "
        text = f"{mark}{theme.name} · 🖼 {count}/{len(Screen)}"
        button(builder, text, AdminAction.THEME, theme.id)
    button(builder, i18n("adm-btn-theme-new"), AdminAction.THEME_NEW)
    button(builder, i18n("adm-btn-back"), AdminAction.MENU)
    builder.adjust(1)
    return builder.as_markup()


async def design_screen(
    session: AsyncSession, i18n: Translator
) -> tuple[str, InlineKeyboardMarkup]:
    themes = [
        (theme, len(await theme_images(session, theme.id))) for theme in await all_themes(session)
    ]
    return i18n("adm-design"), design_keyboard(i18n, themes)


def theme_keyboard(i18n: Translator, theme: Theme, images: dict[str, str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for screen in Screen:
        mark = "✅" if screen in images else "➖"
        text = f"{mark} {i18n(f'adm-screen-{screen.value}')}"
        button(builder, text, AdminAction.IMAGE, theme.id, screen)
    sizes = [2] * ((len(Screen) + 1) // 2)
    if theme.code != DEFAULT_THEME:
        key = "adm-btn-theme-hide" if theme.is_active else "adm-btn-theme-show"
        button(builder, i18n(key), AdminAction.THEME_TOGGLE, theme.id)
        sizes.append(1)
    if theme.code is None:
        button(builder, i18n("adm-btn-theme-delete"), AdminAction.THEME_DELETE, theme.id)
        sizes.append(1)
    button(builder, i18n("adm-btn-back"), AdminAction.DESIGN)
    builder.adjust(*sizes, 1)
    return builder.as_markup()


async def theme_screen(
    session: AsyncSession, i18n: Translator, theme: Theme
) -> tuple[str, InlineKeyboardMarkup]:
    images = await theme_images(session, theme.id)
    if theme.code == DEFAULT_THEME:
        status = i18n("adm-theme-default")
    else:
        status = i18n("adm-theme-active" if theme.is_active else "adm-theme-hidden")
    text = i18n(
        "adm-theme",
        name=html.escape(theme.name),
        name_en=html.escape(theme.name_en),
        status=status,
    )
    return text, theme_keyboard(i18n, theme, images)


def image_keyboard(
    i18n: Translator, theme_id: int, screen: Screen, has_image: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_image:
        button(builder, i18n("adm-btn-image-remove"), AdminAction.IMAGE_REMOVE, theme_id, screen)
    button(builder, i18n("adm-btn-back"), AdminAction.THEME, theme_id)
    builder.adjust(1)
    return builder.as_markup()


def image_text(i18n: Translator, theme: Theme, screen: Screen, has_image: bool) -> str:
    return i18n(
        "adm-image",
        theme=html.escape(theme.name),
        screen=i18n(f"adm-screen-{screen.value}"),
        status=i18n("adm-image-set" if has_image else "adm-image-empty"),
    )


async def _theme(
    callback: CallbackQuery, session: AsyncSession, i18n: Translator, theme_id: int
) -> Theme | None:
    theme = await session.get(Theme, theme_id)
    if theme is None:
        await callback.answer(i18n("adm-not-found"), show_alert=True)
    return theme


async def on_design(
    callback: CallbackQuery, session: AsyncSession, translators: TranslatorHub
) -> None:
    await show(callback, *await design_screen(session, translators.admin))


async def on_theme(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
) -> None:
    i18n = translators.admin
    if theme := await _theme(callback, session, i18n, callback_data.id):
        await show(callback, *await theme_screen(session, i18n, theme))


async def on_theme_toggle(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
) -> None:
    i18n = translators.admin
    theme = await _theme(callback, session, i18n, callback_data.id)
    if theme is None:
        return
    # Тему по умолчанию не скрыть: иначе у части пользователей не будет никакой темы.
    if theme.code != DEFAULT_THEME:
        theme.is_active = not theme.is_active
        await session.flush()
    await show(callback, *await theme_screen(session, i18n, theme))


async def on_theme_delete(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
) -> None:
    i18n = translators.admin
    theme = await _theme(callback, session, i18n, callback_data.id)
    if theme is None or theme.code is not None:
        return
    if callback_data.value != CONFIRM:
        builder = InlineKeyboardBuilder()
        button(
            builder,
            i18n("adm-btn-theme-delete-confirm"),
            AdminAction.THEME_DELETE,
            theme.id,
            CONFIRM,
        )
        button(builder, i18n("adm-btn-cancel"), AdminAction.THEME, theme.id)
        builder.adjust(1)
        await show(
            callback,
            i18n("adm-theme-delete-confirm", name=html.escape(theme.name)),
            builder.as_markup(),
        )
        return
    await delete_theme(session, theme)
    await callback.answer(i18n("adm-theme-deleted"))
    await show(callback, *await design_screen(session, i18n))


async def on_theme_new(
    callback: CallbackQuery, translators: TranslatorHub, state: FSMContext
) -> None:
    i18n = translators.admin
    await state.set_state(AdminInput.theme_name)
    await show(callback, i18n("adm-theme-name-prompt"), cancel_keyboard(i18n, AdminAction.DESIGN))


async def on_theme_name(message: Message, translators: TranslatorHub, state: FSMContext) -> None:
    i18n = translators.admin
    name = (message.text or "").strip()
    if not name or len(name) > NAME_MAX:
        await message.answer(
            i18n("adm-theme-name-prompt"), reply_markup=cancel_keyboard(i18n, AdminAction.DESIGN)
        )
        return
    await state.set_state(AdminInput.theme_name_en)
    await state.set_data({"name": name})
    await message.answer(
        i18n("adm-theme-name-en-prompt"), reply_markup=cancel_keyboard(i18n, AdminAction.DESIGN)
    )


async def on_theme_name_en(
    message: Message, session: AsyncSession, translators: TranslatorHub, state: FSMContext
) -> None:
    i18n = translators.admin
    name_en = (message.text or "").strip()
    if not name_en or len(name_en) > NAME_MAX:
        await message.answer(
            i18n("adm-theme-name-en-prompt"), reply_markup=cancel_keyboard(i18n, AdminAction.DESIGN)
        )
        return
    name = (await state.get_data())["name"]
    await state.clear()
    theme = await create_theme(session, name, name if name_en == "-" else name_en)
    text, markup = await theme_screen(session, i18n, theme)
    await message.answer(f"{i18n('adm-theme-created')}\n\n{text}", reply_markup=markup)


async def on_image(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    theme = await _theme(callback, session, i18n, callback_data.id)
    if theme is None:
        return
    screen = Screen(callback_data.value)
    photo = (await theme_images(session, theme.id)).get(screen)
    # Пока открыт этот экран, присланное фото станет его картинкой.
    await state.set_state(AdminInput.image)
    await state.set_data({"theme_id": theme.id, "screen": screen.value})
    await show(
        callback,
        image_text(i18n, theme, screen, photo is not None),
        image_keyboard(i18n, theme.id, screen, photo is not None),
        photo,
    )


async def on_image_remove(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    session: AsyncSession,
    translators: TranslatorHub,
) -> None:
    i18n = translators.admin
    theme = await _theme(callback, session, i18n, callback_data.id)
    if theme is None:
        return
    await set_theme_image(session, theme.id, Screen(callback_data.value), None)
    await callback.answer(i18n("adm-image-removed"))
    # Сообщение с фото в текст не превратить: экран темы придёт новым сообщением.
    await show(callback, *await theme_screen(session, i18n, theme))


def is_image_file(document: Document | None) -> bool:
    return document is not None and (document.mime_type or "") in IMAGE_TYPES


async def reupload_as_photo(
    bot: Bot, message: Message, caption: str, markup: InlineKeyboardMarkup
) -> str | None:
    """Картинка, присланная файлом: показать её над экраном можно только как фото.

    Скачиваем файл и отправляем его админу фотографией — file_id этого фото и сохраняем.
    None — файл не подошёл (слишком большой или Telegram не принял его как фото).
    """
    document = message.document
    assert document is not None
    if (document.file_size or 0) > PHOTO_MAX_BYTES:
        return None
    try:
        data = await bot.download(document)
        assert data is not None
        sent = await message.answer_photo(
            BufferedInputFile(data.read(), document.file_name or "image"),
            caption=caption,
            reply_markup=markup,
        )
    except TelegramBadRequest:
        return None
    return sent.photo[-1].file_id if sent.photo else None


async def on_image_upload(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    data = await state.get_data()
    theme = await session.get(Theme, int(data["theme_id"]))
    screen = Screen(data["screen"])
    if theme is None:
        await state.clear()
        await message.answer(i18n("adm-not-found"))
        return
    text = f"{i18n('adm-image-saved')}\n\n{image_text(i18n, theme, screen, True)}"
    markup = image_keyboard(i18n, theme.id, screen, True)
    photo: str | None
    if message.photo:
        photo = message.photo[-1].file_id
        await send_screen(message, text, markup, photo)
    elif is_image_file(message.document):
        photo = await reupload_as_photo(bot, message, text, markup)
        if photo is None:
            await message.answer(i18n("adm-image-bad-file"))
            return
    else:
        await message.answer(i18n("adm-image-not-photo"))
        return
    await set_theme_image(session, theme.id, screen, photo)


def create_router() -> Router:
    router = Router(name="admin-design")
    action = AdminCallback.filter
    router.callback_query.register(on_design, action(F.action == AdminAction.DESIGN))
    router.callback_query.register(on_theme, action(F.action == AdminAction.THEME))
    router.callback_query.register(on_theme_toggle, action(F.action == AdminAction.THEME_TOGGLE))
    router.callback_query.register(on_theme_delete, action(F.action == AdminAction.THEME_DELETE))
    router.callback_query.register(on_theme_new, action(F.action == AdminAction.THEME_NEW))
    router.callback_query.register(on_image, action(F.action == AdminAction.IMAGE))
    router.callback_query.register(on_image_remove, action(F.action == AdminAction.IMAGE_REMOVE))
    not_command = ~F.text.startswith("/")
    router.message.register(on_theme_name, StateFilter(AdminInput.theme_name), F.text, not_command)
    router.message.register(
        on_theme_name_en, StateFilter(AdminInput.theme_name_en), F.text, not_command
    )
    router.message.register(on_image_upload, StateFilter(AdminInput.image), not_command)
    return router
