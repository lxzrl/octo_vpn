import html

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import LanguageCallback, MenuAction, MenuCallback
from app.bot.keyboards import language_keyboard, main_menu_keyboard, profile_keyboard
from app.bot.ui import show
from app.db.models import User
from app.i18n import Translator, TranslatorHub
from app.services.money import rub
from app.services.users import set_language


def main_menu_text(i18n: Translator, user: User) -> str:
    # Режим разметки HTML: имя из Telegram может содержать < и &.
    return i18n("main-menu", name=html.escape(user.first_name))


def profile_text(i18n: Translator, user: User) -> str:
    return i18n(
        "profile",
        id=str(user.id),
        registered=user.created_at.strftime("%d.%m.%Y"),
        language=i18n("language-name"),
        balance=rub(user.balance_kop),
    )


async def cmd_start(message: Message, user: User, i18n: Translator, state: FSMContext) -> None:
    await state.clear()
    if user.language is None:
        await message.answer(i18n("choose-language"), reply_markup=language_keyboard())
        return
    await message.answer(main_menu_text(i18n, user), reply_markup=main_menu_keyboard(i18n))


async def on_language(
    callback: CallbackQuery,
    callback_data: LanguageCallback,
    user: User,
    translators: TranslatorHub,
) -> None:
    first_choice = user.language is None
    i18n = translators.get(set_language(user, callback_data.code))
    if first_choice:
        await show(callback, main_menu_text(i18n, user), main_menu_keyboard(i18n))
    else:
        await show(callback, profile_text(i18n, user), profile_keyboard(i18n))


async def on_main_menu(callback: CallbackQuery, user: User, i18n: Translator) -> None:
    await show(callback, main_menu_text(i18n, user), main_menu_keyboard(i18n))


async def on_profile(callback: CallbackQuery, user: User, i18n: Translator) -> None:
    await show(callback, profile_text(i18n, user), profile_keyboard(i18n))


async def on_change_language(callback: CallbackQuery, i18n: Translator) -> None:
    await show(callback, i18n("choose-language"), language_keyboard())


async def on_not_ready(callback: CallbackQuery, i18n: Translator) -> None:
    await callback.answer(i18n("coming-soon"), show_alert=True)


def create_router() -> Router:
    router = Router(name="start")
    router.message.register(cmd_start, CommandStart())
    router.callback_query.register(on_language, LanguageCallback.filter())
    router.callback_query.register(on_main_menu, MenuCallback.filter(F.action == MenuAction.MAIN))
    router.callback_query.register(on_profile, MenuCallback.filter(F.action == MenuAction.PROFILE))
    router.callback_query.register(
        on_change_language, MenuCallback.filter(F.action == MenuAction.LANGUAGE)
    )
    # Поддержка появится на этапе 4.
    router.callback_query.register(on_not_ready, MenuCallback.filter())
    return router
