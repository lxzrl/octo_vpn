from datetime import timedelta

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerCallbackQuery, CopyMessage, SendMessage
from aiogram.types import InlineKeyboardMarkup, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.broadcast import Broadcaster
from app.bot.callbacks import (
    AdminAction,
    AdminCallback,
    LanguageCallback,
    MenuAction,
    MenuCallback,
    PayCallback,
    PlanCallback,
)
from app.config import Settings
from app.db.models import (
    BalanceTransaction,
    Plan,
    PromoCode,
    PromoKind,
    Subscription,
    Ticket,
    TicketMessage,
    TicketStatus,
)
from app.db.models import User as DbUser
from app.i18n import TranslatorHub
from app.main import build_dispatcher
from app.services.clock import as_utc, utcnow
from tests.fakes import TG_USER, FakePanel, FakeSession, callback, message, photo, sent_to

ADMIN = TG_USER
BOB = User(id=200, is_bot=False, first_name="Bob", username="bob_vpn", language_code="en")


@pytest.fixture
def fake() -> FakeSession:
    return FakeSession()


@pytest.fixture
def bot(fake: FakeSession) -> Bot:
    return Bot("42:TEST", session=fake)


@pytest.fixture
def panel() -> FakePanel:
    return FakePanel()


@pytest.fixture
def broadcaster(session_factory: async_sessionmaker[AsyncSession]) -> Broadcaster:
    return Broadcaster(session_factory, delay_seconds=0)


@pytest.fixture
def dp(
    session_factory: async_sessionmaker[AsyncSession],
    panel: FakePanel,
    broadcaster: Broadcaster,
) -> Dispatcher:
    settings = Settings(bot_token="42:TEST", admin_ids=str(ADMIN.id), trial_channel=None)
    return build_dispatcher(
        settings, session_factory, TranslatorHub("ru"), panel, broadcaster=broadcaster
    )


def adm(action: AdminAction, id: int = 0, value: str = "") -> str:
    return AdminCallback(action=action, id=id, value=value).pack()


def menu(action: MenuAction) -> str:
    return MenuCallback(action=action).pack()


async def register(dp: Dispatcher, bot: Bot, user: User, language: str = "ru") -> None:
    await dp.feed_update(bot, message("/start", user))
    await dp.feed_update(bot, callback(LanguageCallback(code=language).pack(), user))


def last(fake: FakeSession, chat_id: int = ADMIN.id) -> str:
    return sent_to(fake, chat_id)[-1] if sent_to(fake, chat_id) else ""


def last_screen(fake: FakeSession) -> str:
    """Последний текст: новое сообщение или перерисованный экран."""
    for call in reversed(fake.calls):
        text = getattr(call, "text", None)
        if isinstance(text, str):
            return text
    return ""


def buttons(fake: FakeSession) -> list[str]:
    for call in reversed(fake.calls):
        markup = getattr(call, "reply_markup", None)
        if isinstance(markup, InlineKeyboardMarkup):
            return [b.text for row in markup.inline_keyboard for b in row]
    return []


async def test_admin_menu_only_for_admins(dp: Dispatcher, bot: Bot, fake: FakeSession) -> None:
    await register(dp, bot, BOB)
    assert "🛠 Админка" not in buttons(fake)
    fake.calls.clear()
    await dp.feed_update(bot, message("/admin", BOB))
    # Вместо админки — подсказка с ID для ADMIN_IDS.
    assert sent_to(fake, BOB.id) == [
        "Админка доступна только тем, чей ID указан в ADMIN_IDS. Ваш Telegram ID: <code>200</code>"
    ]
    await dp.feed_update(bot, callback(adm(AdminAction.STATS), BOB))
    assert "Статистика" not in last_screen(fake)

    await register(dp, bot, ADMIN)
    assert "🛠 Админка" in buttons(fake)
    await dp.feed_update(bot, message("/admin"))
    assert "Админка" in last(fake)
    await dp.feed_update(bot, callback(adm(AdminAction.STATS)))
    assert "Пользователей: 2" in last_screen(fake)


async def test_user_card_extend_balance_ban(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    panel: FakePanel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register(dp, bot, BOB, "en")
    await register(dp, bot, ADMIN)

    await dp.feed_update(bot, callback(adm(AdminAction.FIND_USER)))
    await dp.feed_update(bot, message("@nobody"))
    assert "не найден" in last(fake)
    await dp.feed_update(bot, message("@Bob_VPN"))
    assert "Bob" in last(fake) and "Подписка: нет" in last(fake)

    await dp.feed_update(bot, callback(adm(AdminAction.EXTEND, BOB.id)))
    await dp.feed_update(bot, message("0"))
    assert "от 1 до 3650" in last(fake)
    await dp.feed_update(bot, message("10"))
    assert "Подписка продлена" in last(fake)
    assert "You got 10 days" in last(fake, BOB.id)
    assert len(panel.users) == 1

    await dp.feed_update(bot, callback(adm(AdminAction.BALANCE, BOB.id)))
    await dp.feed_update(bot, message("-5"))
    assert "Нельзя списать" in last(fake)
    await dp.feed_update(bot, message("150,50"))
    assert "Баланс теперь 150,50 ₽" in last(fake)
    assert "150,50 ₽ has been added" in last(fake, BOB.id)

    await dp.feed_update(bot, callback(adm(AdminAction.BAN, BOB.id)))
    assert "Забанен" in last_screen(fake)
    await dp.feed_update(bot, callback(adm(AdminAction.BAN, ADMIN.id)))
    answer = fake.calls[-1]
    assert isinstance(answer, AnswerCallbackQuery) and answer.show_alert

    async with session_factory() as session:
        bob = await session.get(DbUser, BOB.id)
        assert bob is not None and bob.is_banned and bob.balance_kop == 15050
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == BOB.id))
        assert sub is not None and not sub.is_trial
        assert as_utc(sub.expires_at) > utcnow() + timedelta(days=9)
        ledger = list(await session.scalars(select(BalanceTransaction)))
        assert [t.operation for t in ledger] == ["admin"]


async def test_cancel_button_drops_input(dp: Dispatcher, bot: Bot, fake: FakeSession) -> None:
    await register(dp, bot, ADMIN)
    await dp.feed_update(bot, callback(adm(AdminAction.FIND_USER)))
    await dp.feed_update(bot, callback(adm(AdminAction.MENU)))
    fake.calls.clear()
    await dp.feed_update(bot, message("100"))
    # Ввод отменён: текст больше не воспринимается как поиск.
    assert not any("ID:" in text or "не найден" in text for text in sent_to(fake, ADMIN.id))


async def test_set_plan_price_makes_it_buyable(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session:
        session.add(Plan(months=1, days=30, price_rub=None))
        await session.commit()
    await register(dp, bot, ADMIN)
    await dp.feed_update(bot, callback(MenuCallback(action=MenuAction.BUY).pack()))
    assert "1 мес" not in " ".join(buttons(fake))

    await dp.feed_update(bot, callback(adm(AdminAction.PLAN_PRICE, 1)))
    await dp.feed_update(bot, message("abc"))
    assert "целое число" in last(fake)
    await dp.feed_update(bot, message("199"))
    assert "Виден покупателям" in last(fake)

    await dp.feed_update(bot, callback(MenuCallback(action=MenuAction.BUY).pack()))
    assert any("199 ₽" in text for text in buttons(fake))

    await dp.feed_update(bot, callback(adm(AdminAction.PLAN_TOGGLE, 1)))
    assert "Скрыт" in last_screen(fake)


async def test_create_promo_with_wizard(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await register(dp, bot, ADMIN)
    await register(dp, bot, BOB, "en")
    await dp.feed_update(bot, callback(adm(AdminAction.PROMO_NEW)))
    await dp.feed_update(bot, callback(adm(AdminAction.PROMO_KIND, value=PromoKind.BALANCE)))
    await dp.feed_update(bot, message("50"))
    await dp.feed_update(bot, message("2"))  # лимит активаций
    await dp.feed_update(bot, callback(adm(AdminAction.PROMO_SKIP)))  # бессрочно
    await dp.feed_update(bot, message("bad code!"))
    assert "латиница" in last(fake)
    await dp.feed_update(bot, message("bonus50"))
    assert "Промокод создан" in last(fake) and "BONUS50" in last(fake)

    # Тот же код второй раз создать нельзя.
    await dp.feed_update(bot, callback(adm(AdminAction.PROMO_NEW)))
    await dp.feed_update(bot, callback(adm(AdminAction.PROMO_KIND, value=PromoKind.DAYS)))
    await dp.feed_update(bot, message("7"))
    await dp.feed_update(bot, callback(adm(AdminAction.PROMO_SKIP)))
    await dp.feed_update(bot, callback(adm(AdminAction.PROMO_SKIP)))
    await dp.feed_update(bot, message("BONUS50"))
    assert "уже есть" in last(fake)
    await dp.feed_update(bot, callback(adm(AdminAction.PROMO_SKIP)))
    assert "Промокод создан" in last_screen(fake)

    async with session_factory() as session:
        promos = list(await session.scalars(select(PromoCode).order_by(PromoCode.id)))
        assert [(p.code, p.kind, p.value, p.max_uses) for p in promos[:1]] == [
            ("BONUS50", "balance", 5000, 2)
        ]
        assert promos[1].kind == "days" and promos[1].max_uses is None and len(promos[1].code) == 8

    await dp.feed_update(bot, callback(menu(MenuAction.PROMO), BOB))
    await dp.feed_update(bot, message("bonus50", BOB))
    assert "50 ₽" in last(fake, BOB.id)


async def test_options_change_trial_and_rate(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session:
        session.add(Plan(months=1, days=30, price_rub=150))
        await session.commit()
    await register(dp, bot, ADMIN)
    await register(dp, bot, BOB)

    await dp.feed_update(bot, callback(adm(AdminAction.OPTION, value="stars_rub_rate")))
    await dp.feed_update(bot, message("0"))
    assert "Сколько рублей стоит одна звезда" in last(fake)
    await dp.feed_update(bot, message("3"))
    assert "1 звезда = 3 ₽" in last(fake)

    await dp.feed_update(bot, callback(adm(AdminAction.TRIAL_TOGGLE)))
    assert "Пробный период: выключен" in last_screen(fake)

    await dp.feed_update(bot, callback(PlanCallback(plan_id=1).pack(), BOB))
    assert "50 ⭐" in last_screen(fake)

    await dp.feed_update(bot, callback(menu(MenuAction.SUBSCRIPTION), BOB))
    assert "Попробовать бесплатно" not in buttons(fake)
    await dp.feed_update(bot, callback(menu(MenuAction.TRIAL), BOB))
    answer = fake.calls[-1]
    assert (
        isinstance(answer, AnswerCallbackQuery)
        and answer.text == "Пробный период сейчас недоступен"
    )


async def test_support_ticket_round_trip(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await register(dp, bot, ADMIN)
    await register(dp, bot, BOB, "en")

    await dp.feed_update(bot, callback(menu(MenuAction.SUPPORT), BOB))
    assert "Describe the problem" in last_screen(fake)
    await dp.feed_update(bot, callback(menu(MenuAction.SUPPORT_WRITE), BOB))
    await dp.feed_update(bot, photo("It <does not> connect", BOB))
    assert "sent to support" in last(fake, BOB.id)
    notice = last(fake, ADMIN.id)
    assert "Новое обращение #1" in notice and "&lt;does not&gt;" in notice

    await dp.feed_update(bot, callback(adm(AdminAction.TICKET_REPLY, 1)))
    await dp.feed_update(bot, message("Reinstall the app"))
    assert "Ответ отправлен" in last(fake)
    assert "Support reply" in last(fake, BOB.id) and "Reinstall the app" in last(fake, BOB.id)

    await dp.feed_update(bot, callback(menu(MenuAction.SUPPORT_WRITE), BOB))
    await dp.feed_update(bot, message("Thanks, works", BOB))
    assert "Сообщение в обращении #1" in last(fake, ADMIN.id)

    await dp.feed_update(bot, callback(menu(MenuAction.SUPPORT), BOB))
    history = last_screen(fake)
    assert "Request #1" in history and "🖼" in history and "Reinstall" in history

    await dp.feed_update(bot, callback(adm(AdminAction.TICKET_CLOSE, 1)))
    assert "Request #1 is closed" in last(fake, BOB.id)

    async with session_factory() as session:
        ticket = await session.get(Ticket, 1)
        assert ticket is not None and ticket.status == TicketStatus.CLOSED
        texts = list(await session.scalars(select(TicketMessage.from_admin)))
        assert texts == [False, True, False]

    # После закрытия следующее сообщение открывает новое обращение.
    await dp.feed_update(bot, callback(menu(MenuAction.SUPPORT_WRITE), BOB))
    await dp.feed_update(bot, message("One more thing", BOB))
    assert "Новое обращение #2" in last(fake, ADMIN.id)


async def test_broadcast_with_preview_and_report(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    broadcaster: Broadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    eve = User(id=300, is_bot=False, first_name="Eve")
    await register(dp, bot, ADMIN)
    await register(dp, bot, BOB)
    await register(dp, bot, eve)
    fake.blocked.add(eve.id)

    await dp.feed_update(bot, callback(adm(AdminAction.BROADCAST)))
    assert "Всем (3)" in buttons(fake)
    await dp.feed_update(bot, callback(adm(AdminAction.BROADCAST_AUDIENCE, value="all")))
    update = message("Big news")
    await dp.feed_update(bot, update)
    assert update.message is not None
    preview = [c for c in fake.calls if isinstance(c, CopyMessage)]
    assert [c.chat_id for c in preview] == [ADMIN.id]

    send = adm(AdminAction.BROADCAST_SEND, update.message.message_id, "all")
    await dp.feed_update(bot, callback(send))
    await dp.feed_update(bot, callback(send))
    answer = fake.calls[-1]
    assert isinstance(answer, AnswerCallbackQuery) and answer.show_alert
    await broadcaster.join()

    copies = [c.chat_id for c in fake.calls if isinstance(c, CopyMessage)][1:]
    assert sorted(copies) == [ADMIN.id, BOB.id, eve.id]
    report = [c for c in fake.calls if isinstance(c, SendMessage)][-1].text
    assert "Доставлено: 2 из 3" in report and "Заблокировали бота: 1" in report

    async with session_factory() as session:
        stored = await session.get(DbUser, eve.id)
        assert stored is not None and stored.is_blocked_bot


async def test_admins_are_notified_about_payments(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await register(dp, bot, ADMIN)
    await register(dp, bot, BOB)
    async with session_factory() as session:
        session.add(Plan(months=1, days=30, price_rub=100))
        bob = await session.get(DbUser, BOB.id)
        assert bob is not None
        bob.balance_kop = 10000
        await session.commit()

    await dp.feed_update(bot, callback(PayCallback(plan_id=1).pack(), BOB))
    notice = last(fake)
    assert "Оплата #1" in notice and "Bob" in notice and "С баланса: 100 ₽" in notice


async def test_second_admin_from_comma_separated_ids(
    session_factory: async_sessionmaker[AsyncSession], bot: Bot, fake: FakeSession, panel: FakePanel
) -> None:
    settings = Settings(bot_token="42:TEST", admin_ids=f"{ADMIN.id}, {BOB.id}", trial_channel=None)
    dp = build_dispatcher(settings, session_factory, TranslatorHub("ru"), panel)
    await register(dp, bot, BOB)
    assert "🛠 Админка" in buttons(fake)
    await dp.feed_update(bot, message("/admin", BOB))
    assert "Админка" in sent_to(fake, BOB.id)[-1]
