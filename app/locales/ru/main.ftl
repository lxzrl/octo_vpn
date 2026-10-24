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

profile =
    👤 <b>Профиль</b>

    ID: <code>{ $id }</code>
    С нами с: { $registered }
    Язык: { $language }

coming-soon = Этот раздел скоро появится

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
