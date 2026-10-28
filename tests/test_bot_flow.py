from datetime import UTC, datetime

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import (
    AnswerCallbackQuery,
    AnswerPreCheckoutQuery,
    EditMessageText,
    SendInvoice,
    SendMessage,
)
from aiogram.types import (
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
    SuccessfulPayment,
    Update,
    User,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.callbacks import (
    LanguageCallback,
    MenuAction,
    MenuCallback,
    PayCallback,
    PlanCallback,
    Platform,
    PlatformCallback,
)
from app.config import Settings
from app.db.models import Payment, PaymentStatus, Plan, PromoCode, PromoKind, Subscription
from app.db.models import User as DbUser
from app.i18n import TranslatorHub
from app.main import build_dispatcher
from app.vpn.demo import DemoPanel
from tests.fakes import (
    CHAT,
    TG_USER,
    FakePanel,
    FakeSession,
    callback,
    ids,
    message,
    sent_to,
)


@pytest.fixture
def fake() -> FakeSession:
    return FakeSession()


@pytest.fixture
def bot(fake: FakeSession) -> Bot:
    return Bot("42:TEST", session=fake)


@pytest.fixture
def settings() -> Settings:
    return Settings(bot_token="42:TEST", trial_channel=None)


@pytest.fixture
def panel() -> FakePanel:
    return FakePanel()


@pytest.fixture
def dp(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession], panel: FakePanel
) -> Dispatcher:
    return build_dispatcher(settings, session_factory, TranslatorHub("ru"), panel)


def menu(action: MenuAction) -> Update:
    return callback(MenuCallback(action=action).pack())


async def registered(dp: Dispatcher, bot: Bot) -> None:
    await dp.feed_update(bot, message("/start"))
    await dp.feed_update(bot, callback(LanguageCallback(code="ru").pack()))


def last_text(fake: FakeSession) -> str:
    sent = [c for c in fake.calls if isinstance(c, SendMessage | EditMessageText)]
    return sent[-1].text


async def test_first_start_asks_language_then_shows_menu(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await dp.feed_update(bot, message("/start"))
    assert "Выберите язык" in last_text(fake)

    await dp.feed_update(bot, callback(LanguageCallback(code="en").pack()))
    assert "Hi, Alice" in last_text(fake)

    async with session_factory() as session:
        user = await session.get(DbUser, TG_USER.id)
        assert user is not None and user.language == "en"

    await dp.feed_update(bot, message("/start"))
    assert "Hi, Alice" in last_text(fake)


async def test_change_language_from_profile(dp: Dispatcher, bot: Bot, fake: FakeSession) -> None:
    await dp.feed_update(bot, message("/start"))
    await dp.feed_update(bot, callback(LanguageCallback(code="ru").pack()))
    await dp.feed_update(bot, callback(MenuCallback(action=MenuAction.PROFILE).pack()))
    assert "Профиль" in last_text(fake) and "Русский" in last_text(fake)

    await dp.feed_update(bot, callback(MenuCallback(action=MenuAction.LANGUAGE).pack()))
    await dp.feed_update(bot, callback(LanguageCallback(code="en").pack()))
    assert "Profile" in last_text(fake) and "English" in last_text(fake)


async def test_referral_start_payload(
    dp: Dispatcher, bot: Bot, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session:
        session.add(DbUser(id=7, first_name="Ref"))
        await session.commit()

    await dp.feed_update(bot, message("/start ref_7"))

    async with session_factory() as session:
        user = await session.get(DbUser, TG_USER.id)
        assert user is not None and user.referrer_id == 7


async def test_banned_user_is_ignored(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session:
        session.add(DbUser(id=TG_USER.id, first_name="Alice", is_banned=True))
        await session.commit()

    await dp.feed_update(bot, message("/start"))
    assert fake.calls == []


async def test_name_with_html_chars_is_escaped(dp: Dispatcher, bot: Bot, fake: FakeSession) -> None:
    user = User(id=101, is_bot=False, first_name="<Bob & Co>")
    await dp.feed_update(bot, message("/start", user))
    await dp.feed_update(bot, callback(LanguageCallback(code="en").pack(), user))
    assert "&lt;Bob &amp; Co&gt;" in last_text(fake)


async def test_trial_flow(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    panel: FakePanel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await registered(dp, bot)
    await dp.feed_update(bot, menu(MenuAction.SUBSCRIPTION))
    assert "нет подписки" in last_text(fake) and "3 дня" in last_text(fake)

    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    text = last_text(fake)
    assert "Пробный период активирован" in text and "https://sub.example/tg_100" in text
    assert len(panel.users) == 1

    async with session_factory() as session:
        sub = await session.get(Subscription, 1)
        assert sub is not None and sub.is_trial

    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    answer = fake.calls[-1]
    assert isinstance(answer, AnswerCallbackQuery) and answer.show_alert
    assert len(panel.users) == 1


async def test_trial_requires_channel(
    settings: Settings, dp: Dispatcher, bot: Bot, fake: FakeSession, panel: FakePanel
) -> None:
    settings.trial_channel = "@octo_news"
    await registered(dp, bot)

    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    assert "подпишитесь на наш канал" in last_text(fake)
    assert panel.users == {}

    fake.channel_member = True
    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    assert "Пробный период активирован" in last_text(fake)


async def test_trial_channel_check_failure_is_reported_to_admins(
    session_factory: async_sessionmaker[AsyncSession],
    bot: Bot,
    fake: FakeSession,
    panel: FakePanel,
) -> None:
    settings = Settings(bot_token="42:TEST", admin_ids="7", trial_channel="@octo_news")
    dp = build_dispatcher(settings, session_factory, TranslatorHub("ru"), panel)
    fake.channel_error = "Bad Request: member list is inaccessible"
    await registered(dp, bot)

    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    assert any(isinstance(c, AnswerCallbackQuery) and c.show_alert for c in fake.calls)
    alert = sent_to(fake, 7)[-1]
    assert "@octo_news" in alert and "member list is inaccessible" in alert
    assert "администратор канала" in alert
    assert panel.users == {}


async def test_trial_when_panel_is_down(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    panel: FakePanel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await registered(dp, bot)
    panel.fail = True
    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    answer = fake.calls[-1]
    assert (
        isinstance(answer, AnswerCallbackQuery)
        and answer.text
        and "попробуйте" in answer.text.lower()
    )

    async with session_factory() as session:
        user = await session.get(DbUser, TG_USER.id)
        assert user is not None and user.trial_used_at is None


async def test_connect_instructions(dp: Dispatcher, bot: Bot, fake: FakeSession) -> None:
    await registered(dp, bot)
    await dp.feed_update(bot, menu(MenuAction.CONNECT))
    assert "Выберите устройство" in last_text(fake)
    await dp.feed_update(bot, callback(PlatformCallback(platform=Platform.ANDROID).pack()))
    assert "Android" in last_text(fake) and "Happ" in last_text(fake)


async def test_expired_subscription_screen(
    dp: Dispatcher, bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await registered(dp, bot)
    async with session_factory() as session:
        session.add(
            Subscription(
                user_id=TG_USER.id,
                panel_user_id=1,
                panel_username="tg_100",
                subscription_url="https://sub.example/tg_100",
                expires_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        await session.commit()
    await dp.feed_update(bot, menu(MenuAction.SUBSCRIPTION))
    assert "Подписка закончилась" in last_text(fake) and "01.01.2020" in last_text(fake)


def sent_texts(fake: FakeSession) -> list[str]:
    return [c.text for c in fake.calls if isinstance(c, SendMessage | EditMessageText)]


async def add_plan(session_factory: async_sessionmaker[AsyncSession], price: int = 300) -> int:
    async with session_factory() as session:
        plan = Plan(months=1, days=30, price_rub=price)
        session.add(plan)
        await session.commit()
        return plan.id


async def test_buy_with_stars(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    panel: FakePanel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    plan_id = await add_plan(session_factory)
    await registered(dp, bot)

    await dp.feed_update(bot, menu(MenuAction.BUY))
    assert "Выберите тариф" in last_text(fake)
    await dp.feed_update(bot, callback(PlanCallback(plan_id=plan_id).pack()))
    assert "300 ₽ (200 ⭐)" in last_text(fake)

    await dp.feed_update(bot, callback(PayCallback(plan_id=plan_id).pack()))
    invoice = next(c for c in fake.calls if isinstance(c, SendInvoice))
    assert invoice.currency == "XTR" and invoice.prices[0].amount == 200

    await dp.feed_update(
        bot,
        Update(
            update_id=next(ids),
            pre_checkout_query=PreCheckoutQuery(
                id="q1",
                from_user=TG_USER,
                currency="XTR",
                total_amount=200,
                invoice_payload=invoice.payload,
            ),
        ),
    )
    answer = fake.calls[-1]
    assert isinstance(answer, AnswerPreCheckoutQuery) and answer.ok

    paid = Update(
        update_id=next(ids),
        message=Message(
            message_id=next(ids),
            date=datetime.now(UTC),
            chat=CHAT,
            from_user=TG_USER,
            successful_payment=SuccessfulPayment(
                currency="XTR",
                total_amount=200,
                invoice_payload=invoice.payload,
                telegram_payment_charge_id="tg-charge-1",
                provider_payment_charge_id="",
            ),
        ),
    )
    await dp.feed_update(bot, paid)
    assert "Оплата прошла" in last_text(fake)
    assert len(panel.users) == 1

    # Повторная доставка того же платежа не продлевает подписку второй раз.
    before = len(fake.calls)
    await dp.feed_update(bot, paid)
    assert len(fake.calls) == before

    async with session_factory() as session:
        payment = await session.get(Payment, 1)
        assert payment is not None and payment.status == PaymentStatus.PAID
        assert payment.fulfilled_at is not None


async def test_pre_checkout_rejects_unknown_invoice(
    dp: Dispatcher, bot: Bot, fake: FakeSession
) -> None:
    await registered(dp, bot)
    await dp.feed_update(
        bot,
        Update(
            update_id=next(ids),
            pre_checkout_query=PreCheckoutQuery(
                id="q1",
                from_user=TG_USER,
                currency="XTR",
                total_amount=1,
                invoice_payload="pay:999",
            ),
        ),
    )
    answer = fake.calls[-1]
    assert isinstance(answer, AnswerPreCheckoutQuery) and not answer.ok


async def test_promo_code_and_balance_purchase(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    panel: FakePanel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    plan_id = await add_plan(session_factory, price=100)
    async with session_factory() as session:
        session.add(PromoCode(code="GIFT", kind=PromoKind.BALANCE, value=10000))
        await session.commit()
    await registered(dp, bot)

    await dp.feed_update(bot, menu(MenuAction.PROMO))
    await dp.feed_update(bot, message("nope"))
    assert "Такого промокода нет" in last_text(fake)
    await dp.feed_update(bot, message("gift"))
    assert "начислено 100 ₽" in last_text(fake)

    await dp.feed_update(bot, callback(PlanCallback(plan_id=plan_id).pack()))
    assert "Полностью оплачивается с баланса" in last_text(fake)
    await dp.feed_update(bot, callback(PayCallback(plan_id=plan_id).pack()))
    assert "Оплата прошла" in last_text(fake)
    assert not any(isinstance(c, SendInvoice) for c in fake.calls)
    assert len(panel.users) == 1


async def test_start_command_leaves_promo_input(
    dp: Dispatcher, bot: Bot, fake: FakeSession
) -> None:
    await registered(dp, bot)
    await dp.feed_update(bot, menu(MenuAction.PROMO))
    await dp.feed_update(bot, message("/start"))
    assert "Привет" in last_text(fake)
    await dp.feed_update(bot, message("hello"))
    assert "Такого промокода нет" not in last_text(fake)


async def test_referral_screen_and_reward_message(
    dp: Dispatcher,
    bot: Bot,
    fake: FakeSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add(DbUser(id=7, first_name="Ref", language="en"))
        await session.commit()
    plan_id = await add_plan(session_factory)

    await dp.feed_update(bot, message("/start ref_7"))
    await dp.feed_update(bot, callback(LanguageCallback(code="ru").pack()))
    await dp.feed_update(bot, menu(MenuAction.REFERRALS))
    assert "https://t.me/octo_bot?start=ref_100" in last_text(fake)

    await dp.feed_update(bot, callback(PayCallback(plan_id=plan_id).pack()))
    invoice = next(c for c in fake.calls if isinstance(c, SendInvoice))
    await dp.feed_update(
        bot,
        Update(
            update_id=next(ids),
            message=Message(
                message_id=next(ids),
                date=datetime.now(UTC),
                chat=CHAT,
                from_user=TG_USER,
                successful_payment=SuccessfulPayment(
                    currency="XTR",
                    total_amount=invoice.prices[0].amount,
                    invoice_payload=invoice.payload,
                    telegram_payment_charge_id="tg-charge-2",
                    provider_payment_charge_id="",
                ),
            ),
        ),
    )
    reward = next(c for c in fake.calls if isinstance(c, SendMessage) and c.chat_id == 7)
    assert "60 ₽ added to your balance" in reward.text


async def test_demo_mode_gives_vless_link(
    bot: Bot, fake: FakeSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    link = "vless://3f1c2d4e-5a6b-4c7d-8e9f-0a1b2c3d4e5f@203.0.113.7:443?security=reality"
    settings = Settings(bot_token="42:TEST", trial_channel=None, vpn_panel="demo")
    panel = DemoPanel(link)
    dp = build_dispatcher(settings, session_factory, TranslatorHub("ru"), panel)
    await registered(dp, bot)
    await dp.feed_update(bot, menu(MenuAction.TRIAL))
    assert "Пробный период активирован" in last_text(fake) and "203.0.113.7" in last_text(fake)

    await dp.feed_update(bot, menu(MenuAction.SUBSCRIPTION))
    sent = [c for c in fake.calls if isinstance(c, SendMessage | EditMessageText)][-1]
    assert isinstance(sent.reply_markup, InlineKeyboardMarkup)
    buttons = [b for row in sent.reply_markup.inline_keyboard for b in row]
    assert buttons and all(b.url is None for b in buttons)
