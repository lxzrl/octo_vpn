# Админка: только на русском.

adm-menu = 🛠 <b>Админка</b>

adm-btn-stats = 📊 Статистика
adm-btn-find-user = 🔎 Пользователь
adm-btn-tickets = 💬 Обращения ({ $count })
adm-btn-plans = 💳 Тарифы
adm-btn-promos = 🎟 Промокоды
adm-btn-options = ⚙️ Настройки
adm-btn-broadcast = 📢 Рассылка
adm-btn-design = 🎨 Оформление
adm-btn-back = ⬅️ Назад
adm-btn-to-bot = 🏠 В меню бота
adm-btn-cancel = ✖️ Отмена

adm-not-found = Не найдено
adm-panel-error = ⚠️ Панель Remnawave не ответила, ничего не изменено. Попробуйте ещё раз.

## Статистика

adm-period-day = 24 часа
adm-period-week = 7 дней
adm-period-month = 30 дней
adm-period-total = всё время

adm-stats-revenue = { $period }: { $count } опл. · { $amount } · ⭐ { $stars }

adm-stats =
    📊 <b>Статистика</b>

    👥 Пользователей: { $users } (+{ $users_day } за сутки, +{ $users_week } за неделю)
    🚫 Заблокировали бота: { $blocked }

    🔑 Активных подписок: { $active_paid } платных, { $active_trial } пробных
    🎁 Пробный период взяли: { $trials_used }

    💰 <b>Оплаты</b> (реальными деньгами)
    { $revenue }

    💼 На балансах пользователей: { $balances }
    💬 Открытых обращений: { $tickets }

## Пользователь

adm-find-user = 🔎 Пришлите Telegram ID или @username пользователя.
adm-user-not-found = Пользователь не найден. Пришлите ID или @username ещё раз.

adm-user-no-sub = нет
adm-user-sub-active = { $trial ->
    [yes] 🎁 пробная до { $date }
   *[no] ✅ активна до { $date }
}
adm-user-sub-expired = ⛔ закончилась { $date }
adm-user-banned = 🚫 Забанен
adm-user-blocked-bot = 🔕 Заблокировал бота

adm-user-card =
    👤 { $user }

    Язык: { $language }
    Регистрация: { $registered }
    Подписка: { $subscription }
    Пробный период: { $trial }
    Баланс: { $balance }
    Оплат: { $payments } на { $paid }
    Пригласил его: { $referrer }
    Пригласил он: { $invited }, заработал { $earned }
    Открытое обращение: { $ticket }
    { $flags }

adm-btn-extend = ➕ Продлить
adm-btn-balance = 💰 Баланс
adm-btn-ban = 🚫 Забанить
adm-btn-unban = ✅ Разбанить
adm-btn-user-card = 👤 Карточка пользователя
adm-cannot-ban-admin = Админа забанить нельзя

adm-extend-prompt = ➕ На сколько дней продлить подписку? Пришлите число от 1 до 3650.
adm-extend-invalid = Нужно целое число дней от 1 до 3650.
adm-extend-done = ✅ Подписка продлена до { $date }, пользователь получил уведомление.

adm-balance-prompt =
    💰 Пришлите сумму в рублях: «150» начислит, «-150» спишет.
    Можно с копейками: «99,90».
adm-balance-invalid = Не понял сумму. Пример: 150, -50 или 99,90.
adm-balance-insufficient = Нельзя списать больше, чем есть на балансе ({ $balance }).
adm-balance-done = ✅ Баланс теперь { $balance }.

## Тарифы

adm-plans =
    💳 <b>Тарифы</b>

    Тариф без цены или скрытый не показывается покупателям.
adm-plan-no-price = без цены
adm-plan-title = { $status } { $months } мес · { $days } дн · { $price }
adm-plan =
    💳 <b>Тариф</b>

    { $title }
    { $priced ->
        [yes] { $active ->
            [yes] Виден покупателям.
           *[no] Скрыт.
        }
       *[no] Не продаётся, пока не задана цена.
    }
adm-btn-plan-price = ✏️ Изменить цену
adm-btn-plan-hide = 🙈 Скрыть
adm-btn-plan-show = 👁 Показать
adm-plan-price-prompt =
    ✏️ Пришлите цену в рублях целым числом (например, 199).
    Цена в звёздах посчитается по курсу из настроек. «-» уберёт цену.
adm-plan-price-invalid = Нужно целое число рублей от 1 до 100000 или «-».

## Промокоды

adm-promos = 🎟 <b>Промокоды</b> (последние 20): код · что даёт · сколько раз введён
adm-btn-promo-new = ➕ Новый промокод
adm-btn-promo-off = ⛔ Выключить
adm-btn-promo-on = ✅ Включить

adm-promo-value-discount = скидка { $value }%
adm-promo-value-balance = { $value } на баланс
adm-promo-value-days = { $value } дн. подписки

adm-promo =
    🎟 <b>{ $code }</b>

    Даёт: { $value }
    Введён: { $uses } из { $max_uses }
    Действует до: { $expires }
    { $active ->
        [yes] ✅ Включён
       *[no] ⛔ Выключен
    }

adm-promo-choose-kind = 🎟 Что даёт новый промокод?
adm-promo-kind-discount = 🏷 Скидку на следующую покупку
adm-promo-kind-balance = 💰 Деньги на баланс
adm-promo-kind-days = 📅 Дни подписки

adm-promo-value-prompt-discount = Размер скидки в процентах: число от 1 до 100.
adm-promo-value-prompt-balance = Сколько рублей начислить на баланс? Например, 100 или 49,90.
adm-promo-value-prompt-days = Сколько дней подписки добавить? Число от 1 до 3650.

adm-promo-max-uses-prompt = Сколько человек может ввести промокод? Пришлите число или нажмите «Без лимита».
adm-btn-unlimited = ♾ Без лимита
adm-promo-lifetime-prompt = Сколько дней промокод действует? Пришлите число или нажмите «Бессрочно».
adm-btn-no-expiry = ♾ Бессрочно
adm-promo-code-prompt = Пришлите сам код: латиница, цифры, «-» и «_», от 3 до 32 символов. Или нажмите «Сгенерировать».
adm-btn-generate-code = 🎲 Сгенерировать
adm-promo-code-taken = Код { $code } уже есть, пришлите другой.
adm-promo-created = ✅ Промокод создан.

## Настройки

adm-options =
    ⚙️ <b>Настройки</b>

    ⭐ Курс: 1 звезда = { $rate } ₽
    👥 Рефералка: { $first }% с первой оплаты друга, { $next }% со следующих
    🎁 Пробный период: { $trial ->
        [yes] включён, { $days } дн.
       *[no] выключен
    }
    📢 Канал для пробного периода: { $channel }
    🔗 Ссылка на канал: { $url }

adm-btn-trial-off = 🎁 Выключить пробный период
adm-btn-trial-on = 🎁 Включить пробный период
adm-option-stars_rub_rate = ⭐ Курс звезды
adm-option-referral_first_percent = 👥 % с первой оплаты
adm-option-referral_next_percent = 👥 % со следующих
adm-option-trial_days = 🎁 Дни пробного
adm-option-trial_channel = 📢 Канал
adm-option-trial_channel_url = 🔗 Ссылка на канал

adm-option-prompt-stars_rub_rate = Сколько рублей стоит одна звезда? Например, 1,5. Цены в звёздах пересчитаются сразу.
adm-option-prompt-referral_first_percent = Процент с первой оплаты приглашённого друга: число от 0 до 100.
adm-option-prompt-referral_next_percent = Процент со следующих оплат друга: число от 0 до 100.
adm-option-prompt-trial_days = Сколько дней длится пробный период? Число от 1 до 30.
adm-option-prompt-trial_channel =
    Канал, на который нужно подписаться для пробного периода: @username или числовой ID (-100…).
    Бот должен быть админом канала. «-» выключит проверку.
adm-option-prompt-trial_channel_url = Ссылка для кнопки «Перейти в канал» (https://…). Для публичного канала она строится сама, «-» уберёт ссылку.
adm-option-saved = ✅ Сохранено.
adm-channel-ok = ✅ Бот — администратор канала, подписку проверить сможет.
adm-channel-bad =
    ⚠️ Подписку на этот канал бот проверить не сможет: { $problem }.
    Добавьте бота в канал администратором (права можно не давать) и проверьте @username канала.
    Пока это не исправлено, пробный период никому не выдаётся.

## Рассылка

adm-broadcast = 📢 <b>Рассылка</b>: кому отправить?
adm-audience-all = Всем ({ $count })
adm-audience-active = С активной подпиской ({ $count })
adm-audience-inactive = Без активной подписки ({ $count })
adm-broadcast-prompt = Пришлите сообщение для рассылки: текст, фото, видео — оно уйдёт как есть.
adm-broadcast-confirm = ☝️ Так сообщение увидят получатели. Аудитория: { $audience }.
adm-btn-broadcast-send = 🚀 Отправить ({ $count })
adm-broadcast-started = 🚀 Рассылка запущена: { $count } получателей. Пришлю отчёт, когда закончится.
adm-broadcast-already = Эта рассылка уже запущена
adm-broadcast-report =
    📢 <b>Рассылка завершена</b>

    Доставлено: { $delivered } из { $total }
    Заблокировали бота: { $blocked }
    Ошибки: { $failed }

## Обращения

adm-tickets = 💬 <b>Открытые обращения</b> (🔴 ждёт ответа)
adm-tickets-empty = 💬 Открытых обращений нет.
adm-ticket =
    💬 <b>Обращение #{ $id }</b> · { $status ->
        [open] открыто
       *[closed] закрыто
    }
    { $user }

    { $history }
adm-ticket-new = 🆘 <b>Новое обращение #{ $id }</b> от { $user }
adm-ticket-message = 💬 <b>Сообщение в обращении #{ $id }</b> от { $user }
adm-ticket-closed-by-user = ✅ { $user } закрыл обращение #{ $id }
adm-btn-reply = ✍️ Ответить
adm-btn-open-ticket = 💬 Открыть обращение
adm-btn-close-ticket = ✅ Закрыть
adm-ticket-reply-prompt = ✍️ Пришлите ответ на обращение #{ $id }: текст или фото с подписью.
adm-ticket-empty = Пришлите текст или фото.
adm-ticket-reply-sent = ✅ Ответ отправлен.
adm-ticket-reply-failed = ⚠️ Ответ сохранён, но не доставлен: пользователь заблокировал бота.
adm-ticket-already-closed = Обращение уже закрыто
support-author-user = 👤 Пользователь

## Уведомления

adm-payment =
    💰 <b>Оплата #{ $id }</b> от { $user }
    { $plan } · цена { $price }
    Оплачено: { $paid }{ $stars ->
        [0] {""}
       *[other] {" "}(⭐ { $stars })
    }
    С баланса: { $balance } · скидка: { $discount }

## Оформление

adm-design =
    🎨 <b>Оформление</b>

    Тема — это набор картинок к экранам бота. Пользователь выбирает тему после языка и может
    сменить её в профиле. Если в теме нет картинки для экрана, берётся её картинка главного
    меню, а если нет и её — картинка темы «Светлая». 🙈 — тема скрыта.
adm-btn-theme-new = ➕ Новая тема
adm-theme =
    🎨 <b>{ $name }</b> (англ.: { $name_en })

    { $status }

    Выберите экран, чтобы загрузить или заменить картинку. ✅ — картинка есть.
adm-theme-default = Тема по умолчанию: у новых пользователей и у тех, чья тема скрыта.
adm-theme-active = Тема доступна пользователям.
adm-theme-hidden = 🙈 Тема скрыта: её нельзя выбрать, а у тех, кто выбрал, показывается «Светлая».
adm-btn-theme-hide = 🙈 Скрыть тему
adm-btn-theme-show = 👁 Показать тему
adm-btn-theme-delete = 🗑 Удалить тему
adm-btn-theme-delete-confirm = 🗑 Да, удалить
adm-theme-delete-confirm = Удалить тему { $name } вместе с картинками? Пользователи с этой темой перейдут на «Светлую».
adm-theme-deleted = Тема удалена
adm-theme-name-prompt = Название новой темы, например «🎃 Хэллоуин» (до 64 символов).
adm-theme-name-en-prompt = Название по-английски для англоязычных пользователей, например «🎃 Halloween». «-» — то же, что по-русски.
adm-theme-created = ✅ Тема создана. Загрузите картинки: хватит и одной, для главного меню.
adm-screen-main = Главное меню
adm-screen-profile = Профиль
adm-screen-theme = Выбор темы
adm-screen-subscription = Подписка
adm-screen-connect = Подключение
adm-screen-buy = Покупка
adm-screen-referral = Рефералка
adm-screen-support = Поддержка
adm-image = 🖼 <b>{ $theme } · { $screen }</b>

    { $status }
adm-image-set = Сейчас стоит эта картинка. Пришлите новую фото или файлом, чтобы заменить её.
adm-image-empty = Картинки нет. Пришлите картинку фото или файлом (JPG, PNG, WebP; лучше горизонтальную), и она появится над этим экраном.
adm-btn-image-remove = 🗑 Убрать картинку
adm-image-saved = ✅ Картинка сохранена.
adm-image-removed = Картинка убрана
adm-image-not-photo = Пришлите картинку фото или файлом: JPG, PNG или WebP.
adm-image-bad-file = Не получилось: файл больше 10 МБ или Telegram не принял его как фото (слишком вытянутая или огромная по размерам картинка). Попробуйте другой файл.
