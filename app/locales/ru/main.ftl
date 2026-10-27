language-name = Русский

choose-language = 🌐 Выберите язык / Choose your language

main-menu =
    🐙 Привет, { $name }!

    Это Octo VPN: быстрый VPN без ограничений по трафику и устройствам.
    Выберите действие:

btn-subscription = 🔑 Моя подписка
btn-buy = 💳 Купить подписку
btn-referrals = 👥 Пригласить друга
btn-support = 💬 Поддержка
btn-profile = 👤 Профиль
btn-back = ⬅️ Назад
btn-change-language = 🌐 Сменить язык
btn-change-theme = 🎨 Сменить тему
choose-theme = 🎨 Выберите оформление бота. Поменять его можно в любой момент в профиле.
theme-unavailable = Эта тема больше недоступна

profile =
    👤 <b>Профиль</b>

    ID: <code>{ $id }</code>
    С нами с: { $registered }
    Язык: { $language }
    Баланс: { $balance }
    Тема: { $theme }

btn-trial = 🎁 Попробовать бесплатно
btn-connect = 📲 Как подключить
btn-subscription-page = 🌐 Страница подписки
btn-extend = 💳 Продлить подписку
btn-open-channel = 📢 Перейти в канал
btn-check-subscription = ✅ Я подписался
btn-download-app = ⬇️ Скачать Happ

days = { $days ->
    [one] { $days } день
    [few] { $days } дня
   *[many] { $days } дней
}

no-subscription-trial =
    🔑 <b>Моя подписка</b>

    У вас пока нет подписки.
    Попробуйте бесплатно: { days } без ограничений, все локации.

no-subscription =
    🔑 <b>Моя подписка</b>

    У вас пока нет подписки.

subscription-active =
    ✅ <b>Подписка активна</b> до { $date } (осталось { days })

    Ваша ссылка для подключения:
    <code>{ $url }</code>

    Добавьте её в приложение один раз: все локации появятся там, переключаться можно в любой момент.

subscription-trial =
    🎁 <b>Пробный период</b> до { $date } (осталось { days })

    Ваша ссылка для подключения:
    <code>{ $url }</code>

    Добавьте её в приложение один раз: все локации появятся там, переключаться можно в любой момент.

subscription-expired =
    ⛔ <b>Подписка закончилась</b> { $date }

    Продлите её, и доступ вернётся. Ссылка в приложении останется прежней.

trial-activated = 🎉 Пробный период активирован!
trial-already-used = Пробный период уже был использован
trial-need-channel =
    📢 Чтобы получить { days } бесплатно, подпишитесь на наш канал.

    После подписки нажмите «Я подписался».
error-try-later = Что-то пошло не так. Попробуйте ещё раз через пару минут.

connect-choose-platform = 📲 Выберите устройство, на котором будете пользоваться VPN:

platform-ios = 🍏 iPhone / iPad
platform-android = 🤖 Android
platform-windows = 🪟 Windows
platform-macos = 💻 macOS

connect-steps =
    2. Скопируйте ссылку из раздела «Моя подписка» (нажмите на неё).
    3. Откройте Happ и нажмите «+» → «Вставить из буфера».
    4. Выберите локацию и включите VPN.

connect-ios =
    🍏 <b>iPhone / iPad</b>

    1. Установите Happ из App Store.
    { connect-steps }

connect-android =
    🤖 <b>Android</b>

    1. Скачайте и установите Happ (файл .apk из последнего релиза).
    { connect-steps }

connect-windows =
    🪟 <b>Windows</b>

    1. Скачайте и установите Happ (установщик для Windows из последнего релиза).
    { connect-steps }

connect-macos =
    💻 <b>macOS</b>

    1. Установите Happ из App Store.
    { connect-steps }

btn-promo = 🎟 Ввести промокод
btn-plan = { $plan } — { $price }
btn-pay-stars = ⭐ Оплатить { $stars } Stars
btn-pay-balance = ✅ Оплатить с баланса
btn-cancel = ✖️ Отмена
btn-share = 📤 Поделиться ссылкой

plan-name = { $months ->
    [one] { $months } месяц
    [few] { $months } месяца
   *[many] { $months } месяцев
}

buy-title =
    💳 <b>Выберите тариф</b>

    Во всех тарифах: без лимита трафика и устройств, все локации.
buy-no-plans =
    💳 <b>Покупка подписки</b>

    Тарифы скоро появятся.
buy-discount-pending = 🎟 Скидка { $percent }% по промокоду применится к следующей покупке.
buy-balance = 💰 На балансе { $balance }: он спишется при оплате.
plan-unavailable = Этот тариф сейчас недоступен

checkout-plan = 📦 <b>Тариф: { $plan }</b>
checkout-price = Цена: { $price }
checkout-discount = Скидка { $percent }%: −{ $amount }
checkout-balance = С баланса: −{ $amount }
checkout-total-stars = <b>К оплате: { $amount } ({ $stars } ⭐)</b>
checkout-total-balance = <b>Полностью оплачивается с баланса.</b>

invoice-title = Octo VPN — { $plan }
invoice-description = Подписка на { $plan }: без лимита трафика и устройств, все локации.
invoice-outdated = Счёт устарел. Откройте тариф в боте и оплатите заново.

payment-success = ✅ Оплата прошла! Подписка активна до { $date }.
payment-delayed = ✅ Оплата получена. Подписка активируется в течение нескольких минут, мы пришлём сообщение.

referral =
    👥 <b>Приглашайте друзей</b>

    Ваша ссылка:
    <code>{ $link }</code>

    С первой покупки друга вы получите { $first }% на баланс, со всех следующих — { $next }%. Балансом можно оплатить подписку.

    Приглашено: { $invited }
    Заработано: { $earned }
    Баланс: { $balance }
referral-share-text = Пользуюсь Octo VPN: быстрый, без лимитов. Попробуй бесплатно!
referral-reward = 🎉 Ваш друг оплатил подписку. На баланс начислено { $amount }.

promo-enter = 🎟 Отправьте промокод сообщением.
promo-error-not-found = Такого промокода нет. Проверьте написание и отправьте ещё раз.
promo-error-expired = Срок действия промокода истёк.
promo-error-exhausted = Этот промокод больше не действует: активации закончились.
promo-error-already-used = Вы уже использовали этот промокод.
promo-error-discount-pending = У вас уже есть неиспользованная скидка. Сначала оплатите подписку с ней.
promo-discount = 🎟 Промокод принят: скидка { $percent }% на следующую покупку.
promo-balance = 🎟 Промокод принят: на баланс начислено { $amount }.
promo-days = 🎟 Промокод принят: к подписке добавлено { days }.

reminder-5d = ⏳ Подписка закончится через 5 дней, { $date }. Продлите заранее, чтобы не остаться без VPN.
reminder-3d = ⏳ Подписка закончится через 3 дня, { $date }.
reminder-1d = ⏳ Подписка закончится завтра, { $date }.
reminder-1h = ⏰ Подписка закончится через час. Продлите сейчас, чтобы VPN не отключился.
reminder-expired = ⛔ Подписка закончилась. Продлите её, и доступ вернётся: ссылка в приложении останется прежней.

btn-admin = 🛠 Админка
trial-disabled = Пробный период сейчас недоступен

admin-extended = 🎁 Вам добавили { days } подписки. Теперь она действует до { $date }.
admin-balance-added = 💰 На ваш баланс начислено { $amount }.

btn-support-new = ✍️ Написать в поддержку
btn-support-write = ✍️ Написать
btn-support-close = ✅ Закрыть обращение
btn-support-reply = ✍️ Ответить

support-intro =
    💬 <b>Поддержка</b>

    Опишите проблему одним сообщением, можно приложить скриншот. Ответ придёт сюда, в бота.
support-ticket =
    💬 <b>Обращение #{ $id }</b>

    { $history }
support-write = ✍️ Напишите сообщение. Можно прислать фото со скриншотом и подписью.
support-empty = Пришлите текст или фото.
support-sent = ✅ Сообщение отправлено в поддержку. Ответ придёт сюда.
support-closed = ✅ Обращение закрыто. Если появятся вопросы, напишите нам снова.
support-closed-by-admin = ✅ Обращение #{ $id } закрыто. Если остались вопросы, напишите в поддержку ещё раз.
support-reply =
    💬 <b>Ответ поддержки</b> (обращение #{ $id }):

    { $text }
support-photo = 🖼
support-author-you = 👤 Вы
support-author-support = 🛟 Поддержка
admin-denied = Админка доступна только тем, чей ID указан в ADMIN_IDS. Ваш Telegram ID: <code>{ $id }</code>
