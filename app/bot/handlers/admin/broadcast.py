from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.broadcast import Broadcaster, BroadcastReport
from app.bot.callbacks import AdminAction, AdminCallback
from app.bot.handlers.admin.common import AdminInput, back_keyboard, button, cancel_keyboard
from app.bot.ui import show
from app.i18n import TranslatorHub
from app.services.admin import Audience, audience_ids


async def on_broadcast(
    callback: CallbackQuery, session: AsyncSession, translators: TranslatorHub
) -> None:
    i18n = translators.admin
    builder = InlineKeyboardBuilder()
    for audience in Audience:
        count = len(await audience_ids(session, audience))
        button(
            builder,
            i18n(f"adm-audience-{audience.value}", count=count),
            AdminAction.BROADCAST_AUDIENCE,
            value=audience,
        )
    button(builder, i18n("adm-btn-back"), AdminAction.MENU)
    builder.adjust(1)
    await show(callback, i18n("adm-broadcast"), builder.as_markup())


async def on_audience(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    await state.set_state(AdminInput.broadcast)
    await state.set_data({"audience": Audience(callback_data.value).value})
    await show(callback, i18n("adm-broadcast-prompt"), cancel_keyboard(i18n, AdminAction.BROADCAST))


async def on_broadcast_message(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    translators: TranslatorHub,
    state: FSMContext,
) -> None:
    i18n = translators.admin
    audience = Audience((await state.get_data())["audience"])
    await state.clear()
    count = len(await audience_ids(session, audience))
    # Превью: так сообщение увидят получатели.
    await bot.copy_message(message.chat.id, message.chat.id, message.message_id)
    builder = InlineKeyboardBuilder()
    button(
        builder,
        i18n("adm-btn-broadcast-send", count=count),
        AdminAction.BROADCAST_SEND,
        message.message_id,
        audience,
    )
    button(builder, i18n("adm-btn-cancel"), AdminAction.BROADCAST)
    builder.adjust(1)
    await message.answer(
        i18n("adm-broadcast-confirm", audience=i18n(f"adm-audience-{audience.value}", count=count)),
        reply_markup=builder.as_markup(),
    )


async def on_broadcast_send(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    bot: Bot,
    session: AsyncSession,
    translators: TranslatorHub,
    broadcaster: Broadcaster,
) -> None:
    i18n = translators.admin
    assert callback.message is not None
    chat_id = callback.message.chat.id
    recipients = await audience_ids(session, Audience(callback_data.value))

    async def report(result: BroadcastReport) -> None:
        await bot.send_message(
            chat_id,
            i18n(
                "adm-broadcast-report",
                total=result.total,
                delivered=result.delivered,
                blocked=result.blocked,
                failed=result.failed,
            ),
            reply_markup=back_keyboard(i18n),
        )

    if not broadcaster.start(bot, recipients, chat_id, callback_data.id, report):
        await callback.answer(i18n("adm-broadcast-already"), show_alert=True)
        return
    await show(callback, i18n("adm-broadcast-started", count=len(recipients)), back_keyboard(i18n))


def create_router() -> Router:
    router = Router(name="admin-broadcast")
    action = AdminCallback.filter
    router.callback_query.register(on_broadcast, action(F.action == AdminAction.BROADCAST))
    router.callback_query.register(on_audience, action(F.action == AdminAction.BROADCAST_AUDIENCE))
    router.callback_query.register(
        on_broadcast_send, action(F.action == AdminAction.BROADCAST_SEND)
    )
    router.message.register(
        on_broadcast_message, StateFilter(AdminInput.broadcast), ~F.text.startswith("/")
    )
    return router
