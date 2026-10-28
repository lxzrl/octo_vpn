language-name = English

choose-language = 🌐 Выберите язык / Choose your language

main-menu =
    🐙 Hi, { $name }!

    This is Octo VPN: fast VPN with no traffic or device limits.
    Choose an action:

btn-subscription = 🔑 My subscription
btn-buy = 💳 Buy subscription
btn-referrals = 👥 Invite a friend
btn-support = 💬 Support
btn-profile = 👤 Profile
btn-back = ⬅️ Back
btn-change-language = 🌐 Change language
btn-change-theme = 🎨 Change theme
choose-theme = 🎨 Choose how the bot looks. You can change it any time in your profile.
theme-unavailable = This theme is no longer available

profile =
    👤 <b>Profile</b>

    ID: <code>{ $id }</code>
    Member since: { $registered }
    Language: { $language }
    Balance: { $balance }
    Theme: { $theme }

btn-trial = 🎁 Try for free
btn-connect = 📲 How to connect
btn-subscription-page = 🌐 Subscription page
btn-extend = 💳 Extend subscription
btn-open-channel = 📢 Open the channel
btn-check-subscription = ✅ I've subscribed
btn-download-app = ⬇️ Download Happ

days = { $days ->
    [one] { $days } day
   *[other] { $days } days
}

no-subscription-trial =
    🔑 <b>My subscription</b>

    You don't have a subscription yet.
    Try it for free: { days } with no limits, all locations.

no-subscription =
    🔑 <b>My subscription</b>

    You don't have a subscription yet.

subscription-active =
    ✅ <b>Subscription active</b> until { $date } ({ days } left)

    Your connection link:
    <code>{ $url }</code>

    Add it to the app once: all locations will appear there, and you can switch at any time.

subscription-trial =
    🎁 <b>Free trial</b> until { $date } ({ days } left)

    Your connection link:
    <code>{ $url }</code>

    Add it to the app once: all locations will appear there, and you can switch at any time.

subscription-expired =
    ⛔ <b>Subscription ended</b> on { $date }

    Extend it to get access back. The link in your app stays the same.

trial-activated = 🎉 Free trial activated!
trial-already-used = You have already used the free trial
trial-need-channel =
    📢 To get { days } for free, subscribe to our channel.

    Then tap "I've subscribed".
error-try-later = Something went wrong. Please try again in a couple of minutes.

connect-choose-platform = 📲 Choose the device you will use the VPN on:

platform-ios = 🍏 iPhone / iPad
platform-android = 🤖 Android
platform-windows = 🪟 Windows
platform-macos = 💻 macOS

connect-steps =
    2. Copy the link from "My subscription" (tap it).
    3. Open Happ and tap "+" → "Paste from clipboard".
    4. Pick a location and turn the VPN on.

connect-ios =
    🍏 <b>iPhone / iPad</b>

    1. Install Happ from the App Store.
    { connect-steps }

connect-android =
    🤖 <b>Android</b>

    1. Download and install Happ (the .apk file from the latest release).
    { connect-steps }

connect-windows =
    🪟 <b>Windows</b>

    1. Download and install Happ (the Windows installer from the latest release).
    { connect-steps }

connect-macos =
    💻 <b>macOS</b>

    1. Install Happ from the App Store.
    { connect-steps }

btn-promo = 🎟 Enter promo code
btn-plan = { $plan } — { $price }
btn-pay-stars = ⭐ Pay { $stars } Stars
btn-pay-balance = ✅ Pay from balance
btn-cancel = ✖️ Cancel
btn-share = 📤 Share the link

plan-name = { $months ->
    [one] { $months } month
   *[other] { $months } months
}

buy-title =
    💳 <b>Choose a plan</b>

    Every plan: no traffic or device limits, all locations.
buy-no-plans =
    💳 <b>Buy a subscription</b>

    Plans are coming soon.
buy-discount-pending = 🎟 Your { $percent }% promo discount will apply to your next purchase.
buy-balance = 💰 You have { $balance } on your balance: it will be used at checkout.
plan-unavailable = This plan is not available right now

checkout-plan = 📦 <b>Plan: { $plan }</b>
checkout-price = Price: { $price }
checkout-discount = { $percent }% discount: −{ $amount }
checkout-balance = From balance: −{ $amount }
checkout-total-stars = <b>To pay: { $amount } ({ $stars } ⭐)</b>
checkout-total-balance = <b>Fully paid from your balance.</b>

invoice-title = Octo VPN — { $plan }
invoice-description = { $plan } subscription: no traffic or device limits, all locations.
invoice-outdated = This invoice is outdated. Open the plan in the bot and pay again.

payment-success = ✅ Payment received! Your subscription is active until { $date }.
payment-delayed = ✅ Payment received. Your subscription will be activated within a few minutes, we will message you.

referral =
    👥 <b>Invite friends</b>

    Your link:
    <code>{ $link }</code>

    You get { $first }% of a friend's first purchase and { $next }% of every next one on your balance. The balance can pay for your subscription.

    Invited: { $invited }
    Earned: { $earned }
    Balance: { $balance }
referral-share-text = I use Octo VPN: fast, no limits. Try it for free!
referral-reward = 🎉 Your friend paid for a subscription. { $amount } added to your balance.

promo-enter = 🎟 Send the promo code as a message.
promo-error-not-found = There is no such promo code. Check the spelling and try again.
promo-error-expired = This promo code has expired.
promo-error-exhausted = This promo code is no longer valid: it has run out of uses.
promo-error-already-used = You have already used this promo code.
promo-error-discount-pending = You already have an unused discount. Use it on a purchase first.
promo-discount = 🎟 Promo code accepted: { $percent }% off your next purchase.
promo-balance = 🎟 Promo code accepted: { $amount } added to your balance.
promo-days = 🎟 Promo code accepted: { days } added to your subscription.

reminder-5d = ⏳ Your subscription ends in 5 days, on { $date }. Extend it in advance to stay connected.
reminder-3d = ⏳ Your subscription ends in 3 days, on { $date }.
reminder-1d = ⏳ Your subscription ends tomorrow, { $date }.
reminder-1h = ⏰ Your subscription ends in an hour. Extend it now so the VPN keeps working.
reminder-expired = ⛔ Your subscription has ended. Extend it to get access back: the link in your app stays the same.

btn-admin = 🛠 Admin
trial-disabled = The free trial is not available right now

admin-extended = 🎁 You got { days } of subscription. It is now active until { $date }.
admin-balance-added = 💰 { $amount } has been added to your balance.

btn-support-new = ✍️ Contact support
btn-support-write = ✍️ Write
btn-support-close = ✅ Close the request
btn-support-reply = ✍️ Reply

support-intro =
    💬 <b>Support</b>

    Describe the problem in one message, you can attach a screenshot. The answer will come here, in the bot.
support-ticket =
    💬 <b>Request #{ $id }</b>

    { $history }
support-write = ✍️ Write your message. You can send a screenshot with a caption.
support-empty = Please send text or a photo.
support-sent = ✅ Your message has been sent to support. The answer will come here.
support-closed = ✅ The request is closed. If you have more questions, write to us again.
support-closed-by-admin = ✅ Request #{ $id } is closed. If you still have questions, contact support again.
support-reply =
    💬 <b>Support reply</b> (request #{ $id }):

    { $text }
support-photo = 🖼
support-author-you = 👤 You
support-author-support = 🛟 Support
admin-denied = The admin menu is only for IDs listed in ADMIN_IDS. Your Telegram ID: <code>{ $id }</code>
