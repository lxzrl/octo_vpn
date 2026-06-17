"""Russian localization for VPN Bot"""

MESSAGES = {
    # Welcome and basic messages
    'welcome': (
        "🐙 Здравствуй! {name}\n\n"
        "Я твой личный бот и помощник\n\n"
        "Ты можешь использовать наш сервис без необходимости регистрации — "
        "весь процесс происходит внутри Telegram.\n\n"
        '📢 <a href="https://t.me/OctoVPNcom">Наш новостной канал</a>\n'
        '💬 <a href="https://t.me/octovpnchat">Ознакомиться с отзывами</a>\n\n'
        "Выберите действие:"
    ),
    
    'welcome_back': (
        "🐙 С возвращением, {name}!\n\n"
        "🔥 Что нового:\n"
        "• Добавлены новые серверы в Европе\n"
        "• Улучшена стабильность соединения\n"
        "• Улучшена скорость соединения\n\n"
        "Выберите действие:"
    ),
    
    'help': (
        "📖 Помощь:\n\n"
        "🛒 Оплатить подписку:\n"
        "• Выберите тарифный план\n"
        "• Оплатите удобным способом\n"
        "• Получите конфигурацию автоматически\n\n"
        "📱 Настройка:\n"
        "• Скачайте приложение v2RayTun\n"
        "• Отсканируйте QR-код или импортируйте файл\n"
        "• Наслаждайтесь безопасным интернетом!\n\n"
        "🎁 Реферальная система:\n"
        "• Приглашайте друзей по своей ссылке\n"
        "• Получайте 10% с каждой их покупки\n"
        "• Выводите заработанные деньги\n\n"
        "💬 Поддержка работает круглосуточно!"
    ),
    
    # Subscription plans
    'plans_header': "🐙 OctoVPN предлагает вам лучшие сервера с неограниченным траффиком.\n"
    "• Подходит для обхода всех блокировок\n"
    "• До 10 устройств одновременно\n"
    "• Без ограничений по скорости и трафику\n\n",
    'plan_template': (
        "{emoji} {name} {popular_badge}\n"
        "💰 {price} ₽ ({price_per_month} ₽/мес)\n"
        "⏰ {duration} дней\n"
        "📝 {description}\n"
        "💎 {savings}\n\n"
    ),
    'popular_badge': "Популярный",
    'best_deal_badge': "Лучшее предложение",
    'choose_plan': "👆 Нажмите на кнопку для выбора плана:",
    
    # Payment
    'payment_methods': (
        "💳 Способы оплаты для плана \"{plan_name}\":\n\n"
        "💰 Сумма к оплате: {amount} ₽\n"
        "⏰ Срок действия: {duration} дней\n\n"
        "Выберите удобный способ оплаты:"
    ),
    'payment_created': (
        "✅ Счет успешно создан!\n\n"
        "📦 План: {plan_name}\n"
        "💰 Сумма: {amount} ₽\n"
        "🔗 Ссылка: {payment_url}\n\n"
        "⏰ Счет действителен 15 минут\n"
        "🎯 После оплаты VPN активируется мгновенно!\n\n"
        "💡 Совет: сохраните эту ссылку, чтобы не потерять"
    ),
    'payment_success': (
        "🎉 Поздравляем! Оплата прошла успешно!\n\n"
        "✅ VPN подписка активирована\n"
        "📦 План: {plan_name}\n"
        "📅 Действует до: {end_date}\n"
        "🌍 Сервер: {server_location}\n\n"
        "📱 Ваша конфигурация готова к использованию!"
    ),
    'payment_failed': (
        "❌ Ошибка при обработке платежа\n\n"
        "Возможные причины:\n"
        "• Недостаточно средств на счете\n"
        "• Истек срок действия карты\n"
        "• Технические проблемы\n\n"
        "💬 Обратитесь в поддержку или попробуйте другой способ оплаты"
    ),
    'payment_pending': (
        "⏳ Ожидаем поступления платежа...\n\n"
        "💰 Сумма: {amount} ₽\n"
        "🔗 Ссылка: {payment_url}\n\n"
        "⏰ Осталось времени: {time_left} мин\n\n"
        "🔄 Проверить статус платежа"
    ),
    
    # Profile
    'profile_info': (
        "👤 Личный кабинет\n\n"
        "🆔 ID: {user_id}\n"
        "👤 {full_name}\n"
        "📅 С нами с: {created_at}\n"
        "💰 Потрачено всего: {total_spent} ₽\n\n"
        "📱 Текущая подписка:\n"
        "{subscription_info}\n\n"
    ),
    'subscription_active': (
        "✅ АКТИВНА\n"
        "📦 План: {plan_name}\n"
        "📅 До: {end_date}\n"
        "⏰ Осталось: {time_remaining}\n"
        "🌍 Сервер: {server_location}"
    ),
    'subscription_inactive': "❌ Подписка не активна\n\n🛒 Купите VPN для защиты своего интернета!",
    'subscription_expired': (
        "⏰ Подписка истекла {days_ago} дней назад\n\n"
        "🔄 Продлите подписку со скидкой 10%!"
    ),
    
    # VPN Configuration
    'vpn_config_info': (
        "📱 Инструкция по подключению:\n\n"
        "1️⃣ Скачайте приложение v2RayTun:\n"
        "• Android: <a href='https://play.google.com/store/apps/details?id=com.v2raytun.android&hl=ru'>Google play</a>\n"
        "• iOS: <a href='https://apps.apple.com/us/app/v2raytun/id6476628951'>App Store</a>\n"
        "• Windows/Mac: wireguard.com\n\n"
        "2️⃣ Добавьте конфигурацию:\n"
        "• Нажмите '+' в приложении\n"
        "• Выберите 'Отсканировать QR'\n"
        "• Отсканируйте QR-код\n"
        "Или добавьте вручную\n"
        "• Нажмите '+' в приложении\n"
        "• Скопируйте ссылку сервера\n"
        "• Выбирите 'Добавить из буфера обмена'\n\n"
        "3️⃣ Подключитесь и наслаждайтесь!"
    ),
    
    # Referral system
    'referral_info': (
        "🎁 Реферальная система\n\n"
        "💰 Ваша статистика:\n"
        "👥 Приглашено друзей: {referral_count}\n"
        "💵 Заработано: {earned_amount} ₽\n"
        "💳 Доступно к выводу: {available_balance} ₽\n\n"
        "🔗 Ваша реферальная ссылка:\n"
        "`{referral_link}`\n\n"
        "💡 Условия программы:\n"
        "• 10% с каждой покупки друга\n"
        "• Оплата подписки с помощью баланса" 
        "📢 Поделитесь ссылкой в соцсетях!"
    ),
    'referral_bonus': (
        "🎉 Поздравляем!\n\n"
        "💰 Вы получили {amount} ₽ за приглашение друга!\n"
        "👤 Пользователь: {friend_name}\n\n"
        "💳 Баланс пополнен автоматически"
    ),
    
    # Support
    'support_info': (
        "💬 Техническая поддержка\n\n"
        "🕐 Работаем круглосуточно, без выходных\n"
        "⚡ Среднее время ответа: 5 минут\n\n"
        "📱 Способы связи:\n"
        "• Telegram: @{support_username}\n"
        "• Чат в боте (кнопка ниже)\n\n"
        "🆘 Частые проблемы:\n"
        "• Не подключается VPN\n"
        "• Медленная скорость\n"
        "• Проблемы с оплатой\n"
        "• Настройка на устройствах\n\n"
        "📝 Опишите проблему подробно для быстрого решения!"
    ),
    'support_chat': "💬 Написать в поддержку",
    'support_faq': "❓ Часто задаваемые вопросы",
    
    # Admin messages
    'admin_panel': (
        "🔧 Панель администратора\n\n"
        "📊 Статистика:\n"
        "👥 Всего пользователей: {total_users}\n"
        "✅ Активных подписок: {active_subscriptions}\n"
        "💰 Доходы сегодня: {daily_revenue} ₽\n"
        "💵 Доходы за месяц: {monthly_revenue} ₽\n"
        "🔑 Доступных ключей: {available_keys}\n"
        "🆕 Новых пользователей: {new_users}\n\n"
        "⏰ Последнее обновление: {last_update}"
    ),
    'admin_not_authorized': "❌ Доступ запрещен. У вас нет прав администратора.",
    'admin_users_list': "👥 Управление пользователями",
    'admin_keys_management': "🔑 Управление VPN ключами",
    'admin_broadcast': "📢 Массовая рассылка",
    'admin_stats': "📊 Подробная статистика",
    
    # Broadcast
    'broadcast_start': (
        "📢 Массовая рассылка\n\n"
        "👥 Всего пользователей: {total_users}\n"
        "✅ Активных: {active_users}\n\n"
        "📝 Отправьте сообщение для рассылки:"
    ),
    'broadcast_confirm': (
        "📢 Подтвердите рассылку\n\n"
        "👥 Получателей: {recipients}\n"
        "📝 Сообщение:\n\n{message}\n\n"
        "⚠️ Отправить всем пользователям?"
    ),
    'broadcast_success': "✅ Рассылка завершена! Отправлено {sent} сообщений из {total}.",
    
    # Errors and warnings
    'error_general': "❌ Что-то пошло не так. Попробуйте позже или обратитесь в поддержку.",
    'error_no_subscription': "❌ У вас нет активной подписки. Купите VPN для продолжения.",
    'error_payment_timeout': "⏰ Время оплаты истекло. Создайте новый счет для покупки.",
    'error_insufficient_keys': "❌ Временно нет доступных VPN ключей. Обратитесь в поддержку.",
    'error_invalid_plan': "❌ Неверный тарифный план. Выберите план из списка.",
    'error_payment_failed': "❌ Ошибка создания платежа. Попробуйте другой способ оплаты.",
    'warning_subscription_expires': (
        "⚠️ Внимание!\n\n"
        "Ваша подписка истекает через {days} дней.\n\n"
    ),
    
    # Success messages
    'success_config_sent': "✅ Конфигурация отправлена! Проверьте выше.",
    'success_subscription_extended': "✅ Подписка успешно продлена до {end_date}!",
    'success_referral_registered': "✅ Новый реферал зарегистрирован! Вы получите бонус после его первой покупки.",
    
    # Buttons
    'btn_buy_vpn': "🛒 Купить VPN",
    'btn_my_profile': "👤 Мой профиль",
    'btn_help': "❓ Помощь",
    'btn_support': "💬 Поддержка",
    'btn_referral': "🎁 Рефералы",
    'btn_config': "📱 Моя конфигурация",
    
    # Plan buttons with dynamic pricing
    'btn_plan_1_month': "🥉 1 месяц - {price} ₽",
    'btn_plan_3_months': "🥈 3 месяца - {price} ₽ 🔥",
    'btn_plan_6_months': "🥇 6 месяцев - {price} ₽ 💎",
    'btn_plan_12_months': "💰 1 год - {price} ₽ 👑",
    
    # Payment buttons
    'btn_yoomoney': "💳 ЮMoney (карты, кошельки)",
    'btn_crypto': "₿ Crypto (USDT)",
    'btn_check_payment': "🔄 Проверить платеж",
    'btn_new_payment': "💳 Создать новый счет",
    
    # Navigation buttons
    'btn_back': "⬅️ Назад",
    'btn_main_menu': "🏠 Главное меню",
    'btn_cancel': "❌ Отмена",
    'btn_confirm': "✅ Подтвердить",
    'btn_download': "📁 Скачать",
    'btn_share': "📤 Поделиться",
    
    # Admin buttons
    'btn_admin_users': "👥 Пользователи",
    'btn_admin_keys': "🔑 VPN ключи",
    'btn_admin_stats': "📊 Статистика",
    'btn_admin_broadcast': "📢 Рассылка",
    'btn_admin_settings': "⚙️ Настройки",
    'btn_admin_logs': "📋 Логи",
    
    # Time periods
    'today': "сегодня",
    'yesterday': "вчера",
    'this_week': "на этой неделе",
    'this_month': "в этом месяце",
    'days_ago': "{days} дней назад",
    'hours_ago': "{hours} часов назад",
    'minutes_ago': "{minutes} минут назад",
}


def get_message(key: str, **kwargs) -> str:
    """Get localized message with formatting"""
    message = MESSAGES.get(key, f"❌ Сообщение не найдено: {key}")
    if kwargs:
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError) as e:
            # Return message without formatting if there's an error
            return message
    return message


def format_price_per_month(total_price: int, months: int) -> str:
    """Format price per month"""
    try:
        price_per_month = total_price / months
        return f"{price_per_month:.0f}"
    except (ZeroDivisionError, TypeError):
        return "0"


def format_savings(plan_price: int, base_month_price: int, months: int) -> str:
    """Calculate and format savings"""
    try:
        full_price = base_month_price * months
        savings = full_price - plan_price
        if savings > 0:
            return f"Экономия {savings} ₽!"
        return "Базовая цена"
    except (TypeError, ValueError):
        return "Базовая цена"