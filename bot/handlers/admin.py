"""Admin handlers for VPN Telegram Bot (Fully Async)"""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, TelegramError
from telegram.ext import ContextTypes
from sqlalchemy import select, func, desc, update

from bot.models.database import DatabaseManager, User, Subscription, Payment, VPNKey
from bot.config.settings import Config
from bot.utils.helpers import (
    is_admin,
    log_admin_action,
    format_datetime,
    format_date,
    format_time_ago,
    StatsCalculator
)
from locales.ru import get_message

logger = logging.getLogger(__name__)

# Инициализируем асинхронный менеджер базы данных
db_manager = DatabaseManager(Config.DATABASE_URL)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin panel"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text(get_message('admin_not_authorized'))
        return

    async with db_manager.get_session() as session:
        # Асинхронно собираем всю статистику
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

        active_users_stmt = select(func.count(User.id)).where(
            User.last_activity >= datetime.now(timezone.utc) - timedelta(days=7)
        )
        active_users = (await session.execute(active_users_stmt)).scalar() or 0

        active_subs_stmt = select(func.count(Subscription.id)).where(
            Subscription.is_active == True,
            Subscription.end_date > datetime.now(timezone.utc)
        )
        active_subscriptions = (await session.execute(active_subs_stmt)).scalar() or 0

        # Выручка за сегодня
        today = datetime.now(timezone.utc).date()
        daily_rev_stmt = select(func.sum(Payment.amount)).where(
            Payment.status == 'completed',
            func.cast(Payment.completed_at, func.Date) == today
        )
        daily_revenue = (await session.execute(daily_rev_stmt)).scalar() or 0
        daily_revenue = daily_revenue / 100  # из копеек в рубли

        # Выручка за месяц
        start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_rev_stmt = select(func.sum(Payment.amount)).where(
            Payment.status == 'completed',
            Payment.completed_at >= start_of_month
        )
        monthly_revenue = (await session.execute(monthly_rev_stmt)).scalar() or 0
        monthly_revenue = monthly_revenue / 100

        # Доступные ключи
        available_keys_stmt = select(func.count(VPNKey.id)).where(VPNKey.is_used == False)
        available_keys = (await session.execute(available_keys_stmt)).scalar() or 0

        # Новые пользователи за сегодня
        new_users_stmt = select(func.count(User.id)).where(
            func.cast(User.created_at, func.Date) == today
        )
        new_users = (await session.execute(new_users_stmt)).scalar() or 0

        admin_text = get_message('admin_panel',
            total_users=total_users,
            active_subscriptions=active_subscriptions,
            daily_revenue=int(daily_revenue),
            monthly_revenue=int(monthly_revenue),
            available_keys=available_keys,
            new_users=new_users,
            last_update=format_datetime(datetime.now(timezone.utc))
        )

        keyboard = [
            [
                InlineKeyboardButton("👥 Пользователи", callback_data='admin_users'),
                InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')
            ],
            [
                InlineKeyboardButton("🔑 VPN ключи", callback_data='admin_keys'),
                InlineKeyboardButton("💰 Платежи", callback_data='admin_payments')
            ],
            [
                InlineKeyboardButton("📢 Рассылка", callback_data='admin_broadcast'),
                InlineKeyboardButton("📋 Логи", callback_data='admin_logs')
            ],
            [
                InlineKeyboardButton("⚙️ Настройки", callback_data='admin_settings'),
                InlineKeyboardButton("🔄 Обновить", callback_data='admin_refresh')
            ]
        ]

        await update.message.reply_text(
            text=admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

        # Запускаем запись лога асинхронно в треде, если функция синхронная
        await asyncio.to_thread(log_admin_action, user_id, "accessed_admin_panel")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin callback queries"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.edit_message_text(get_message('admin_not_authorized'))
        return

    action = query.data.replace('admin_', '')

    if action == 'refresh':
        await admin_panel_refresh(update, context)
    elif action == 'users':
        await admin_users_list(update, context)
    elif action == 'stats':
        await admin_detailed_stats(update, context)
    elif action == 'keys':
        await admin_keys_management(update, context)
    elif action == 'payments':
        await admin_payments_list(update, context)
    elif action == 'broadcast':
        await admin_broadcast_start(update, context)
    elif action == 'logs':
        await admin_logs_view(update, context)
    elif action == 'settings':
        await admin_settings(update, context)

async def admin_panel_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh admin panel"""
    query = update.callback_query
    user_id = update.effective_user.id

    async with db_manager.get_session() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

        active_subs_stmt = select(func.count(Subscription.id)).where(
            Subscription.is_active == True,
            Subscription.end_date > datetime.now(timezone.utc)
        )
        active_subscriptions = (await session.execute(active_subs_stmt)).scalar() or 0

        today = datetime.now(timezone.utc).date()
        daily_rev_stmt = select(func.sum(Payment.amount)).where(
            Payment.status == 'completed',
            func.cast(Payment.completed_at, func.Date) == today
        )
        daily_revenue = (await session.execute(daily_rev_stmt)).scalar() or 0
        daily_revenue = daily_revenue / 100

        start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_rev_stmt = select(func.sum(Payment.amount)).where(
            Payment.status == 'completed',
            Payment.completed_at >= start_of_month
        )
        monthly_revenue = (await session.execute(monthly_rev_stmt)).scalar() or 0
        monthly_revenue = monthly_revenue / 100

        available_keys_stmt = select(func.count(VPNKey.id)).where(VPNKey.is_used == False)
        available_keys = (await session.execute(available_keys_stmt)).scalar() or 0

        new_users_stmt = select(func.count(User.id)).where(
            func.cast(User.created_at, func.Date) == today
        )
        new_users = (await session.execute(new_users_stmt)).scalar() or 0

        admin_text = get_message('admin_panel',
            total_users=total_users,
            active_subscriptions=active_subscriptions,
            daily_revenue=int(daily_revenue),
            monthly_revenue=int(monthly_revenue),
            available_keys=available_keys,
            new_users=new_users,
            last_update=format_datetime(datetime.now(timezone.utc))
        )

        keyboard = [
            [
                InlineKeyboardButton("👥 Пользователи", callback_data='admin_users'),
                InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')
            ],
            [
                InlineKeyboardButton("🔑 VPN ключи", callback_data='admin_keys'),
                InlineKeyboardButton("💰 Платежи", callback_data='admin_payments')
            ],
            [
                InlineKeyboardButton("📢 Рассылка", callback_data='admin_broadcast'),
                InlineKeyboardButton("📋 Логи", callback_data='admin_logs')
            ],
            [
                InlineKeyboardButton("⚙️ Настройки", callback_data='admin_settings'),
                InlineKeyboardButton("🔄 Обновлено ✅", callback_data='admin_refresh')
            ]
        ]

        await query.edit_message_text(
            text=admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

        await asyncio.to_thread(log_admin_action, user_id, "refreshed_admin_panel")

async def admin_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show users list for admin"""
    query = update.callback_query

    async with db_manager.get_session() as session:
        page = context.user_data.get('admin_users_page', 0)
        limit = 10
        offset = page * limit

        # Асинхронно достаем список юзеров
        users_stmt = select(User).order_by(desc(User.created_at)).offset(offset).limit(limit)
        users_result = await session.execute(users_stmt)
        users = users_result.scalars().all()

        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

        users_text = f"👥 Пользователи (стр. {page + 1}):\n\n"

        for user in users:
            # Так как мы в асинхронном контексте сессии, можем читать user.has_active_subscription
            status_emoji = "✅" if user.has_active_subscription else "❌"
            last_activity = format_time_ago(user.last_activity)

            users_text += f"{status_emoji} <b>{user.full_name}</b>\n"
            users_text += f"   🆔 ID: <code>{user.telegram_id}</code>\n"
            users_text += f"   👤 @{user.username or 'None'}\n"
            users_text += f"   📅 Регистрация: {format_date(user.created_at)}\n"
            users_text += f"   🕐 Активность: {last_activity}\n"
            users_text += f"   💰 Потрачено: {user.total_spent} ₽\n"
            users_text += f"   🎁 Рефералов: {user.total_referrals}\n\n"

        users_text += f"📊 Всего пользователей: {total_users}"

        keyboard = []
        nav_row = []

        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'admin_users_page_{page-1}'))
        if (page + 1) * limit < total_users:
            nav_row.append(InlineKeyboardButton("Вперед ➡️", callback_data=f'admin_users_page_{page+1}'))

        if nav_row:
            keyboard.append(nav_row)

        keyboard.extend([
            [
                InlineKeyboardButton("🔍 Поиск пользователя", callback_data='admin_user_search'),
                InlineKeyboardButton("📊 Статистика", callback_data='admin_user_stats')
            ],
            [InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_back')]
        ])

        await query.edit_message_text(
            text=users_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

async def admin_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed statistics"""
    query = update.callback_query
    user_id = update.effective_user.id

    async with db_manager.get_session() as session:
        # Если StatsCalculator синхронный, запускаем в потоке
        stats = await asyncio.to_thread(StatsCalculator.calculate_daily_stats)

        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

        active_week_stmt = select(func.count(User.id)).where(User.last_activity >= datetime.now(timezone.utc) - timedelta(days=7))
        active_users_week = (await session.execute(active_week_stmt)).scalar() or 0

        active_month_stmt = select(func.count(User.id)).where(User.last_activity >= datetime.now(timezone.utc) - timedelta(days=30))
        active_users_month = (await session.execute(active_month_stmt)).scalar() or 0

        # Группировка подписок по планам
        subs_stmt = select(Subscription.plan_type, func.count(Subscription.id)).where(
            Subscription.is_active == True,
            Subscription.end_date > datetime.now(timezone.utc)
        ).group_by(Subscription.plan_type)
        subs_by_plan = (await session.execute(subs_stmt)).all()

        # Общий доход
        total_rev_stmt = select(func.sum(Payment.amount)).where(Payment.status == 'completed')
        total_revenue = (await session.execute(total_rev_stmt)).scalar() or 0
        total_revenue = total_revenue / 100

        # Недельный доход
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        weekly_rev_stmt = select(func.sum(Payment.amount)).where(
            Payment.status == 'completed',
            Payment.completed_at >= week_ago
        )
        weekly_revenue = (await session.execute(weekly_rev_stmt)).scalar() or 0
        weekly_revenue = weekly_revenue / 100

        stats_text = f"📊 <b>Подробная статистика</b>\n\n"
        stats_text += f"👥 <b>Пользователи:</b>\n"
        stats_text += f"   • Всего: {total_users}\n"
        stats_text += f"   • Новых сегодня: {stats.get('new_users', 0)}\n"
        stats_text += f"   • Активных за неделю: {active_users_week}\n"
        stats_text += f"   • Активных за месяц: {active_users_month}\n\n"

        stats_text += f"📱 <b>Подписки:</b>\n"
        stats_text += f"   • Активных: {stats.get('active_subscriptions', 0)}\n"
        for plan_type, count in subs_by_plan:
            plan_name = plan_type.replace('_', ' ').title()
            stats_text += f"   • {plan_name}: {count}\n"
        stats_text += "\n"

        stats_text += f"💰 <b>Доходы:</b>\n"
        stats_text += f"   • Сегодня: {stats.get('daily_revenue', 0.0):.0f} ₽\n"
        stats_text += f"   • За неделю: {weekly_revenue:.0f} ₽\n"
        stats_text += f"   • Всего: {total_revenue:.0f} ₽\n"
        stats_text += f"   • Платежей сегодня: {stats.get('successful_payments', 0)}\n\n"

        stats_text += f"🔄 <b>Обновлено:</b> {format_datetime(datetime.now(timezone.utc))}"

        keyboard = [
            [
                InlineKeyboardButton("📈 График доходов", callback_data='admin_revenue_chart'),
                InlineKeyboardButton("👥 Активность пользователей", callback_data='admin_activity_chart')
            ],
            [
                InlineKeyboardButton("📊 Экспорт данных", callback_data='admin_export_data'),
                InlineKeyboardButton("🔄 Обновить", callback_data='admin_stats')
            ],
            [InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_back')]
        ]

        await query.edit_message_text(text=stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        await asyncio.to_thread(log_admin_action, user_id, "viewed_detailed_stats")

async def admin_keys_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage VPN keys"""
    query = update.callback_query

    async with db_manager.get_session() as session:
        total_keys = (await session.execute(select(func.count(VPNKey.id)))).scalar() or 0
        available_keys = (await session.execute(select(func.count(VPNKey.id)).where(VPNKey.is_used == False))).scalar() or 0
        used_keys = total_keys - available_keys

        keys_text = f"🔑 <b>Управление VPN ключами</b>\n\n"
        keys_text += f"📊 <b>Статистика:</b>\n"
        keys_text += f"   • Всего ключей: {total_keys}\n"
        keys_text += f"   • Доступных: {available_keys}\n"
        keys_text += f"   • Использованных: {used_keys}\n\n"

        if available_keys < 10:
            keys_text += "⚠️ <b>Внимание!</b> Мало доступных ключей!\n\n"

        keys_text += f"🔄 <b>Обновлено:</b> {format_datetime(datetime.now(timezone.utc))}"

        keyboard = [
            [
                InlineKeyboardButton("➕ Добавить ключи", callback_data='admin_keys_add'),
                InlineKeyboardButton("📋 Список ключей", callback_data='admin_keys_list')
            ],
            [
                InlineKeyboardButton("🗑️ Очистить использованные", callback_data='admin_keys_cleanup'),
                InlineKeyboardButton("📊 Статистика по серверам", callback_data='admin_keys_stats')
            ],
            [InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_back')]
        ]

        await query.edit_message_text(text=keys_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def admin_payments_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent payments"""
    query = update.callback_query

    async with db_manager.get_session() as session:
        # Получаем последние 20 платежей
        stmt = select(Payment).order_by(desc(Payment.created_at)).limit(20)
        result = await session.execute(stmt)
        payments = result.scalars().all()

        payments_text = f"💰 <b>Последние платежи</b>\n\n"

        for payment in payments:
            # Догружаем пользователя
            user_stmt = select(User).filter_by(id=payment.user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalars().first()

            status_emoji = {
                'completed': '✅',
                'pending': '⏳',
                'failed': '❌',
                'cancelled': '🚫'
            }.get(payment.status, '❓')

            payments_text += f"{status_emoji} <b>{payment.amount_rubles:.0f} ₽</b>\n"
            payments_text += f"   👤 {user.full_name if user else 'Unknown'}\n"
            payments_text += f"   📦 {payment.plan_type.replace('_', ' ').title()}\n"
            payments_text += f"   💳 {payment.payment_method.upper() if payment.payment_method else 'N/A'}\n"
            payments_text += f"   📅 {format_datetime(payment.created_at)}\n\n"

        keyboard = [
            [
                InlineKeyboardButton("💰 Статистика доходов", callback_data='admin_revenue_stats'),
                InlineKeyboardButton("🔍 Поиск платежа", callback_data='admin_payment_search')
            ],
            [
                InlineKeyboardButton("📊 По методам оплаты", callback_data='admin_payment_methods'),
                InlineKeyboardButton("🔄 Обновить", callback_data='admin_payments')
            ],
            [InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_back')]
        ]

        await query.edit_message_text(text=payments_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start broadcast message creation"""
    query = update.callback_query

    async with db_manager.get_session() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        active_users_stmt = select(func.count(User.id)).where(
            User.last_activity >= datetime.now(timezone.utc) - timedelta(days=30),
            User.is_active == True  # Рассылаем только тем, у кого бот активен
        )
        active_users = (await session.execute(active_users_stmt)).scalar() or 0

        broadcast_text = get_message('broadcast_start',
            total_users=total_users,
            active_users=active_users
        )

        keyboard = [[InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_back')]]
        await query.edit_message_text(text=broadcast_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

        context.user_data['waiting_broadcast'] = True

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast message from admin"""
    user_id = update.effective_user.id

    if not is_admin(user_id) or not context.user_data.get('waiting_broadcast'):
        return

    broadcast_message = update.message.text
    context.user_data['waiting_broadcast'] = False
    context.user_data['broadcast_message'] = broadcast_message

    async with db_manager.get_session() as session:
        # Рассылаем только тем, кто не заблокировал бота
        total_users = (await session.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0

        confirm_text = get_message('broadcast_confirm', recipients=total_users, message=broadcast_message)
        keyboard = [[
            InlineKeyboardButton("✅ Отправить всем", callback_data='admin_broadcast_confirm'),
            InlineKeyboardButton("❌ Отмена", callback_data='admin_back')
        ]]

        await update.message.reply_text(text=confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def admin_broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and execute broadcast (With User Cleanup on Blocked)"""
    query = update.callback_query
    await query.answer("📢 Начинаем рассылку...")

    user_id = update.effective_user.id
    broadcast_message = context.user_data.get('broadcast_message')

    if not broadcast_message:
        await query.edit_message_text("❌ Сообщение для рассылки не найдено")
        return

    async with db_manager.get_session() as session:
        # Рассылаем только АКТИВНЫМ пользователям
        stmt = select(User).where(User.is_active == True)
        users_result = await session.execute(stmt)
        users = users_result.scalars().all()
        total_users = len(users)

        sent_count = 0
        failed_count = 0
        blocked_count = 0  # Количество тех, кто заблокировал бота

        await query.edit_message_text(
            f"📢 Рассылка запущена...\n\n"
            f"👥 Всего получателей: {total_users}\n"
            f"✅ Отправлено: 0\n"
            f"❌ Ошибок: 0"
        )

        for i, user in enumerate(users):
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=broadcast_message,
                    parse_mode='HTML'
                )
                sent_count += 1

            except Forbidden:
                # ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАЛ БОТА
                # Помечаем его неактивным в БД, чтобы не нагружать бота в будущем
                blocked_count += 1
                user.is_active = False
                logger.info(f"User {user.telegram_id} blocked the bot. Marked as inactive.")

            except TelegramError as te:
                # Другие сетевые или ТГ ошибки
                failed_count += 1
                logger.warning(f"Telegram error sending broadcast to {user.telegram_id}: {te}")

            except Exception as e:
                failed_count += 1
                logger.warning(f"Unexpected error sending broadcast to {user.telegram_id}: {e}")

            # Обновляем прогресс каждые 30 сообщений (безопасный интервал для избежания Flood Limit)
            if (i + 1) % 30 == 0 or (i + 1) == total_users:
                # Фиксируем пометки неактивных в БД, чтобы транзакции не висели
                await session.commit()

                try:
                    await query.edit_message_text(
                        f"📢 Рассылка в процессе...\n\n"
                        f"👥 Всего получателей: {total_users}\n"
                        f"✅ Отправлено: {sent_count}\n"
                        f"❌ Ошибок: {failed_count}\n"
                        f"🚫 Заблокировали бота: {blocked_count}\n"
                        f"📊 Прогресс: {((i + 1) / total_users * 100):.1f}%"
                    )
                except Exception:
                    pass  # Игнорируем ошибки частого редактирования сообщения прогресса

            # Контроль лимитов Telegram: 30 сообщений в секунду max.
            # 0.05 сек задержки дает комфортные 20 сообщений в сек.
            await asyncio.sleep(0.05)

        # Окончательно коммитим изменения
        await session.commit()

        success_text = get_message('broadcast_success', sent=sent_count, total=total_users)
        if failed_count > 0:
            success_text += f"\n⚠️ Сетевых ошибок: {failed_count}"
        if blocked_count > 0:
            success_text += f"\n🗑️ Очищено мертвых пользователей (заблокировали бота): {blocked_count}"

        keyboard = [[InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_back')]]
        await query.edit_message_text(text=success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

        await asyncio.to_thread(log_admin_action, user_id, "broadcast_sent", f"Sent to {sent_count}/{total_users}. Blocked: {blocked_count}")

async def admin_logs_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View admin logs"""
    query = update.callback_query

    try:
        log_file = f"logs/vpn_bot_{datetime.now().strftime('%Y%m%d')}.log"
        # Чтение файла — синхронная операция, оборачиваем в тред во избежание блокировок
        def read_logs():
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.readlines()[-20:]

        recent_logs = await asyncio.to_thread(read_logs)

        logs_text = f"📋 <b>Последние логи</b>\n\n<pre>"
        for line in recent_logs:
            if len(line) > 100:
                line = line[:97] + "..."
            logs_text += line
        logs_text += "</pre>"

    except FileNotFoundError:
        logs_text = "📋 <b>Логи</b>\n\n❌ Файл логов не найден"
    except Exception as e:
        logs_text = f"📋 <b>Логи</b>\n\n❌ Ошибка чтения логов: {str(e)}"

    keyboard = [
        [
            InlineKeyboardButton("📁 Скачать полный лог", callback_data='admin_download_logs'),
            InlineKeyboardButton("🔄 Обновить", callback_data='admin_logs')
        ],
        [InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_back')]
    ]
    await query.edit_message_text(text=logs_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin settings"""
    query = update.callback_query

    settings_text = f"⚙️ <b>Настройки бота</b>\n\n"
    settings_text += f"🤖 <b>Основные:</b>\n"
    settings_text += f"   • Режим отладки: {'✅' if Config.DEBUG else '❌'}\n"
    settings_text += f"   • Уровень логов: {Config.LOG_LEVEL}\n"
    settings_text += f"   • Язык по умолчанию: {Config.DEFAULT_LANGUAGE}\n\n"

    settings_text += f"💰 <b>Тарифы:</b>\n"
    settings_text += f"   • 1 месяц: {Config.PLAN_1_MONTH_PRICE} ₽\n"
    settings_text += f"   • 3 месяца: {Config.PLAN_3_MONTH_PRICE} ₽\n"
    settings_text += f"   • 6 месяцев: {Config.PLAN_6_MONTH_PRICE} ₽\n"
    settings_text += f"   • 12 месяцев: {Config.PLAN_12_MONTH_PRICE} ₽\n\n"

    settings_text += f"🎁 <b>Реферальная программа:</b>\n"
    settings_text += f"   • Процент бонуса: {Config.REFERRAL_BONUS_PERCENT}%\n"
    settings_text += f"   • Минимум для вывода: {Config.REFERRAL_MIN_PAYOUT} ₽\n"

    keyboard = [
        [
            InlineKeyboardButton("💰 Изменить тарифы", callback_data='admin_edit_prices'),
            InlineKeyboardButton("🎁 Настроить рефералы", callback_data='admin_edit_referrals')
        ],
        [
            InlineKeyboardButton("🔧 Системные настройки", callback_data='admin_system_settings'),
            InlineKeyboardButton("💾 Резервное копирование", callback_data='admin_backup')
        ],
        [InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_back')]
    ]
    await query.edit_message_text(text=settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def admin_back_to_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to admin panel"""
    query = update.callback_query
    await query.answer()

    # Сбрасываем состояния рассылки
    context.user_data.pop('waiting_broadcast', None)
    context.user_data.pop('broadcast_message', None)

    await admin_panel_refresh(update, context)
