from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def show(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    """Перерисовывает экран в том же сообщении, а если это невозможно, присылает новое."""
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest as error:
            # Повторное нажатие той же кнопки: экран уже такой, это не ошибка.
            if "message is not modified" not in error.message:
                raise
    elif callback.message is not None and callback.bot is not None:
        await callback.bot.send_message(callback.message.chat.id, text, reply_markup=markup)
    await callback.answer()
