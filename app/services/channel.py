import logging

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

SUBSCRIBED = {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER}


class ChannelCheckError(Exception):
    """Не удалось проверить подписку: обычно бот не добавлен в канал администратором."""


async def is_subscribed(bot: Bot, channel: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(channel, user_id)
    except TelegramAPIError as error:
        logger.error("Не удалось проверить подписку на %s: %s", channel, error)
        raise ChannelCheckError(str(error)) from error
    if member.status == ChatMemberStatus.RESTRICTED:
        return bool(getattr(member, "is_member", False))
    return member.status in SUBSCRIBED


async def bot_channel_problem(bot: Bot, channel: str) -> str | None:
    """Почему бот не сможет проверять подписку на канал; None — всё в порядке."""
    try:
        me = await bot.me()
        member = await bot.get_chat_member(channel, me.id)
    except TelegramAPIError as error:
        return str(error)
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
        status = ChatMemberStatus(member.status).value
        return f"бот в канале со статусом «{status}», а нужен администратор"
    return None
