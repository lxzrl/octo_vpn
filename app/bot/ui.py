from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InputMediaPhoto, Message

# Подпись к фото в Telegram не длиннее 1024 символов: более длинный экран показываем без картинки.
CAPTION_LIMIT = 1024


def _fits(text: str, photo: str | None) -> str | None:
    return photo if photo and len(text) <= CAPTION_LIMIT else None


async def send_screen(
    message: Message, text: str, markup: InlineKeyboardMarkup, photo: str | None = None
) -> None:
    """Отправляет экран новым сообщением: с картинкой, если она задана, иначе текстом."""
    if photo := _fits(text, photo):
        await message.answer_photo(photo, caption=text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


async def show(
    callback: CallbackQuery,
    text: str,
    markup: InlineKeyboardMarkup,
    photo: str | None = None,
) -> None:
    """Перерисовывает экран в том же сообщении, а если это невозможно, присылает новое.

    Сообщение с фото можно перерисовать только в сообщение с фото, текст — только в текст.
    Иначе (например, админ только что добавил картинки) экран приходит новым сообщением.
    """
    photo = _fits(text, photo)
    message = callback.message
    try:
        if isinstance(message, Message) and photo and message.photo:
            await message.edit_media(
                InputMediaPhoto(media=photo, caption=text), reply_markup=markup
            )
        elif isinstance(message, Message) and not photo and message.text is not None:
            await message.edit_text(text, reply_markup=markup)
        elif isinstance(message, Message):
            await send_screen(message, text, markup, photo)
        elif message is not None and callback.bot is not None:
            # Старое недоступное сообщение: присылаем экран заново в тот же чат.
            if photo:
                await callback.bot.send_photo(
                    message.chat.id, photo, caption=text, reply_markup=markup
                )
            else:
                await callback.bot.send_message(message.chat.id, text, reply_markup=markup)
    except TelegramBadRequest as error:
        # Повторное нажатие той же кнопки: экран уже такой, это не ошибка.
        if "message is not modified" not in error.message:
            raise
    await callback.answer()
