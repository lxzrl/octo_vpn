"""Main bot application - VPN Telegram Bot"""

import os
import sys
import logging
from datetime import datetime

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)

from bot.config.settings import Config
from bot.models.database import DatabaseManager

from bot.handlers.main import (
    start_command,
    show_plans,
    select_payment_method,
    process_payment,
    verify_payment,
    show_profile,
    show_my_config,
    show_referral_info,
    show_help,
    show_support,
    main_menu,
    cancel_conversation,
    SELECTING_PLAN,
    SELECTING_PAYMENT_METHOD,
    WAITING_PAYMENT
)

from bot.handlers.admin import (
    admin_panel,
    handle_broadcast_message,
    admin_back_to_panel,
    admin_broadcast_confirm
)

from bot.utils.helpers import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def invalid_input_fallback(update, context) -> None:
    if update.message:
        await update.message.reply_text(
            "⚠️ Используйте кнопки меню.\nДля выхода: /cancel"
        )


def create_application() -> Application:
    Config.validate()

    application = Application.builder().token(Config.BOT_TOKEN).build()

    # ✅ DB init (1 раз, без дублей)
    application.bot_data["db_manager"] = DatabaseManager(Config.DATABASE_URL)

    conversation_text_fallback = MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        invalid_input_fallback
    )

    purchase_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_plans, pattern='^buy_vpn$')],
        states={
            SELECTING_PLAN: [
                CallbackQueryHandler(select_payment_method, pattern='^plan_'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
                conversation_text_fallback
            ],
            SELECTING_PAYMENT_METHOD: [
                CallbackQueryHandler(process_payment, pattern='^pay_'),
                CallbackQueryHandler(show_plans, pattern='^buy_vpn$'),
                conversation_text_fallback
            ],
            WAITING_PAYMENT: [
                CallbackQueryHandler(verify_payment, pattern='^verify_payment_'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
                conversation_text_fallback
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_conversation),
            CallbackQueryHandler(main_menu, pattern='^main_menu$')
        ]
    )

    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(purchase_conversation)

    application.add_handler(CallbackQueryHandler(show_profile, pattern='^profile$'))
    application.add_handler(CallbackQueryHandler(show_my_config, pattern='^my_config$'))
    application.add_handler(CallbackQueryHandler(show_referral_info, pattern='^referral$'))
    application.add_handler(CallbackQueryHandler(show_help, pattern='^help$'))
    application.add_handler(CallbackQueryHandler(show_support, pattern='^support$'))
    application.add_handler(CallbackQueryHandler(main_menu, pattern='^main_menu$'))

    application.add_handler(CallbackQueryHandler(admin_back_to_panel, pattern='^admin_back$'))
    application.add_handler(CallbackQueryHandler(admin_broadcast_confirm, pattern='^admin_broadcast_confirm$'))

    admin_filter = filters.User(user_id=Config.ADMIN_IDS)

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter,
        handle_broadcast_message)
    )

    return application


async def error_handler(update: object, context) -> None:
    logger.error(f"Error: {context.error}", exc_info=context.error)


# =========================
# FIXED POST INIT
# =========================
async def post_init(application: Application) -> None:
    logger.info("🚀 Bot init...")

    db_manager = application.bot_data.get("db_manager")

    if not db_manager:
        db_manager = DatabaseManager(Config.DATABASE_URL)
        application.bot_data["db_manager"] = db_manager

    await db_manager.create_tables()

    logger.info("✅ Database initialized")

    bot_info = await application.bot.get_me()

    logger.info(f"Bot started @{bot_info.username}")

    for admin_id in Config.ADMIN_IDS:
        try:
            await application.bot.send_message(
                chat_id=admin_id,
                text=f"🤖 Bot started @{bot_info.username}"
            )
        except Exception:
            pass


async def post_shutdown(application: Application) -> None:
    logger.info("🛑 Shutdown")


def main():
    logger.info("Starting bot...")

    try:
        application = create_application()

        application.post_init = post_init
        application.post_shutdown = post_shutdown

        application.add_error_handler(error_handler)

        application.run_polling(
            drop_pending_updates=True
        )

    except Exception as e:
        logger.error(f"Failed: {e}")


if __name__ == "__main__":
    main()