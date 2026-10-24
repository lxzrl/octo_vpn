from urllib.parse import quote

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import MenuAction, MenuCallback
from app.bot.keyboards import referral_keyboard
from app.bot.ui import show
from app.db.models import User
from app.i18n import Translator
from app.services.money import rub
from app.services.options import Options
from app.services.referrals import referral_stats
from app.services.users import referral_link


async def on_referrals(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    user: User,
    i18n: Translator,
    options: Options,
) -> None:
    me = await bot.me()
    link = referral_link(me.username or "", user.id)
    stats = await referral_stats(session, user.id)
    text = i18n(
        "referral",
        link=link,
        first=options.referral_first_percent,
        next=options.referral_next_percent,
        invited=stats.invited,
        earned=rub(stats.earned_kop),
        balance=rub(user.balance_kop),
    )
    share_url = (
        f"https://t.me/share/url?url={quote(link)}&text={quote(i18n('referral-share-text'))}"
    )
    await show(callback, text, referral_keyboard(i18n, share_url))


def create_router() -> Router:
    router = Router(name="referral")
    router.callback_query.register(
        on_referrals, MenuCallback.filter(F.action == MenuAction.REFERRALS)
    )
    return router
